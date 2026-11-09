"""Loopback FastAPI application for evidence-led company exploration."""
from __future__ import annotations

import copy
import json
import os
import threading
import uuid
from collections import Counter, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse

from .batches import apply_batch, as_of_record, eligible_relationship, public_date, validate_batch
from .migrate import FACETS, migration
from .store import KINDS, Store, canonical, digest, empty_snapshot, now

ROOT = Path(__file__).resolve().parents[1]


def create_app(data_dir=None, seed_path=None):
    @asynccontextmanager
    async def lifespan(_application):
        store()
        yield

    application = FastAPI(title='Company Knowledge Graph', version='1.2.0', docs_url=None, redoc_url=None, lifespan=lifespan)
    directory = Path(data_dir or os.environ.get('CKG_DATA_DIR', ROOT / 'data'))
    seed = Path(seed_path or ROOT / 'seed' / 'atlas.json')
    lock = threading.RLock()
    application.state.store = None
    application.state.quote_service = None
    application.state.daily_service = None

    def store():
        with lock:
            if application.state.store is None:
                result = Store(directory)
                if not result.revision():
                    initial = migration(seed) if seed.exists() else empty_snapshot()
                    result.commit_snapshot(initial, 'Import existing atlas without changing the original files' if seed.exists() else 'Initialize empty research graph', 'legacy-atlas-import' if seed.exists() else None)
                application.state.store = result
            return application.state.store

    def quotes():
        with lock:
            if application.state.quote_service is None:
                from .quotes import QuoteService
                application.state.quote_service = QuoteService(directory)
            return application.state.quote_service

    def daily_prices():
        with lock:
            if application.state.daily_service is None:
                from .daily_prices import DailyPrices
                application.state.daily_service = DailyPrices(directory)
            return application.state.daily_service

    def market_scope(root, panel='apple'):
        from .daily_prices import primary_instruments
        if panel not in ('apple','controls'):
            raise HTTPException(422, 'panel must be apple or controls')
        snapshot = store().snapshot()
        if panel == 'controls':
            from .market_factors import control_universe
            if root != 'AAPL':
                raise HTTPException(422, 'The visual control panel uses Apple as its reference')
            anchor = not_found(next((c for c in snapshot['companies'] if c['id']==root),None),'Reference company')
            controls, instruments, _ = control_universe()
            instruments.update(primary_instruments(snapshot,[root]))
            return snapshot, [summary(anchor,snapshot)]+controls, [], instruments
        companies, selected, rows = filtered(snapshot, root=root, depth=1)
        identifiers = sorted(selected, key=lambda i: (i != root, companies[i].get('name', i).casefold()))
        return snapshot, [summary(companies[i], snapshot) for i in identifiers], rows, primary_instruments(snapshot, identifiers)

    def not_found(value, label):
        if value is None:
            raise HTTPException(404, f'{label} not found')
        return value

    def safe_validate(payload, snapshot, revision):
        try:
            return validate_batch(payload, snapshot, revision)
        except (TypeError, ValueError, KeyError, AttributeError) as error:
            # Bad nested JSON types must produce an invalid proposal, never a partial write or HTTP 500.
            return {'valid': False, 'batch_id': payload.get('batch_id'), 'base_revision': payload.get('base_revision'), 'errors': [f'Malformed batch field types: {type(error).__name__}. Check the supplied JSON schema.'], 'warnings': [], 'diff': {key: 0 for key in (*KINDS, 'superseded_claims', 'updated_records')}, 'preview': {'nodes': [], 'edges': []}, 'coverage': {}, 'idempotent': False}

    @application.middleware('http')
    async def same_origin_mutations(request: Request, call_next):
        # No external site can use browser credentials to publish graph changes.
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            origin = request.headers.get('origin')
            if origin:
                from urllib.parse import urlparse
                host = urlparse(origin).hostname
                if host not in ('127.0.0.1', 'localhost', '::1'):
                    from fastapi.responses import JSONResponse
                    return JSONResponse({'detail': 'Mutations accept local browser origins only.'}, status_code=403)
        return await call_next(request)

    def summary(company, snapshot):
        instruments = [row for row in snapshot['instruments'] if row.get('company_id') == company['id']]
        primary = next((row for row in instruments if row.get('is_primary')), instruments[0] if instruments else {})
        return {'id': company['id'], 'name': company.get('name', company['id']), 'country': company.get('country'), 'status': company.get('status', 'unknown'), 'primary_ticker': primary.get('ticker'), 'parent_id': company.get('parent_id'), 'relationship_count': sum(eligible_relationship(row) and company['id'] in (row.get('source_id'), row.get('target_id')) for row in snapshot['relationships'])}

    def available_claim(claim, snapshot, as_of):
        known = public_date(claim.get('known_from'), claim.get('date_precision', 'day'))
        if not known or known > as_of:
            return False
        sources = {row['id']: row for row in snapshot['sources']}
        for identifier in claim.get('source_ids', []):
            source = sources.get(identifier, {})
            source_date = public_date(source.get('published_date'), source.get('date_precision', 'day'))
            if not source_date or source_date > as_of:
                return False
        return True

    def active_claims(snapshot, as_of=None):
        candidates = [row for row in snapshot['claims'] if not as_of or available_claim(row, snapshot, as_of)]
        superseded = {row.get('supersedes_id') for row in candidates if row.get('supersedes_id')}
        return [row for row in candidates if row['id'] not in superseded]

    def filtered(snapshot, root=None, depth=1, company_ids='', types='', evidence='', statuses='', country='', product='', project_id='', batch_id='', as_of=None):
        companies = {row['id']: as_of_record(row, as_of) for row in snapshot['companies']}
        if root and root not in companies:
            raise HTTPException(404, 'Root company not found')
        if as_of and not public_date(as_of):
            raise HTTPException(422, 'as_of must be an ISO calendar date')
        def values(value):
            return {part.strip() for part in value.split(',') if part.strip()}
        type_set, grade_set, status_set = values(types), values(evidence), values(statuses)
        claims = active_claims(snapshot, as_of)
        claims_by_relation = {}
        for claim in claims:
            claims_by_relation.setdefault(claim.get('relationship_id'), []).append(claim)
        candidates = []
        for original in snapshot['relationships']:
            value = as_of_record(original, as_of)
            if not eligible_relationship(value):
                continue
            if value.get('source_id') not in companies or value.get('target_id') not in companies:
                continue
            if type_set and value.get('type') not in type_set or grade_set and value.get('evidence_grade') not in grade_set or status_set and value.get('status') not in status_set:
                continue
            if product and product.lower() not in str(value.get('product') or '').lower():
                continue
            if project_id and value.get('project_id') != project_id:
                continue
            if batch_id and value.get('batch_id') != batch_id:
                continue
            if country and any(companies[identifier].get('country') != country and identifier != root for identifier in (value['source_id'], value['target_id'])):
                continue
            if as_of and not claims_by_relation.get(value['id']):
                continue
            item = copy.deepcopy(value)
            item['source_name'] = companies[item['source_id']]['name']
            item['target_name'] = companies[item['target_id']]['name']
            item['active_claim_ids'] = [row['id'] for row in claims_by_relation.get(item['id'], [])]
            candidates.append(item)
        selected = values(company_ids)
        if project_id and not selected:
            # Participants are company nodes. A shared project creates no pairwise edge.
            sources = {row['id']: row for row in snapshot['sources']}
            def participation_available(row):
                if not as_of:
                    return True
                dates = [public_date(sources.get(identifier, {}).get('published_date'), sources.get(identifier, {}).get('date_precision', 'day')) for identifier in row.get('source_ids', [])]
                known = public_date(row.get('known_from')) if row.get('known_from') else max(dates) if dates and all(dates) else None
                return bool(known and known <= as_of and dates and all(value and value <= as_of for value in dates))
            selected = {row['company_id'] for row in snapshot['participations'] if row.get('project_id') == project_id and participation_available(row)}
            selected &= set(companies)
        elif selected:
            selected &= set(companies)
            if root:
                selected.add(root)
        elif root:
            selected, frontier = {root}, {root}
            for _ in range(max(0, min(int(depth), 2))):
                neighbors = {identifier for row in candidates if row['source_id'] in frontier or row['target_id'] in frontier for identifier in (row['source_id'], row['target_id'])}
                frontier = neighbors - selected
                selected |= neighbors
        else:
            selected = {identifier for row in candidates for identifier in (row['source_id'], row['target_id'])}
        candidates = [row for row in candidates if row['source_id'] in selected and row['target_id'] in selected]
        bundles = Counter(tuple(sorted((row['source_id'], row['target_id']))) for row in candidates)
        for item in candidates:
            item['bundle_count'] = bundles[tuple(sorted((item['source_id'], item['target_id'])))]
        return companies, selected, sorted(candidates, key=lambda row: row['id'])

    @application.get('/api/health')
    def health():
        database = store()
        snapshot = database.snapshot()
        return {'status': 'ok', 'app_id': 'company_knowledge_graph', 'app_version': '1.2.0', 'instance_root': str(ROOT.resolve()), 'data_directory': str(directory.resolve()), 'revision': database.revision(), 'seeded': bool(snapshot.get('meta', {}).get('seeded')), 'counts': {key: len(snapshot[key]) for key in ('companies', 'relationships', 'sources', 'claims', 'projects', 'frontier')}, 'read_only_scope_note': 'Research batches are manually validated and published. No research or signal experiments run automatically.'}

    @application.get('/api/companies')
    def companies(q: str = '', limit: int = 30, offset: int = 0):
        snapshot = store().snapshot()
        query = q.casefold().strip()
        rows = []
        for company in snapshot['companies']:
            item = summary(company, snapshot)
            haystack = ' '.join(str(value or '') for value in (company['id'], company.get('name'), item.get('primary_ticker'), ' '.join(company.get('aliases') or [])))
            if not query or query in haystack.casefold():
                rows.append(item)
        rows.sort(key=lambda row: row['name'].casefold())
        return {'items': rows[max(offset, 0):max(offset, 0) + max(1, min(limit, 500))], 'total': len(rows)}

    @application.get('/api/options')
    def options():
        snapshot = store().snapshot()
        return {'relationship_types': sorted({row['type'] for row in snapshot['relationships']}), 'evidence_grades': ['primary_explicit', 'attributed_explicit'], 'statuses': sorted({str(row.get('status')) for row in snapshot['relationships'] if row.get('status')}), 'countries': sorted({row['country'] for row in snapshot['companies'] if row.get('country')}), 'products': sorted({row['product'] for row in snapshot['relationships'] if row.get('product')}), 'projects': [{'id': row['id'], 'name': row['name']} for row in snapshot['projects']], 'batches': [{'id': row['id'], 'name': row['name']} for row in snapshot['batches']], 'anchors': snapshot.get('meta', {}).get('anchors', []), 'revision': store().revision(), 'source_cutoff': snapshot.get('meta', {}).get('source_cutoff')}

    @application.get('/api/market/network')
    def market_network(root: str = 'AAPL', panel: str = 'apple'):
        snapshot, nodes, edges, instruments = market_scope(root,panel)
        from .market_factors import BENCHMARKS,control_universe
        service = daily_prices()
        return {'root': root, 'panel':panel, 'title':'Cross-industry controls' if panel=='controls' else 'Apple network',
                'control_policy':control_universe()[2] if panel=='controls' else None,
                'apple_node_count':len(filtered(snapshot,root=root,depth=1)[1]),
                'control_company_count':len(control_universe()[0]),
                'revision': store().revision(), 'nodes': nodes, 'edges': edges,
                'hidden_nodes': 0, 'hidden_edges': 0, 'total_nodes': len(nodes), 'total_edges': len(edges),
                'limits': {'nodes': len(nodes), 'edges': len(edges)},
                'instruments': instruments, 'cache': service.status(instruments),
                'benchmark_cache':service.status(BENCHMARKS),
                'timeline': service.timeline(instruments.get(root)),
                'scope_note': 'Visual cross-industry reference basket with Apple as a benchmark. No relationship edges are asserted; statistical independence is not established.' if panel=='controls' else 'Current documented Apple neighborhood: all direct counterparties and documented links among them. Historical prices do not reconstruct a historical relationship map.'}

    @application.get('/api/market/day')
    def market_day(date: str, root: str = 'AAPL', basis: str = 'close', panel: str = 'apple'):
        if basis not in ('close', 'adjusted'):
            raise HTTPException(422, 'basis must be close or adjusted')
        _, nodes, _, instruments = market_scope(root,panel)
        try:
            return {**daily_prices().day(nodes, instruments, date, root, basis),'panel':panel}
        except ValueError:
            raise HTTPException(422, 'date must be an ISO calendar date')

    @application.get('/api/market/status')
    def market_status(root: str = 'AAPL', panel: str = 'apple'):
        _, _, _, instruments = market_scope(root,panel)
        return daily_prices().status(instruments)

    @application.post('/api/market/refresh')
    def market_refresh(payload: dict):
        from .market_factors import BENCHMARKS
        _, _, _, instruments = market_scope(str(payload.get('root', 'AAPL')),str(payload.get('panel','apple')))
        return daily_prices().refresh({**instruments,**BENCHMARKS})

    @application.get('/api/graph')
    def graph(root: str | None = None, depth: int = 1, company_ids: str = '', types: str = '', evidence: str = '', statuses: str = '', country: str = '', product: str = '', project_id: str = '', batch_id: str = '', as_of: str | None = None, limit_nodes: int = 100, limit_edges: int = 300):
        snapshot = store().snapshot()
        companies, selected, rows = filtered(snapshot, root, depth, company_ids, types, evidence, statuses, country, product, project_id, batch_id, as_of)
        # Apple's screened direct roster is larger than the usual canvas limit.
        node_cap, edge_cap = (300, 600) if root == 'AAPL' and depth == 1 else (100, 300)
        node_limit, edge_limit = max(1, min(limit_nodes, node_cap)), max(1, min(limit_edges, edge_cap))
        identifiers = sorted(selected, key=lambda identifier: (identifier != root, companies[identifier].get('name', identifier).casefold()))[:node_limit]
        visible = set(identifiers)
        edges = [row for row in rows if row['source_id'] in visible and row['target_id'] in visible][:edge_limit]
        return {'revision': store().revision(), 'root': root, 'nodes': [summary(companies[identifier], snapshot) for identifier in identifiers], 'edges': edges, 'hidden_nodes': len(selected) - len(identifiers), 'hidden_edges': len(rows) - len(edges), 'total_nodes': len(selected), 'total_edges': len(rows), 'limits': {'nodes': node_limit, 'edges': edge_limit}, 'filter_note': 'Explicit documented relationships only; undirected legacy links require economic-direction review. Dated view excludes unknown/newer claim or source dates and is not a complete historical reconstruction.'}

    @application.get('/api/relationships')
    def relationships(root: str | None = None, depth: int = 1, company_ids: str = '', types: str = '', evidence: str = '', statuses: str = '', country: str = '', product: str = '', project_id: str = '', batch_id: str = '', as_of: str | None = None, limit: int = 50, offset: int = 0):
        snapshot = store().snapshot()
        _, _, rows = filtered(snapshot, root, depth, company_ids, types, evidence, statuses, country, product, project_id, batch_id, as_of)
        return {'items': rows[max(offset, 0):max(offset, 0) + max(1, min(limit, 500))], 'total': len(rows)}

    @application.get('/api/companies/{identifier}')
    def company_detail(identifier: str):
        snapshot = store().snapshot()
        company = not_found(next((row for row in snapshot['companies'] if row['id'] == identifier), None), 'Company')
        instruments = [row for row in snapshot['instruments'] if row.get('company_id') == identifier]
        rows = [row for row in snapshot['relationships'] if identifier in (row.get('source_id'), row.get('target_id'))]
        neighbor_ids = {item for row in rows for item in (row['source_id'], row['target_id'])} - {identifier}
        participation_ids = {row['project_id'] for row in snapshot['participations'] if row['company_id'] == identifier}
        relationship_ids = {row['id'] for row in rows}
        quote = None
        primary = next((row for row in instruments if row.get('is_primary')), instruments[0] if instruments else None)
        if primary:
            quote = quotes().get_cached(primary)
        claims = [row for row in snapshot['claims'] if row.get('relationship_id') in relationship_ids or row.get('company_id') == identifier]
        source_ids = {source_id for claim in claims for source_id in claim.get('source_ids', [])}
        return {'company': company, 'instruments': instruments, 'relationships': rows, 'neighbors': [summary(row, snapshot) for row in snapshot['companies'] if row['id'] in neighbor_ids], 'projects': [row for row in snapshot['projects'] if row['id'] in participation_ids], 'claims': claims, 'sources': [row for row in snapshot['sources'] if row['id'] in source_ids], 'gaps': [row for row in snapshot['coverage'] if row.get('kind') == 'gap' and (row.get('anchor_id') == identifier or row.get('company_id') == identifier)], 'frontier': [row for row in snapshot['frontier'] if row.get('company_id') == identifier], 'quote': quote}

    @application.get('/api/relationships/{identifier}')
    def relationship_detail(identifier: str):
        snapshot = store().snapshot()
        relation = not_found(next((row for row in snapshot['relationships'] if row['id'] == identifier), None), 'Relationship')
        claims = [row for row in snapshot['claims'] if row.get('relationship_id') == identifier]
        source_ids = {value for claim in claims for value in claim.get('source_ids', [])}
        return {'relationship': relation, 'claims': claims, 'sources': [row for row in snapshot['sources'] if row['id'] in source_ids], 'companies': [row for row in snapshot['companies'] if row['id'] in (relation['source_id'], relation['target_id'])], 'project': next((row for row in snapshot['projects'] if row['id'] == relation.get('project_id')), None)}

    @application.get('/api/projects')
    def projects():
        snapshot = store().snapshot()
        return {'items': [{**row, 'participant_count': sum(value.get('project_id') == row['id'] for value in snapshot['participations'])} for row in snapshot['projects']]}

    @application.get('/api/projects/{identifier}')
    def project_detail(identifier: str):
        snapshot = store().snapshot()
        project = not_found(next((row for row in snapshot['projects'] if row['id'] == identifier), None), 'Project')
        participants = [row for row in snapshot['participations'] if row.get('project_id') == identifier]
        company_ids = {row['company_id'] for row in participants}
        source_ids = set(project.get('source_ids', [])) | {value for row in participants for value in row.get('source_ids', [])}
        return {'project': project, 'participations': participants, 'companies': [row for row in snapshot['companies'] if row['id'] in company_ids], 'sources': [row for row in snapshot['sources'] if row['id'] in source_ids], 'relationships': [row for row in snapshot['relationships'] if row.get('project_id') == identifier], 'claims': [row for row in snapshot['claims'] if row.get('project_id') == identifier]}

    @application.get('/api/research')
    def research():
        snapshot = store().snapshot()
        return {'revision': store().revision(), 'frontier': snapshot['frontier'], 'batches': snapshot['batches'], 'coverage': snapshot['coverage'], 'summary': {'frontier_by_status': dict(Counter(row.get('status', 'pending') for row in snapshot['frontier'])), 'frontier_by_facet': dict(Counter(row.get('facet', 'unknown') for row in snapshot['frontier'])), 'coverage_records': len(snapshot['coverage']), 'completeness_note': 'Coverage describes the recorded search checklist, not the proportion of the true network discovered.'}}

    @application.post('/api/research/frontier')
    def nominate(payload: dict):
        with lock, store().connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            revision = store().revision(conn)
            if payload.get('base_revision', revision) != revision:
                raise HTTPException(409, 'Stale base_revision')
            snapshot = store().snapshot(conn=conn)
            if payload.get('facet') not in FACETS:
                raise HTTPException(422, 'Choose one of the six research branches')
            if bool(payload.get('company_id')) == bool(payload.get('project_id')):
                raise HTTPException(422, 'Choose exactly one company or project')
            field = 'company_id' if payload.get('company_id') else 'project_id'
            kind = 'companies' if field == 'company_id' else 'projects'
            if not any(row['id'] == payload[field] for row in snapshot[kind]):
                raise HTTPException(422, 'Unresolved research target')
            prior = next((row for row in snapshot['frontier'] if row.get(field) == payload[field] and row.get('facet') == payload['facet'] and row.get('status') in ('pending', 'in_progress', 'blocked')), None)
            if prior:
                return {'revision': revision, 'idempotent': True, 'item': prior}
            row = {**payload, 'id': payload.get('id') or 'lead:' + uuid.uuid4().hex, 'status': 'pending', 'local_depth': 0, 'root_id': payload[field], 'created_at': now(), 'source_ids': payload.get('source_ids', []), 'next_action': payload.get('next_action', 'Review the branch checklist in a bounded batch.')}
            row.pop('base_revision', None)
            if any(value['id'] == row['id'] for value in snapshot['frontier']):
                raise HTTPException(409, 'Frontier ID already exists')
            snapshot['frontier'].append(row)
            result = store().commit_snapshot(snapshot, f'Nominate {payload[field]} / {payload["facet"]}', conn=conn)
            return {**result, 'item': row}

    @application.post('/api/batches/validate')
    def validate(payload: dict):
        with lock, store().connection() as conn:
            snapshot = store().snapshot(conn=conn)
            revision = store().revision(conn)
            result = safe_validate(payload, snapshot, revision)
            published = conn.execute('SELECT content_hash FROM published_batches WHERE batch_id=?', (str(payload.get('batch_id') or ''),)).fetchone()
            if published:
                if published['content_hash'] == digest(payload):
                    result.update(valid=True, idempotent=True, errors=[])
                else:
                    result['valid'] = False
                    result['errors'].append('batch_id was previously published with different content; revision restoration does not free identifiers.')
            proposal_id = 'proposal:' + uuid.uuid4().hex
            result['proposal_id'] = proposal_id
            conn.execute('INSERT INTO proposals(id,batch_id,base_revision,content_hash,payload,result,created_at) VALUES(?,?,?,?,?,?,?)', (proposal_id, str(payload.get('batch_id') or ''), int(payload.get('base_revision')) if isinstance(payload.get('base_revision'), int) else -1, digest(payload), canonical(payload), canonical(result), now()))
            return result

    @application.post('/api/batches/{proposal_id}/publish')
    def publish(proposal_id: str, payload: dict):
        with lock, store().connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM proposals WHERE id=?', (proposal_id,)).fetchone()
            if not row:
                raise HTTPException(404, 'Proposal not found')
            batch = json.loads(row['payload'])
            snapshot = store().snapshot(conn=conn)
            revision = store().revision(conn)
            prior = conn.execute('SELECT content_hash FROM published_batches WHERE batch_id=?', (batch.get('batch_id'),)).fetchone()
            if prior and prior['content_hash'] != digest(batch):
                raise HTTPException(409, 'Previously published batch ID has different content')
            prior = dict(prior) if prior else next((value for value in snapshot['batches'] if value['id'] == batch.get('batch_id')), None)
            if prior and prior.get('content_hash') == digest(batch):
                return {'revision': revision, 'batch_id': batch['batch_id'], 'idempotent': True, 'counts': {key: len(snapshot[key]) for key in KINDS}}
            if payload.get('base_revision') != revision or batch.get('base_revision') != revision:
                raise HTTPException(409, 'Stale base_revision; revalidate against the active revision')
            result = safe_validate(batch, snapshot, revision)
            if not result['valid']:
                raise HTTPException(422, result['errors'])
            updated = apply_batch(batch, snapshot)
            commit = store().commit_snapshot(updated, f'Publish research batch: {batch["name"]}', batch['batch_id'], conn)
            conn.execute('INSERT INTO published_batches(batch_id,content_hash,revision) VALUES(?,?,?)', (batch['batch_id'], digest(batch), commit['revision']))
            return {**commit, 'batch_id': batch['batch_id'], 'idempotent': False, 'counts': {key: len(updated[key]) for key in KINDS}}

    @application.get('/api/revisions')
    def revisions():
        return {'items': store().revisions()}

    @application.post('/api/revisions/{revision}/restore')
    def restore(revision: int, payload: dict):
        with lock, store().connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if payload.get('base_revision') != store().revision(conn):
                raise HTTPException(409, 'Stale base_revision')
            try:
                snapshot = store().snapshot(revision, conn)
            except KeyError:
                raise HTTPException(404, 'Revision not found')
            result = store().commit_snapshot(snapshot, f'Restore revision {revision} as a new revision', conn=conn)
            return {**result, 'restored_from': revision}

    @application.get('/api/revisions/{revision}/diff')
    def revision_diff(revision: int):
        try:
            historical = store().snapshot(revision)
        except KeyError:
            raise HTTPException(404, 'Revision not found')
        current = store().snapshot()
        added, removed, changed = {}, {}, {}
        for kind in KINDS:
            old = {row['id']: row for row in historical[kind]}
            new = {row['id']: row for row in current[kind]}
            added[kind] = sorted(new.keys() - old.keys())
            removed[kind] = sorted(old.keys() - new.keys())
            changed[kind] = sorted(key for key in old.keys() & new.keys() if canonical(old[key]) != canonical(new[key]))
        return {'revision': revision, 'current_revision': store().revision(), 'added': added, 'removed': removed, 'changed': changed, 'description': 'Differences from selected revision to the current active graph.'}

    @application.get('/api/export')
    def export(revision: int | None = None):
        selected = revision or store().revision()
        try:
            snapshot = store().snapshot(selected)
        except KeyError:
            raise HTTPException(404, 'Revision not found')
        manifest = next(row for row in store().revisions() if row['revision'] == selected)
        return {'schema_version': '1.0', 'revision': selected, 'snapshot': snapshot, 'manifest': {**manifest, 'excluded': ['price cache', 'browser view state'], 'read_only_original_atlas': True}}

    @application.post('/api/instruments/{identifier}/refresh')
    def refresh(identifier: str, payload: dict):
        instrument = not_found(store().get('instruments', identifier), 'Instrument')
        try:
            return quotes().refresh(instrument, force=bool(payload.get('force', False)))
        except Exception as exc:
            prior = quotes().get_cached(instrument)
            if prior:
                return {**prior, 'stale': True, 'error': str(exc)}
            raise HTTPException(502, f'yfinance refresh failed: {exc}')

    @application.get('/api/instruments/{identifier}/quote')
    def cached_quote(identifier: str):
        instrument = not_found(store().get('instruments', identifier), 'Instrument')
        return quotes().get_cached(instrument)

    @application.get('/api/docs')
    def document_list():
        return {'items': [{'path': path.relative_to(ROOT / 'docs').as_posix(), 'title': path.stem.replace('_', ' ').replace('-', ' ').title()} for path in sorted((ROOT / 'docs').rglob('*.md'))]}

    def safe_file(category, path):
        if category not in ('docs', 'templates', 'research', 'schemas'):
            raise HTTPException(404, 'Unknown file category')
        base = (ROOT / category).resolve()
        target = (base / path).resolve()
        if not target.is_relative_to(base) or not target.is_file():
            raise HTTPException(404, 'File not found')
        return target

    @application.get('/api/docs/{path:path}', response_class=PlainTextResponse)
    def document(path: str):
        target = safe_file('docs', path)
        if target.suffix.lower() != '.md':
            raise HTTPException(404, 'Markdown document not found')
        return target.read_text(encoding='utf-8')

    @application.get('/api/files/{category}/{path:path}')
    def download_file(category: str, path: str):
        target = safe_file(category, path)
        return FileResponse(target, filename=target.name)

    @application.get('/{path:path}')
    def frontend(path: str):
        if path == 'api' or path.startswith('api/'):
            raise HTTPException(404, 'API endpoint not found')
        base = (ROOT / 'frontend' / 'dist').resolve()
        target = (base / path).resolve()
        if not target.is_relative_to(base):
            raise HTTPException(404, 'File not found')
        if target.is_file():
            return FileResponse(target)
        index = base / 'index.html'
        if index.is_file():
            return FileResponse(index)
        return PlainTextResponse('Frontend has not been built. See README for local build instructions.', status_code=503)

    return application


app = create_app()
