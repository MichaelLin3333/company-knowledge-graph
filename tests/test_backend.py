"""Temporary-database acceptance tests: no external research or price requests."""
import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.store import digest


@pytest.fixture
def seed(tmp_path):
    data = {'as_of': '2026-10-24', 'anchors': [{'id': 'A', 'name': 'Alpha'}],
            'companies': [{'company_id': identifier, 'name': name, 'country': 'United States', 'public_private': 'public' if identifier != 'C' else 'private', 'parent_id': None, 'economic_confirmation_group_id': identifier, 'affiliated_inference_cluster': identifier} for identifier, name in [('A', 'Alpha'), ('B', 'Beta'), ('C', 'Gamma')]],
            'instruments': [{'company_id': 'A', 'ticker': 'ALPHA', 'is_primary': True, 'declared_exchange': 'TEST', 'declared_currency': 'USD'}, {'company_id': 'A', 'ticker': 'ALPHA.ADR', 'is_primary': False}],
            'sources': [{'source_id': 'S1', 'title': 'Fixture annual filing', 'publisher': 'Fictional Fixture Company', 'url': 'https://example.invalid/fixture', 'published_date': '2025-01-01', 'reviewed_sections': ['Note 1']}],
            'relationships': [{'relationship_id': identifier, 'source_company_id': left, 'target_company_id': right, 'counterparty_id': right, 'anchor_id': 'A', 'relationship_type': 'upstream_supplier', 'description': 'Explicit fixture supply disclosure', 'scope': 'Fictional fixture', 'evidence_grade': 'company_confirmed', 'status': 'operational', 'retention': 'primary_candidate', 'source_ids': ['S1'], 'historical_usable_from': '2025-01-01', 'known_from': '2025-01-01', 'path': ['A', left, right]} for identifier, left, right in [('R1', 'A', 'B'), ('R2', 'B', 'C')]],
            'screening': [], 'document_review': [], 'gaps': []}
    path = tmp_path / 'seed.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    return path


@pytest.fixture
def client(tmp_path, seed):
    application = create_app(tmp_path / 'database', seed)
    with TestClient(application) as test_client:
        yield test_client


def batch(client, **updates):
    result = {'schema_version': '1.0', 'batch_id': 'fixture-batch-1', 'name': 'Fictional test research', 'base_revision': client.get('/api/health').json()['revision'], 'cutoff': '2026-10-24', 'mode': 'company', 'root_company_ids': ['A'], 'root_project_ids': [], 'max_additional_hops': 2, 'investigated_company_ids': ['A'], 'investigated_project_ids': [], 'companies': [], 'instruments': [], 'sources': [], 'relationships': [], 'claims': [], 'projects': [], 'participations': [], 'frontier': [], 'coverage': [], 'supersedes_claim_ids': [], 'research_log': []}
    result.update(updates)
    return result


def connection(identifier='R3', source='A', target='D', product=None):
    return {'id': identifier, 'source_id': source, 'target_id': target, 'type': 'upstream_supplier', 'description': 'Fictional explicitly documented relationship', 'status': 'operational', 'evidence_grade': 'primary_explicit', 'direction': 'directed', 'direction_review_status': 'reviewed', 'scope': 'Fictional', 'product': product, 'known_from': '2026-01-01', 'claim_ids': ['C3']}


def evidence(identifier='C3', relation='R3', source='A', target='D'):
    return {'id': identifier, 'relationship_id': relation, 'subject_id': source, 'object_id': target, 'predicate': 'buys_from', 'text': 'Fictional claim', 'evidence_grade': 'primary_explicit', 'source_ids': ['S1'], 'locator': 'Fixture section 1', 'supporting_text': 'Fictional source explicitly identifies the parties.', 'known_from': '2026-01-01', 'date_precision': 'day', 'terms': [], 'conflict_with_ids': []}


def expanded(client, **updates):
    values = {'companies': [{'id': 'D', 'name': 'Delta', 'status': 'private', 'country': 'Japan'}], 'relationships': [connection()], 'claims': [evidence()]}
    values.update(updates)
    return batch(client, **values)


def validate(client, value):
    response = client.post('/api/batches/validate', json=value)
    assert response.status_code == 200, response.text
    return response.json()


def publish(client, value):
    proposal = validate(client, value)
    assert proposal['valid'], proposal['errors']
    response = client.post(f'/api/batches/{proposal["proposal_id"]}/publish', json={'base_revision': value['base_revision']})
    assert response.status_code == 200, response.text
    return response.json()


def test_migration_is_lossless_and_never_infers_arrows(client, seed):
    health = client.get('/api/health').json()
    assert health['counts']['companies'] == 3
    assert health['counts']['relationships'] == 2
    exported = client.get('/api/export').json()
    raw = json.loads(seed.read_text(encoding='utf-8'))
    assert exported['snapshot']['meta']['legacy_original'] == raw
    assert all(row['direction'] == 'undirected' for row in exported['snapshot']['relationships'])
    assert len(exported['snapshot']['instruments']) == 2
    assert len(exported['snapshot']['companies']) == 3
    assert client.get('/api/companies/C').json()['quote'] is None


def test_neighborhood_hops_and_no_transitive_shortcut(client):
    one = client.get('/api/graph?root=A').json()
    assert {row['id'] for row in one['nodes']} == {'A', 'B'}
    two = client.get('/api/graph?root=A&depth=2').json()
    assert {row['id'] for row in two['nodes']} == {'A', 'B', 'C'}
    assert len(two['edges']) == 2
    assert not any({row['source_id'], row['target_id']} == {'A', 'C'} for row in two['edges'])
    assert client.get('/api/relationships?root=A&depth=2&limit=1').json()['total'] == 2


def test_filters_dates_and_root_retention(client):
    assert len(client.get('/api/graph?root=A&as_of=2024-12-31').json()['edges']) == 0
    assert len(client.get('/api/graph?root=A&as_of=2025-01-01').json()['edges']) == 1
    assert client.get('/api/graph?root=A&types=competitor').json()['nodes'][0]['id'] == 'A'
    assert client.get('/api/graph?root=A&as_of=broken').status_code == 422
    assert client.get('/api/graph?root=missing').status_code == 404


def test_validation_is_nonpublishing_atomic_and_idempotent(client):
    before = client.get('/api/export').json()
    value = expanded(client)
    proposal = validate(client, value)
    assert proposal['valid'], proposal['errors']
    assert client.get('/api/export').json() == before
    result = publish(client, value)
    assert result['revision'] == before['revision'] + 1
    assert client.get('/api/companies/D').status_code == 200
    same = validate(client, value)
    assert same['valid'] and same['idempotent']
    again = client.post(f'/api/batches/{same["proposal_id"]}/publish', json={'base_revision': value['base_revision']}).json()
    assert again['idempotent']
    assert again['revision'] == result['revision']
    value['name'] = 'Changed same identifier'
    assert not validate(client, value)['valid']


def test_invalid_import_changes_no_records_or_revision(client):
    value = expanded(client)
    value['claims'][0]['supporting_text'] = ''
    before = client.get('/api/export').json()
    proposal = validate(client, value)
    assert not proposal['valid']
    response = client.post(f'/api/batches/{proposal["proposal_id"]}/publish', json={'base_revision': value['base_revision']})
    assert response.status_code == 422
    assert client.get('/api/export').json() == before


def test_stale_publish_and_restore_preserve_history(client):
    value = expanded(client)
    proposal = validate(client, value)
    nomination = publish(client, batch(client, batch_id='intervening-fixture'))
    assert client.post(f'/api/batches/{proposal["proposal_id"]}/publish', json={'base_revision': value['base_revision']}).status_code == 409
    restored = client.post('/api/revisions/1/restore', json={'base_revision': nomination['revision']})
    assert restored.status_code == 200
    assert restored.json()['revision'] == 3
    assert len(client.get('/api/revisions').json()['items']) == 3
    assert client.post('/api/revisions/1/restore', json={'base_revision': 1}).status_code == 409


def test_quotas_depth_and_unlimited_enumeration(client):
    value = expanded(client, investigated_company_ids=[f'TOO_MANY_{index}' for index in range(26)])
    assert not validate(client, value)['valid']
    value = expanded(client, companies=[{'id': 'D', 'name': 'Delta'}], relationships=[connection(source='C')], claims=[evidence(source='C')])
    result = validate(client, value)
    assert not result['valid'] and any('two explicit company hops' in error for error in result['errors'])
    names = [{'id': f'ENUM{i}', 'name': f'Enumerated company {i}', 'status': 'private'} for i in range(80)]
    relations, claims = [], []
    for i, company in enumerate(names):
        relation = connection(identifier=f'ER{i}', target=company['id'])
        relation['claim_ids'] = [f'EC{i}']
        relations.append(relation)
        claims.append(evidence(identifier=f'EC{i}', relation=f'ER{i}', target=company['id']))
    assert validate(client, batch(client, companies=names, relationships=relations, claims=claims))['valid']


@pytest.mark.parametrize('change,fragment', [
    (lambda value: value['relationships'][0].update(evidence_grade='lead_unresolved'), 'primary_explicit'),
    (lambda value: value['claims'][0].update(object_id='C'), 'subject/object'),
    (lambda value: value['relationships'][0].update(product='Camera sensor'), 'product attribution'),
    (lambda value: value['claims'][0].update(known_from='2027-01-01'), 'exceeds cutoff'),
    (lambda value: value['claims'][0].update(known_from=None, date_precision='day'), 'known_from'),
    (lambda value: value['claims'][0].update(source_ids=['missing']), 'source_id'),
])
def test_claim_admission_guards(client, change, fragment):
    value = expanded(client)
    change(value)
    result = validate(client, value)
    assert not result['valid'] and any(fragment in error for error in result['errors'])


def test_unknown_dates_retained_but_not_historical(client):
    value = expanded(client)
    value['claims'][0].update(known_from=None, date_precision='unknown')
    value['relationships'][0]['known_from'] = None
    publish(client, value)
    assert len(client.get('/api/graph?root=A').json()['edges']) == 2
    assert len(client.get('/api/graph?root=A&as_of=2026-10-24').json()['edges']) == 1


def test_share_classes_do_not_duplicate_company_and_parent_cycles_rejected(client):
    value = expanded(client, instruments=[{'id': 'D-quote', 'company_id': 'D', 'ticker': 'ALPHA'}])
    assert any('already belongs' in error for error in validate(client, value)['errors'])
    value = expanded(client, companies=[{'id': 'D', 'name': 'Delta', 'parent_id': 'E'}, {'id': 'E', 'name': 'Epsilon', 'parent_id': 'D'}])
    assert any('parent cycle' in error for error in validate(client, value)['errors'])


def test_project_roles_never_generate_participant_clique(client):
    role_claims = [{'id': f'project-role-{identifier}', 'entity_kind': 'project', 'project_id': 'P', 'company_id': identifier, 'role': 'equipment_supplier', 'relationship_id': None, 'predicate': 'project_role', 'text': 'Fictional named role', 'evidence_grade': 'primary_explicit', 'source_ids': ['S1'], 'locator': 'Fixture project section', 'supporting_text': f'Fictional facility names {identifier} as equipment supplier.', 'known_from': '2026-01-01', 'date_precision': 'day', 'terms': []} for identifier in ('A', 'B', 'C')]
    value = batch(client, mode='project', root_company_ids=[], investigated_company_ids=[], root_project_ids=['P'], investigated_project_ids=['P'], projects=[{'id': 'P', 'name': 'Fictional facility', 'source_ids': ['S1'], 'terms': []}], claims=role_claims, participations=[{'id': f'P-{identifier}', 'project_id': 'P', 'company_id': identifier, 'role': 'equipment_supplier', 'source_ids': ['S1'], 'claim_ids': [f'project-role-{identifier}']} for identifier in ('A', 'B', 'C')])
    publish(client, value)
    project = client.get('/api/projects/P').json()
    assert len(project['participations']) == 3
    assert len(project['relationships']) == 0
    graph = client.get('/api/graph?root=A&project_id=P').json()
    assert {row['id'] for row in graph['nodes']} == {'A', 'B', 'C'}
    assert graph['edges'] == []
    assert client.get('/api/health').json()['counts']['relationships'] == 2


def test_correction_supersession_and_historical_original(client):
    value = batch(client, claims=[evidence(identifier='correction', relation='R1', source='A', target='B')])
    value['claims'][0].update(supersedes_id='legacy-claim:R1', known_from='2026-02-01')
    publish(client, value)
    current = client.get('/api/graph?root=A').json()['edges'][0]
    historical = client.get('/api/graph?root=A&as_of=2025-06-01').json()['edges'][0]
    assert current['active_claim_ids'] == ['correction']
    assert historical['active_claim_ids'] == ['legacy-claim:R1']
    assert len(client.get('/api/relationships/R1').json()['claims']) == 2


def test_sourced_updates_direction_company_status_and_frontier_work_state(client):
    revised = evidence(identifier='direction-review', relation='R1', source='A', target='B')
    revised['known_from'] = '2026-02-01'
    company_claim = {'id': 'company-status', 'entity_kind': 'company', 'company_id': 'C', 'relationship_id': None, 'predicate': 'listing_status', 'text': 'Fictional status change', 'evidence_grade': 'primary_explicit', 'source_ids': ['S1'], 'locator': 'Fictional fixture section 1', 'supporting_text': 'Fictional Gamma became listed.', 'known_from': '2026-02-01', 'date_precision': 'day', 'terms': []}
    value = batch(client, claims=[revised, company_claim], record_updates=[
        {'kind': 'relationships', 'id': 'R1', 'changes': {'direction': 'directed', 'direction_review_status': 'reviewed'}, 'claim_ids': ['direction-review'], 'reason': 'Explicit role review'},
        {'kind': 'companies', 'id': 'C', 'changes': {'status': 'public'}, 'claim_ids': ['company-status'], 'reason': 'Listing update'},
        {'kind': 'frontier', 'id': 'frontier:A:supply_manufacturing', 'changes': {'status': 'completed'}, 'claim_ids': [], 'reason': 'Recorded checklist completed'},
    ])
    proposal = validate(client, value)
    assert proposal['valid'], proposal['errors']
    assert proposal['diff']['updated_records'] == 3
    publish(client, value)
    assert client.get('/api/relationships/R1').json()['relationship']['direction'] == 'directed'
    assert client.get('/api/companies/C').json()['company']['status'] == 'public'
    assert next(row for row in client.get('/api/research').json()['frontier'] if row['id'] == 'frontier:A:supply_manufacturing')['status'] == 'completed'
    assert client.get('/api/graph?root=A&as_of=2025-06-01').json()['edges'][0]['direction'] == 'undirected'
    assert client.get('/api/export?revision=1').json()['snapshot']['relationships'][0]['direction'] == 'undirected'


def test_updates_require_new_related_evidence_and_never_rewrite_endpoints(client):
    value = batch(client, record_updates=[{'kind': 'relationships', 'id': 'R1', 'changes': {'source_id': 'C'}, 'claim_ids': [], 'reason': 'Invalid shortcut rewrite'}])
    assert any('cannot change' in error for error in validate(client, value)['errors'])
    value['record_updates'][0]['changes'] = {'direction': 'directed', 'direction_review_status': 'reviewed'}
    assert any('requires new explicit' in error for error in validate(client, value)['errors'])


def test_queue_deduplication_is_nonmutating(client):
    before = client.get('/api/health').json()
    result = client.post('/api/research/frontier', json={'company_id': 'A', 'facet': 'supply_manufacturing', 'reason': 'Already queued'}).json()
    assert result['idempotent']
    after = client.get('/api/health').json()
    assert before['revision'] == after['revision']
    assert before['counts']['frontier'] == after['counts']['frontier']


def test_batch_identifiers_survive_restore(client):
    value = expanded(client)
    result = publish(client, value)
    restored = client.post('/api/revisions/1/restore', json={'base_revision': result['revision']}).json()
    assert validate(client, value)['idempotent']
    value['base_revision'] = restored['revision']
    value['name'] = 'Reusing identifier after restore'
    assert not validate(client, value)['valid']


def test_large_fixture_respects_caps_and_table_retains_all(tmp_path):
    data = {'as_of': '2026-10-24', 'companies': [{'company_id': f'N{i}', 'name': f'Company {i}', 'public_private': 'private'} for i in range(1000)], 'relationships': [], 'sources': [{'source_id': 'S', 'title': 'Fictional fixture', 'publisher': 'Test', 'url': 'https://example.invalid/test', 'published_date': '2026-01-01'}], 'instruments': []}
    for i in range(3000):
        data['relationships'].append({'relationship_id': f'R{i}', 'source_company_id': 'N0', 'target_company_id': f'N{1 + i % 999}', 'relationship_type': 'upstream_supplier', 'description': 'Explicit synthetic fixture', 'evidence_grade': 'company_confirmed', 'retention': 'primary_candidate', 'source_ids': ['S'], 'known_from': '2026-01-01'})
    seed_path = tmp_path / 'large.json'
    seed_path.write_text(json.dumps(data), encoding='utf-8')
    with TestClient(create_app(tmp_path / 'large-db', seed_path)) as current:
        graph = current.get('/api/graph?root=N0&limit_nodes=1000&limit_edges=3000').json()
        assert len(graph['nodes']) == 100 and len(graph['edges']) <= 300
        assert graph['total_nodes'] == 1000 and graph['total_edges'] == 3000
        assert graph['hidden_nodes'] == 900
        table = current.get('/api/relationships?root=N0&limit=25&offset=25').json()
        assert table['total'] == 3000 and len(table['items']) == 25
        node_ids = {row['id'] for row in graph['nodes']}
        assert all(row['source_id'] in node_ids and row['target_id'] in node_ids for row in graph['edges'])


def test_remote_origin_and_safe_download_routes(client):
    assert client.post('/api/research/frontier', headers={'origin': 'https://untrusted.example'}, json={'company_id': 'A', 'facet': 'supply_manufacturing'}).status_code == 403
    assert client.get('/api/files/backend/app.py').status_code == 404
    assert client.get('/api/files/docs/..%2F..%2Fbackend%2Fapp.py').status_code == 404
    assert client.get('/api/no-such-endpoint').status_code == 404


def test_apple_explorer_can_request_the_entire_screened_neighborhood(tmp_path):
    peers = [f'C{i}' for i in range(200)]
    data = {'companies': [{'company_id': identifier, 'name': identifier, 'public_private': 'private'}
                          for identifier in ['AAPL', *peers]],
            'sources': [{'source_id': 'S', 'title': 'Fixture', 'url': 'https://example.invalid/fixture'}],
            'relationships': [{'relationship_id': f'R{i}', 'source_company_id': 'AAPL',
                               'target_company_id': peers[i % len(peers)], 'relationship_type': 'upstream_supplier',
                               'description': 'Explicit synthetic fixture', 'evidence_grade': 'company_confirmed',
                               'retention': 'primary_candidate', 'source_ids': ['S']} for i in range(340)]}
    seed_path = tmp_path / 'apple.json'
    seed_path.write_text(json.dumps(data), encoding='utf-8')
    with TestClient(create_app(tmp_path / 'apple-db', seed_path)) as current:
        graph = current.get('/api/graph?root=AAPL&depth=1&limit_nodes=300&limit_edges=600').json()
        assert len(graph['nodes']) == 201 and len(graph['edges']) == 340
        assert graph['hidden_nodes'] == graph['hidden_edges'] == 0
        compact = current.get('/api/graph?root=AAPL').json()
        assert len(compact['nodes']) == 100 and compact['total_nodes'] == 201


def test_malformed_nested_batches_are_invalid_not_server_errors(client):
    value = expanded(client)
    value['relationships'][0]['source_id'] = ['not', 'an', 'id']
    assert not validate(client, value)['valid']
    value = expanded(client)
    value['claims'][0]['conflict_with_ids'] = [[]]
    assert not validate(client, value)['valid']


def test_materiality_terms_need_field_level_dates_units_and_sources(client):
    value = expanded(client)
    value['claims'][0]['terms'] = [{'value': 50, 'unit': 'percent', 'period': 'FY2026', 'scope': 'issuer revenue', 'known_from': None, 'source_ids': ['S1']}]
    assert validate(client, value)['valid']
    del value['claims'][0]['terms'][0]['known_from']
    assert not validate(client, value)['valid']


def test_attributed_reporting_cannot_be_promoted_to_primary(client):
    value = expanded(client, sources=[{'id': 'MEDIA', 'title': 'Fictional institution research', 'publisher': 'Fictional Research House', 'url': 'https://example.invalid/report', 'published_date': '2026-01-01', 'date_precision': 'day', 'document_type': 'institutional_report'}])
    value['claims'][0]['source_ids'] = ['MEDIA']
    assert any('attributed_explicit' in error for error in validate(client, value)['errors'])
    value['claims'][0]['evidence_grade'] = 'attributed_explicit'
    value['relationships'][0]['evidence_grade'] = 'attributed_explicit'
    assert validate(client, value)['valid']


@pytest.mark.parametrize('field,value', [('name', ['invalid']), ('aliases', [{}])])
def test_company_scalar_type_poisoning_rejected(client, field, value):
    candidate = expanded(client)
    candidate['companies'][0][field] = value
    assert not validate(client, candidate)['valid']
    update = batch(client, claims=[{'id': 'company-fact', 'entity_kind': 'company', 'company_id': 'A', 'relationship_id': None, 'predicate': 'identity', 'text': 'Fictional identity fact', 'evidence_grade': 'primary_explicit', 'source_ids': ['S1'], 'locator': 'Fixture note', 'supporting_text': 'Fictional identity source', 'known_from': '2026-01-01', 'date_precision': 'day'}], record_updates=[{'kind': 'companies', 'id': 'A', 'changes': {field: value}, 'claim_ids': ['company-fact'], 'reason': 'Invalid fixture update'}])
    assert not validate(client, update)['valid']


def test_relationship_type_poisoning_and_primary_promotion_rejected(client):
    value = expanded(client)
    value['relationships'][0]['type'] = ['supplies']
    assert not validate(client, value)['valid']
    value['relationships'][0]['type'] = 'supplies'
    value['claims'][0]['evidence_grade'] = 'attributed_explicit'
    assert any('attributed-only' in error for error in validate(client, value)['errors'])


def test_metadata_updates_cannot_predate_their_evidence(client):
    claim = evidence(identifier='later-status', relation='R1', source='A', target='B')
    claim.update(known_from='2020-01-01', source_ids=['LATER'])
    value = batch(client, sources=[{'id': 'LATER', 'title': 'Later status disclosure', 'publisher': 'Fictional Company', 'url': 'https://example.invalid/later', 'published_date': '2026-10-20', 'date_precision': 'day'}], claims=[claim], record_updates=[{'kind': 'relationships', 'id': 'R1', 'changes': {'status': 'cancelled'}, 'claim_ids': ['later-status'], 'reason': 'Status correction disclosed later'}])
    publish(client, value)
    assert client.get('/api/graph?root=A&as_of=2026-10-10').json()['edges'][0]['status'] == 'operational'
    assert client.get('/api/graph?root=A&as_of=2026-10-21').json()['edges'][0]['status'] == 'cancelled'


def test_project_root_union_counts_toward_five_project_limit(client):
    projects = [{'id': f'P{index}', 'name': f'Fictional project {index}', 'source_ids': ['S1']} for index in range(6)]
    value = batch(client, mode='project', root_company_ids=[], investigated_company_ids=[], root_project_ids=[row['id'] for row in projects], investigated_project_ids=[], projects=projects)
    assert any('five projects' in error for error in validate(client, value)['errors'])


def test_duplicate_new_company_names_require_identity_resolution(client):
    value = expanded(client, companies=[{'id': 'D', 'name': 'Duplicated fictional company'}, {'id': 'E', 'name': 'Duplicated fictional company'}])
    assert any('duplicates name' in error for error in validate(client, value)['errors'])


def test_project_participant_role_cannot_borrow_unrelated_project_fact(client):
    role = {'id': 'role-claim', 'entity_kind': 'project', 'company_id': 'A', 'project_id': 'P', 'role': 'equipment_supplier', 'relationship_id': None, 'predicate': 'project_role', 'text': 'Fictional supplier role', 'evidence_grade': 'primary_explicit', 'source_ids': ['S1'], 'locator': 'Fixture project note', 'supporting_text': 'Fictional Alpha supplies equipment to P.', 'known_from': '2026-01-01', 'date_precision': 'day'}
    value = batch(client, mode='project', root_company_ids=[], investigated_company_ids=[], root_project_ids=['P'], projects=[{'id': 'P', 'name': 'Fictional P', 'source_ids': ['S1']}], claims=[role], participations=[{'id': 'P-A', 'project_id': 'P', 'company_id': 'A', 'role': 'lender', 'source_ids': ['S1'], 'claim_ids': ['role-claim']}])
    assert any('atomic project-role claim' in error for error in validate(client, value)['errors'])


def test_exact_time_precision_requires_a_real_offset_timestamp(client):
    value = expanded(client)
    value['claims'][0]['date_precision'] = 'time'
    assert not validate(client, value)['valid']
    value['claims'][0]['known_from'] = '2026-01-01T12:30:00Z'
    assert validate(client, value)['valid']


def test_real_seed_import_mapping_preserves_all_legacy_records(tmp_path):
    path = Path(__file__).resolve().parents[1] / 'seed' / 'atlas.json'
    if not path.exists():
        pytest.skip('Root has not copied legacy seed yet')
    raw = json.loads(path.read_text(encoding='utf-8'))
    with TestClient(create_app(tmp_path / 'real-seed-db', path)) as current:
        exported = current.get('/api/export').json()
        snapshot = exported['snapshot']
        assert len(snapshot['companies']) == 114 and len(snapshot['relationships']) == 180
        assert snapshot['meta']['legacy_original'] == raw
        assert {row['legacy']['relationship_id'] for row in snapshot['relationships']} == {row['relationship_id'] for row in raw['relationships']}
        assert len(snapshot['batches'][0]['mapping']['relationships']) == 180
        assert current.get('/api/graph?root=AAPL').status_code == 200


def test_company_evidence_includes_clickable_source_register(client):
    before = client.get('/api/export').json()
    detail = client.get('/api/companies/A').json()
    needed = {source for claim in detail['claims'] for source in claim.get('source_ids', [])}
    assert {source['id'] for source in detail['sources']} == needed == {'S1'}
    assert detail['sources'][0]['url'] == 'https://example.invalid/fixture'
    assert client.get('/api/export').json()['manifest']['snapshot_hash'] == before['manifest']['snapshot_hash']
