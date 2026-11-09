"""Research admission checks and atomic publication of versioned JSON batches."""
from __future__ import annotations

import copy
import json
import re
from collections import deque
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .migrate import FACETS
from .store import KINDS, canonical, digest, now

PRECISIONS = {'unknown', 'day', 'month', 'year', 'time'}
GRADES = {'primary_explicit', 'attributed_explicit', 'lead_unresolved'}
ARRAYS = [kind for kind in KINDS if kind != 'batches']


def public_date(value, precision='day'):
    """Return conservative availability date. Do not guess unknown dates."""
    import calendar
    if not value or precision == 'unknown':
        return None
    try:
        if precision == 'year':
            return date(int(str(value)[:4]), 12, 31).isoformat()
        if precision == 'month':
            year, month = map(int, str(value)[:7].split('-'))
            return date(year, month, calendar.monthrange(year, month)[1]).isoformat()
        if precision == 'time':
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', str(value)):
                return None
            return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(timezone.utc).date().isoformat()
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(value)):
            return None
        return date.fromisoformat(str(value)).isoformat()
    except (ValueError, TypeError):
        return None


def eligible_relationship(value):
    return value.get('evidence_grade') in {'primary_explicit', 'attributed_explicit'} and value.get('legacy_retention') != 'excluded'


def schema_errors(batch, record_kind=None):
    """Enforce field types before semantic checks; optional arrays retain API defaults."""
    import jsonschema
    path = Path(__file__).resolve().parents[1] / 'schemas' / 'batch_v1.schema.json'
    if not path.exists():
        return ['Required batch JSON schema is missing; publication is unavailable.']
    schema = json.loads(path.read_text(encoding='utf-8'))
    schema['required'] = ['schema_version', 'batch_id', 'name', 'base_revision', 'cutoff', 'mode']
    # Minimal records can omit unknown optional metadata; all supplied properties are typed.
    minimal = {'company': ['id', 'name'], 'instrument': ['id', 'company_id', 'ticker'], 'source': ['id', 'title', 'publisher', 'url', 'published_date', 'date_precision'], 'relationship': ['id', 'source_id', 'target_id', 'type', 'description', 'status', 'evidence_grade', 'direction'], 'project': ['id', 'name', 'source_ids'], 'frontier': ['id', 'facet'], 'coverage': ['id']}
    for name, required in minimal.items():
        schema.get('$defs', {}).get(name, {})['required'] = required
    if record_kind:
        singular = {'companies': 'company', 'instruments': 'instrument', 'relationships': 'relationship', 'projects': 'project', 'participations': 'participation', 'frontier': 'frontier', 'coverage': 'coverage'}[record_kind]
        schema = {'$ref': f'#/$defs/{singular}', '$defs': schema['$defs']}
    validator = jsonschema.Draft202012Validator(schema)
    return [f'JSON schema {"/".join(map(str, error.absolute_path)) or "/"}: {error.message}' for error in sorted(validator.iter_errors(batch), key=lambda error: str(error.absolute_path))][:50]


def claim_available_from(claim, sources):
    known = public_date(claim.get('known_from'), claim.get('date_precision', 'day'))
    dates = [public_date(sources.get(identifier, {}).get('published_date'), sources.get(identifier, {}).get('date_precision', 'day')) for identifier in claim.get('source_ids', [])]
    return max([known] + dates) if known and dates and all(dates) else None


def _records(snapshot):
    return {kind: {row['id']: row for row in snapshot.get(kind, [])} for kind in KINDS}


def validate_batch(batch, snapshot, revision):
    errors, warnings = [], []
    result = {'valid': False, 'batch_id': batch.get('batch_id') if isinstance(batch, dict) else None, 'base_revision': batch.get('base_revision') if isinstance(batch, dict) else None, 'errors': errors, 'warnings': warnings, 'diff': {kind: 0 for kind in (*ARRAYS, 'superseded_claims', 'updated_records')}, 'preview': {'nodes': [], 'edges': []}, 'coverage': {}, 'idempotent': False}
    if not isinstance(batch, dict):
        errors.append('Batch must be a JSON object.')
        return result
    typed_errors = schema_errors(batch)
    if typed_errors:
        errors.extend(typed_errors)
        return result
    for key in ('schema_version', 'batch_id', 'name', 'base_revision', 'cutoff', 'mode'):
        if key not in batch:
            errors.append(f'Missing required batch field: {key}.')
    if batch.get('schema_version') != '1.0':
        errors.append('schema_version must be 1.0.')
    if not isinstance(batch.get('batch_id'), str) or not batch.get('batch_id', '').strip():
        errors.append('batch_id must be a nonempty stable string.')
    if not isinstance(batch.get('name'), str) or not batch.get('name', '').strip():
        errors.append('name must be nonempty.')
    existing = _records(snapshot)
    prior = existing['batches'].get(batch.get('batch_id'))
    content_hash = digest(batch)
    if prior:
        if prior.get('content_hash') == content_hash:
            result.update(valid=True, idempotent=True)
            return result
        errors.append('batch_id already exists with different content; use a new batch ID.')
    if isinstance(batch.get('base_revision'), bool) or batch.get('base_revision') != revision:
        errors.append(f'Stale base_revision: active revision is {revision}.')
    cutoff = public_date(batch.get('cutoff'))
    if not cutoff:
        errors.append('cutoff must be an ISO calendar date.')
    if batch.get('mode') not in ('company', 'project'):
        errors.append('mode must be company or project.')
    if batch.get('max_additional_hops', 2) != 2:
        errors.append('v1 max_additional_hops must be 2.')
    list_fields = (*ARRAYS, 'root_company_ids', 'root_project_ids', 'investigated_company_ids', 'investigated_project_ids', 'supersedes_claim_ids', 'research_log', 'record_updates')
    for field in list_fields:
        if not isinstance(batch.get(field, []), list):
            errors.append(f'{field} must be an array.')
    if errors and any(not isinstance(batch.get(field, []), list) for field in list_fields):
        return result
    for field in ('root_company_ids', 'root_project_ids', 'investigated_company_ids', 'investigated_project_ids', 'supersedes_claim_ids'):
        if any(not isinstance(value, str) for value in batch.get(field, [])):
            errors.append(f'{field} must contain string IDs.')
    if errors and any(any(not isinstance(value, str) for value in batch.get(field, [])) for field in ('root_company_ids', 'root_project_ids', 'investigated_company_ids', 'investigated_project_ids', 'supersedes_claim_ids')):
        return result
    if batch.get('mode') == 'company' and len(set(batch.get('investigated_company_ids', []))) > 25:
        errors.append('Company batches investigate at most 25 distinct companies; enumeration may be larger.')
    if batch.get('mode') == 'project':
        if len(set(batch.get('investigated_project_ids', [])) | set(batch.get('root_project_ids', []))) > 5:
            errors.append('Project batches investigate at most five projects.')
        if batch.get('investigated_company_ids'):
            errors.append('Project batches cannot deeply investigate company ecosystems; queue a company batch.')
    additions = {}
    for kind in ARRAYS:
        additions[kind] = {}
        for row in batch.get(kind, []):
            if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row.get('id', '').strip():
                errors.append(f'Each {kind} record needs a nonempty string id.')
                continue
            if row['id'] in additions[kind]:
                errors.append(f'Duplicate {kind} ID in batch: {row["id"]}.')
                continue
            additions[kind][row['id']] = row
            if row['id'] in existing[kind] and canonical(row) != canonical(existing[kind][row['id']]):
                errors.append(f'Cannot overwrite existing {kind}/{row["id"]}; add a sourced correction/superseding claim.')
        result['diff'][kind] = sum(identifier not in existing[kind] for identifier in additions[kind])
    combined = {kind: existing[kind] | additions.get(kind, {}) for kind in KINDS}
    updated = {kind: {} for kind in KINDS}
    update_keys = set()
    for update in batch.get('record_updates', []):
        if not isinstance(update, dict):
            errors.append('record_updates entries must be objects.')
            continue
        kind, identifier, changes = update.get('kind'), update.get('id'), update.get('changes')
        if kind not in ('companies', 'instruments', 'relationships', 'projects', 'participations', 'frontier', 'coverage') or not isinstance(identifier, str) or identifier not in existing.get(kind, {}):
            errors.append('Each record_update must identify an existing supported kind/id.')
            continue
        if (kind, identifier) in update_keys:
            errors.append(f'Duplicate record_update for {kind}/{identifier}.')
        update_keys.add((kind, identifier))
        if not isinstance(changes, dict) or not changes or not update.get('reason'):
            errors.append(f'Update {kind}/{identifier} requires nonempty changes and reason.')
            continue
        forbidden = {'id', 'legacy', 'batch_id'} | ({'source_id', 'target_id'} if kind == 'relationships' else set())
        if forbidden.intersection(changes):
            errors.append(f'Update {kind}/{identifier} cannot change IDs, original legacy data, batch identity or relationship endpoints.')
            continue
        candidate = {**copy.deepcopy(existing[kind][identifier]), **copy.deepcopy(changes)}
        candidate_errors = schema_errors(candidate, kind)
        if candidate_errors:
            errors.extend(f'Updated {kind}/{identifier}: {message}' for message in candidate_errors)
            continue
        updated[kind][identifier] = candidate
        combined[kind][identifier] = candidate
        if kind not in ('frontier', 'coverage'):
            claim_ids = update.get('claim_ids', [])
            if not isinstance(claim_ids, list) or not claim_ids:
                errors.append(f'Factual update {kind}/{identifier} requires new explicit claim_ids.')
                continue
            for claim_id in claim_ids:
                claim = additions['claims'].get(claim_id)
                if not claim:
                    errors.append(f'Update {kind}/{identifier} must reference a new explicit claim, not an unrelated old claim.')
                    continue
                company_id = identifier if kind == 'companies' else candidate.get('company_id')
                related = (kind == 'relationships' and claim.get('relationship_id') == identifier) or (kind == 'companies' and identifier in (claim.get('company_id'), claim.get('subject_id'), claim.get('object_id'))) or (kind == 'instruments' and company_id in (claim.get('company_id'), claim.get('subject_id'), claim.get('object_id'))) or (kind == 'projects' and claim.get('project_id') == identifier) or (kind == 'participations' and claim.get('project_id') == candidate.get('project_id') and company_id in (claim.get('company_id'), claim.get('subject_id'), claim.get('object_id')))
                if not related:
                    errors.append(f'Update {kind}/{identifier} claim {claim_id} does not identify the affected entity/relationship.')
    result['diff']['updated_records'] = sum(len(rows) for rows in updated.values())
    checking = {kind: additions.get(kind, {}) | updated[kind] for kind in KINDS}

    def check_date(value, precision, label, reject_future=True):
        if precision not in PRECISIONS:
            errors.append(f'{label}: date_precision must be explicit (unknown/day/month/year/time).')
            return
        if precision == 'unknown':
            if value is not None:
                errors.append(f'{label}: unknown date must be null.')
            return
        resolved = public_date(value, precision)
        if not resolved:
            errors.append(f'{label}: invalid date for {precision} precision.')
        elif reject_future and cutoff and resolved > cutoff:
            errors.append(f'{label}: public-knowledge date exceeds cutoff.')

    for source in additions['sources'].values():
        if any(not isinstance(source.get(key), str) or not source.get(key, '').strip() for key in ('title', 'publisher', 'url')):
            errors.append(f'Source {source["id"]} needs title, publisher and URL.')
        if urlparse(str(source.get('url', ''))).scheme not in ('http', 'https'):
            errors.append(f'Source {source["id"]} URL must use https or http.')
        check_date(source.get('published_date'), source.get('date_precision'), f'Source {source["id"]}')

    def source_ids(row, label):
        values = row.get('source_ids', [])
        if not isinstance(values, list) or not values or any(not isinstance(value, str) or value not in combined['sources'] for value in values):
            errors.append(f'{label}: provide at least one existing/resolved source_id.')

    def terms(row, label):
        if not isinstance(row.get('terms', []), list):
            errors.append(f'{label}: terms must be an array.')
            return
        for index, term in enumerate(row.get('terms', [])):
            if not isinstance(term, dict):
                errors.append(f'{label} term {index} must be an object.')
                continue
            for key in ('value', 'unit', 'period', 'scope', 'known_from', 'source_ids'):
                if key not in term:
                    errors.append(f'{label} term {index} requires its own {key}; unknown values remain null.')
            if not term.get('unit'):
                errors.append(f'{label} term {index} requires units.')
            source_ids(term, f'{label} term {index}')
            if term.get('known_from') is not None and not public_date(term.get('known_from')):
                errors.append(f'{label} term {index} has invalid known_from.')
            if term.get('known_from') and cutoff and str(term['known_from'])[:10] > cutoff:
                errors.append(f'{label} term {index} availability exceeds cutoff.')

    for company in checking['companies'].values():
        if not company.get('name'):
            errors.append(f'Company {company["id"]} needs a name.')
        if company.get('status', 'unknown') not in ('public', 'private', 'subsidiary', 'private_subsidiary', 'unknown'):
            errors.append(f'Company {company["id"]} has unsupported status.')
        if company.get('parent_id') and company['parent_id'] not in combined['companies']:
            errors.append(f'Company {company["id"]} parent is unresolved.')
        if company.get('parent_id') == company['id']:
            errors.append(f'Company {company["id"]} cannot parent itself.')
        for old in combined['companies'].values():
            if old['id'] != company['id'] and re.sub(r'\W', '', old.get('name', '').lower()) == re.sub(r'\W', '', company.get('name', '').lower()) and not company.get('identity_resolution_notes'):
                errors.append(f'Company {company["id"]} duplicates name of {old["id"]}; resolve identity or provide identity_resolution_notes.')
                break
    for company in checking['companies'].values():
        seen, current = set(), company['id']
        while current in combined['companies']:
            if current in seen:
                errors.append(f'Company {company["id"]} creates a legal-parent cycle.')
                break
            seen.add(current)
            current = combined['companies'][current].get('parent_id')

    ticker_owners = {}
    for instrument in combined['instruments'].values():
        if instrument.get('company_id') not in combined['companies']:
            errors.append(f'Instrument {instrument["id"]} company is unresolved.')
        if not instrument.get('ticker'):
            errors.append(f'Instrument {instrument["id"]} needs ticker.')
        key = str(instrument.get('ticker', '')).upper()
        if key in ticker_owners and ticker_owners[key] != instrument.get('company_id'):
            errors.append(f'Ticker {key} already belongs to another company; ADR/share classes are instruments, not duplicate issuers.')
        ticker_owners[key] = instrument.get('company_id')

    superseded = set(batch.get('supersedes_claim_ids', []))
    for claim in additions['claims'].values():
        label = f'Claim {claim["id"]}'
        relation = combined['relationships'].get(claim.get('relationship_id'))
        entity_kind = claim.get('entity_kind', 'relationship')
        if entity_kind == 'relationship':
            if not relation:
                errors.append(f'{label}: relationship_id is unresolved.')
            elif {claim.get('subject_id'), claim.get('object_id')} != {relation.get('source_id'), relation.get('target_id')}:
                errors.append(f'{label}: subject/object must match the explicit relationship endpoints.')
        elif entity_kind == 'company':
            if claim.get('company_id') not in combined['companies'] or claim.get('relationship_id'):
                errors.append(f'{label}: company claim needs resolved company_id and null relationship_id.')
        elif entity_kind == 'project':
            if claim.get('project_id') not in combined['projects'] or claim.get('relationship_id'):
                errors.append(f'{label}: project claim needs resolved project_id and null relationship_id.')
        else:
            errors.append(f'{label}: entity_kind must be relationship, company or project.')
        if claim.get('evidence_grade') not in GRADES - {'lead_unresolved'}:
            errors.append(f'{label}: accepted claims need primary_explicit or attributed_explicit evidence.')
        if any(not isinstance(claim.get(key), str) or not claim.get(key, '').strip() for key in ('predicate', 'locator', 'supporting_text')):
            errors.append(f'{label}: predicate, locator and supporting_text are required.')
        source_ids(claim, label)
        if claim.get('evidence_grade') == 'primary_explicit':
            for identifier in claim.get('source_ids', []):
                source = combined['sources'].get(identifier, {})
                category = str(source.get('document_type') or source.get('evidence_class') or '').lower()
                if any(token in category for token in ('institutional', 'research_report', 'specialist', 'news_article', 'technical_analysis', 'media_report')):
                    errors.append(f'{label}: institutional or reporting sources require attributed_explicit; do not promote attribution to company confirmation.')
        check_date(claim.get('known_from'), claim.get('date_precision'), label)
        terms(claim, label)
        if claim.get('supersedes_id'):
            if claim['supersedes_id'] not in existing['claims']:
                errors.append(f'{label}: supersedes_id must resolve to an existing claim.')
            elif any(existing['claims'][claim['supersedes_id']].get(key) != claim.get(key) for key in ('relationship_id', 'company_id', 'project_id')):
                errors.append(f'{label}: supersession must remain within the same relationship/company/project.')
            superseded.add(claim['supersedes_id'])
        conflicts = claim.get('conflict_with_ids', [])
        if not isinstance(conflicts, list) or any(identifier not in existing['claims'] for identifier in conflicts):
            errors.append(f'{label}: conflict_with_ids must identify existing claims.')
    for identifier in superseded:
        if identifier not in existing['claims']:
            errors.append(f'Superseded claim {identifier} does not exist.')
        if not any(row.get('supersedes_id') == identifier for row in additions['claims'].values()):
            errors.append(f'Superseded claim {identifier} needs a new claim with supersedes_id; no destructive removal.')
    result['diff']['superseded_claims'] = len(superseded)

    for relation in checking['relationships'].values():
        label = f'Relationship {relation["id"]}'
        if relation.get('source_id') not in combined['companies'] or relation.get('target_id') not in combined['companies']:
            errors.append(f'{label}: both endpoints must resolve to company IDs.')
        if relation.get('source_id') == relation.get('target_id'):
            errors.append(f'{label}: self edges are not accepted.')
        if relation.get('evidence_grade') not in ('primary_explicit', 'attributed_explicit'):
            errors.append(f'{label}: inference-only connections belong in frontier, not relationships.')
        if not relation.get('type') or not relation.get('description'):
            errors.append(f'{label}: type and description are required.')
        if relation.get('direction') not in ('undirected', 'directed'):
            errors.append(f'{label}: direction must be explicit.')
        if relation.get('direction') == 'directed' and relation.get('direction_review_status') != 'reviewed':
            errors.append(f'{label}: directed edges require direction_review_status reviewed.')
        linked = [claim for claim in combined['claims'].values() if claim.get('relationship_id') == relation['id'] and claim['id'] not in superseded]
        if not linked:
            errors.append(f'{label}: at least one explicit sourced claim is required.')
        if relation.get('evidence_grade') == 'primary_explicit' and linked and not any(claim.get('evidence_grade') == 'primary_explicit' for claim in linked):
            errors.append(f'{label}: attributed-only claims cannot establish a primary_explicit relationship.')
        for identifier in relation.get('claim_ids', []):
            if identifier not in combined['claims'] or combined['claims'][identifier].get('relationship_id') != relation['id']:
                errors.append(f'{label}: claim_ids include an unrelated or unresolved claim.')
        if relation.get('product') and not any(claim.get('product') == relation['product'] or claim.get('product_scope') == relation['product'] for claim in linked):
            errors.append(f'{label}: product attribution requires matching claim.product or claim.product_scope; catalogues/list membership cannot create attribution.')
        if relation.get('project_id') and relation['project_id'] not in combined['projects']:
            errors.append(f'{label}: project_id is unresolved.')
        if relation.get('known_from') and not public_date(relation['known_from']):
            errors.append(f'{label}: known_from must be ISO date or null.')
        if relation.get('known_from') and cutoff and relation['known_from'][:10] > cutoff:
            errors.append(f'{label}: known_from exceeds cutoff.')
        for key in ('valid_from', 'valid_to'):
            if relation.get(key) and not public_date(relation[key]):
                errors.append(f'{label}: invalid {key}.')
        if relation.get('valid_from') and relation.get('valid_to') and relation['valid_to'] < relation['valid_from']:
            errors.append(f'{label}: valid_to precedes valid_from.')
    for project in checking['projects'].values():
        if not project.get('name'):
            errors.append(f'Project {project["id"]} needs a name.')
        source_ids(project, f'Project {project["id"]}')
        terms(project, f'Project {project["id"]}')
    for participation in checking['participations'].values():
        if participation.get('company_id') not in combined['companies'] or participation.get('project_id') not in combined['projects']:
            errors.append(f'Participation {participation["id"]}: company/project unresolved.')
        if not participation.get('role'):
            errors.append(f'Participation {participation["id"]}: role required.')
        source_ids(participation, f'Participation {participation["id"]}')
        if not participation.get('claim_ids'):
            errors.append(f'Participation {participation["id"]}: an explicit sourced project/role claim is required.')
        for identifier in participation.get('claim_ids', []):
            if identifier not in combined['claims']:
                errors.append(f'Participation {participation["id"]}: unresolved claim.')
            elif combined['claims'][identifier].get('project_id') != participation.get('project_id') and combined['relationships'].get(combined['claims'][identifier].get('relationship_id'), {}).get('project_id') != participation.get('project_id'):
                errors.append(f'Participation {participation["id"]}: claim must identify this project or an explicit project relationship.')
        role_claims = [combined['claims'].get(identifier, {}) for identifier in participation.get('claim_ids', [])]
        if not any(claim.get('project_id') == participation.get('project_id') and claim.get('company_id') == participation.get('company_id') and claim.get('role') == participation.get('role') for claim in role_claims):
            errors.append(f'Participation {participation["id"]}: requires an atomic project-role claim matching company_id, project_id and role.')
    for frontier in checking['frontier'].values():
        if frontier.get('facet') not in FACETS:
            errors.append(f'Frontier {frontier["id"]}: facet must be one of the six research branches.')
        if frontier.get('status', 'pending') not in ('pending', 'in_progress', 'completed', 'blocked', 'excluded', 'no_explicit_evidence'):
            errors.append(f'Frontier {frontier["id"]}: unsupported research status.')
        if bool(frontier.get('company_id')) == bool(frontier.get('project_id')):
            errors.append(f'Frontier {frontier["id"]}: nominate exactly one company or project.')
        if frontier.get('company_id') and frontier['company_id'] not in combined['companies']:
            errors.append(f'Frontier {frontier["id"]}: company unresolved.')
        if frontier.get('project_id') and frontier['project_id'] not in combined['projects']:
            errors.append(f'Frontier {frontier["id"]}: project unresolved.')
        if frontier.get('parent_frontier_id') and frontier['parent_frontier_id'] not in combined['frontier']:
            errors.append(f'Frontier {frontier["id"]}: parent frontier unresolved.')

    roots = batch.get('root_company_ids', [])
    project_roots = batch.get('root_project_ids', [])
    if batch.get('mode') == 'company' and not roots:
        errors.append('Company mode needs at least one root_company_id.')
    if batch.get('mode') == 'project' and not project_roots:
        errors.append('Project mode needs at least one root_project_id.')
    for identifier in roots + batch.get('investigated_company_ids', []):
        if identifier not in combined['companies']:
            errors.append(f'Unresolved root/investigated company: {identifier}.')
    for identifier in project_roots + batch.get('investigated_project_ids', []):
        if identifier not in combined['projects']:
            errors.append(f'Unresolved root/investigated project: {identifier}.')
    adjacency = {identifier: set() for identifier in combined['companies']}
    for relation in combined['relationships'].values():
        if eligible_relationship(relation) and relation.get('source_id') in adjacency and relation.get('target_id') in adjacency:
            adjacency[relation['source_id']].add(relation['target_id'])
            adjacency[relation['target_id']].add(relation['source_id'])
    distances = {identifier: 0 for identifier in roots if identifier in adjacency}
    for participation in combined['participations'].values():
        if participation.get('project_id') in project_roots and participation.get('company_id') in adjacency:
            distances[participation['company_id']] = 0
    queue = deque(distances)
    while queue:
        identifier = queue.popleft()
        if distances[identifier] >= 2:
            continue
        for neighbor in adjacency[identifier]:
            if neighbor not in distances:
                distances[neighbor] = distances[identifier] + 1
                queue.append(neighbor)
    expanded = set(additions['companies']) | set(batch.get('investigated_company_ids', []))
    for relation in additions['relationships'].values():
        expanded.update([relation.get('source_id'), relation.get('target_id')])
    for identifier in expanded:
        if identifier not in distances:
            errors.append(f'Company {identifier} is disconnected or beyond two explicit company hops from this batch frontier.')
    for project_id in additions['projects']:
        if batch.get('mode') == 'project' and project_id not in project_roots and project_id not in batch.get('investigated_project_ids', []):
            errors.append(f'Project {project_id} must be declared as a root or investigated project.')
    if not batch.get('coverage'):
        warnings.append('No coverage records supplied; this batch cannot claim a completed source checklist.')
    if any(claim.get('date_precision') == 'unknown' for claim in additions['claims'].values()):
        warnings.append('Unknown claim dates are retained but excluded from historical graph filters.')
    result['coverage'] = {'records': len(batch.get('coverage', [])), 'investigated_companies': len(set(batch.get('investigated_company_ids', []))), 'investigated_projects': len(set(batch.get('investigated_project_ids', []))), 'enumerated_companies': result['diff']['companies'], 'max_hops': 2, 'declared_limits_only_not_total_network_completeness': True}
    result['preview'] = {'nodes': list(checking['companies'].values())[:100], 'edges': list(checking['relationships'].values())[:300], 'updates': copy.deepcopy(batch.get('record_updates', []))}
    result['valid'] = not errors
    return result


def apply_batch(batch, snapshot):
    result = copy.deepcopy(snapshot)
    for kind in ARRAYS:
        ids = {row['id'] for row in result[kind]}
        for value in batch.get(kind, []):
            if value['id'] not in ids:
                row = copy.deepcopy(value)
                row.setdefault('batch_id', batch['batch_id'])
                result[kind].append(row)
                ids.add(row['id'])
    for update in batch.get('record_updates', []):
        for row in result[update['kind']]:
            if row['id'] == update['id']:
                relevant_claims = [claim for claim in batch.get('claims', []) if claim['id'] in update.get('claim_ids', [])]
                sources = {source['id']: source for source in result['sources']}
                known_dates = [claim_available_from(claim, sources) for claim in relevant_claims]
                previous = {key: copy.deepcopy(row.get(key)) for key in update['changes']}
                row.setdefault('record_history', []).append({'batch_id': batch['batch_id'], 'changes': copy.deepcopy(update['changes']), 'previous': previous, 'previous_missing': [key for key in update['changes'] if key not in row], 'known_from': max(known_dates) if known_dates and all(known_dates) else None})
                row.update(copy.deepcopy(update['changes']))
                row['last_updated_batch_id'] = batch['batch_id']
                break
    claims_by_relation = {}
    for claim in result['claims']:
        claims_by_relation.setdefault(claim.get('relationship_id'), []).append(claim['id'])
    for relation in result['relationships']:
        relation['claim_ids'] = claims_by_relation.get(relation['id'], [])
    result['batches'].append({'id': batch['batch_id'], 'batch_id': batch['batch_id'], 'name': batch['name'], 'cutoff': batch['cutoff'], 'mode': batch['mode'], 'created_at': now(), 'base_revision': batch['base_revision'], 'content_hash': digest(batch), 'research_log': batch.get('research_log', []), 'record_updates': copy.deepcopy(batch.get('record_updates', [])), 'limits': {key: batch.get(key) for key in ('max_additional_hops', 'investigated_company_ids', 'investigated_project_ids', 'root_company_ids', 'root_project_ids')}})
    result.setdefault('meta', {})['source_cutoff'] = max(filter(None, [result.get('meta', {}).get('source_cutoff'), batch.get('cutoff')]))
    return result


def as_of_record(row, cutoff):
    """Undo later factual metadata updates without rewriting the active record."""
    result = copy.deepcopy(row)
    if cutoff:
        for update in reversed(result.get('record_history', [])):
            if not update.get('known_from') or update['known_from'] > cutoff:
                result.update(copy.deepcopy(update['previous']))
                for key in update.get('previous_missing', []):
                    result.pop(key, None)
    return result
