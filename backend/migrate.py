"""Lossless atlas import. Discovery paths never become economic arrows."""
from __future__ import annotations

import copy
from pathlib import Path
import json
from .store import empty_snapshot, now, digest

FACETS = ('supply_manufacturing', 'customers_distribution', 'corporate_ecosystem', 'collaboration_dependencies', 'strategic_investment', 'projects_financing')
TYPE_FACET = {
    'upstream_supplier': 'supply_manufacturing', 'downstream_customer': 'customers_distribution',
    'channel_partner': 'customers_distribution', 'strategic_equity': 'strategic_investment',
    'joint_venture': 'corporate_ecosystem', 'infrastructure': 'projects_financing',
    'financing': 'projects_financing', 'competitor': 'collaboration_dependencies', 'complement': 'collaboration_dependencies',
}


def migration(seed_path):
    raw = json.loads(Path(seed_path).read_text(encoding='utf-8-sig'))
    snapshot = empty_snapshot()
    mapping = {kind: {} for kind in ('companies', 'instruments', 'sources', 'relationships')}
    batch_id = 'legacy-atlas-import'
    for value in raw.get('companies', []):
        item = copy.deepcopy(value)
        item.update(id=value['company_id'], status=value.get('public_private', 'unknown'), aliases=value.get('aliases', []), notes=value.get('notes', ''), reviewed_at=raw.get('as_of'), legacy=copy.deepcopy(value))
        snapshot['companies'].append(item)
        mapping['companies'][value['company_id']] = item['id']
    for index, value in enumerate(raw.get('instruments', [])):
        item = copy.deepcopy(value)
        item.update(id=f"instrument:{value['company_id']}:{value['ticker']}", exchange=value.get('declared_exchange'), currency=value.get('declared_currency'), legacy=copy.deepcopy(value))
        snapshot['instruments'].append(item)
        mapping['instruments'][str(index)] = item['id']
    for value in raw.get('sources', []):
        item = copy.deepcopy(value)
        item.update(id=value['source_id'], date_precision=value.get('date_precision') or ('day' if value.get('published_date') else 'unknown'), retrieved_at=None, locator='; '.join(value.get('reviewed_sections', [])), legacy=copy.deepcopy(value))
        snapshot['sources'].append(item)
        mapping['sources'][value['source_id']] = item['id']
    for value in raw.get('relationships', []):
        item = copy.deepcopy(value)
        identifier = value['relationship_id']
        grade = {'company_confirmed': 'primary_explicit', 'institutional_estimate': 'attributed_explicit'}.get(value.get('evidence_grade'), 'lead_unresolved')
        claim_id = 'legacy-claim:' + identifier
        item.update(id=identifier, source_id=value['source_company_id'], target_id=value['target_company_id'], type=value['relationship_type'], evidence_grade=grade, direction='undirected', direction_review_status='legacy_indexing_direction_unreviewed', product=None, project_id=None, batch_id=batch_id, claim_ids=[claim_id], legacy_retention=value.get('retention'), legacy=copy.deepcopy(value))
        # Retain all records, including excluded/context. Graph visibility is separate.
        snapshot['relationships'].append(item)
        claim = {'id': claim_id, 'relationship_id': identifier, 'subject_id': item['source_id'], 'object_id': item['target_id'], 'predicate': item['type'], 'text': value['description'], 'evidence_grade': grade, 'source_ids': value.get('source_ids', []), 'locator': 'Legacy atlas description; see each cited source reviewed_sections and evidence card', 'supporting_text': value['description'], 'known_from': value.get('historical_usable_from') or value.get('known_from'), 'date_precision': 'day' if value.get('historical_usable_from') or value.get('known_from') else 'unknown', 'valid_from': value.get('valid_from'), 'valid_to': value.get('valid_to'), 'terms': [], 'supersedes_id': None, 'conflict_with_ids': [], 'review_status': 'legacy_documentary_paraphrase_requires_claim_level_review', 'batch_id': batch_id}
        if value.get('materiality_value') is not None:
            claim['terms'].append({'value': value['materiality_value'], 'unit': value.get('materiality_unit'), 'period': value.get('materiality_period'), 'scope': value.get('scope'), 'known_from': value.get('materiality_usable_from'), 'source_ids': value.get('source_ids', []), 'date_precision': 'day' if value.get('materiality_usable_from') else 'unknown', 'legacy_notes': value.get('materiality_notes'), 'historical_certified': False})
        snapshot['claims'].append(claim)
        mapping['relationships'][identifier] = identifier
        if grade == 'lead_unresolved' or value.get('retention') == 'excluded':
            snapshot['frontier'].append({'id': 'legacy-lead:' + identifier, 'company_id': value.get('counterparty_id'), 'project_id': None, 'facet': TYPE_FACET.get(value['relationship_type'], 'collaboration_dependencies'), 'status': 'excluded' if value.get('retention') == 'excluded' else 'pending', 'local_depth': max(len(value.get('path', [])) - 1, 0), 'root_id': value.get('anchor_id'), 'parent_frontier_id': None, 'reason': value['description'], 'source_ids': value.get('source_ids', []), 'next_action': 'Review explicit evidence and legacy retention decision before any graph admission.', 'batch_id': batch_id, 'legacy': copy.deepcopy(value)})
    for index, value in enumerate(raw.get('screening', [])):
        # Screening is an audit trail, not new asserted relationships.
        snapshot['coverage'].append({'id': f'legacy-screening:{index}', 'kind': 'screening', 'legacy': copy.deepcopy(value), **copy.deepcopy(value)})
    for index, value in enumerate(raw.get('document_review', [])):
        snapshot['coverage'].append({'id': f'legacy-document:{index}', 'kind': 'document_review', **copy.deepcopy(value)})
    for index, value in enumerate(raw.get('gaps', [])):
        snapshot['coverage'].append({'id': f'legacy-gap:{index}', 'kind': 'gap', **copy.deepcopy(value)})
    for company in snapshot['companies']:
        for facet in FACETS:
            snapshot['frontier'].append({'id': f"frontier:{company['id']}:{facet}", 'company_id': company['id'], 'project_id': None, 'facet': facet, 'status': 'pending', 'local_depth': 0, 'root_id': company['id'], 'parent_frontier_id': None, 'reason': 'Company-neutral branch checklist not yet completed. Existing atlas evidence does not certify full branch coverage.', 'source_ids': [], 'next_action': 'Select this branch in a bounded research batch; enumerate explicit names before deeper investigation.', 'batch_id': batch_id})
    snapshot['batches'].append({'id': batch_id, 'batch_id': batch_id, 'name': 'Existing six-company atlas migration', 'cutoff': raw.get('as_of'), 'mode': 'migration', 'created_at': now(), 'legacy_counts': {key: len(raw.get(key, [])) for key in ('companies', 'instruments', 'sources', 'relationships')}, 'mapping': mapping, 'content_hash': digest(raw)})
    snapshot['meta'] = {'seeded': True, 'source_cutoff': raw.get('as_of'), 'anchors': raw.get('anchors', []), 'legacy_original': raw, 'scope_note': 'Research and visualization only. No new company research, return experiments, or trading tests.'}
    return snapshot
