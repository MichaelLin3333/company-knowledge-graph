"""Daily replay math, missing-data semantics and isolation; no market-data requests."""
import copy
import threading
import time
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.daily_prices import DailyPrices, primary_instruments
from backend.app import create_app
from backend.store import digest, empty_snapshot


def instrument(company):
    return {'id': 'i-'+company, 'company_id': company, 'ticker': company, 'currency': 'USD', 'is_primary': True}


def bar(day, close, adjusted=None, volume=100):
    return {'day': day, 'close': close, 'adjusted_close': adjusted if adjusted is not None else close, 'volume': volume}


def sample(service):
    companies = [{'id': i, 'name': i} for i in ['AAPL', 'SUP', 'PRIVATE']]
    instruments = {i: instrument(i) for i in ['AAPL', 'SUP']}
    service.ingest(instruments['AAPL'], [bar('2025-01-02', 100), bar('2025-01-03', 110)])
    service.ingest(instruments['SUP'], [bar('2025-01-02', 200), bar('2025-01-03', 210)])
    return companies, instruments


def test_close_change_relative_percentage_points_and_private(tmp_path):
    s = DailyPrices(tmp_path); companies, instruments = sample(s)
    result = s.day(companies, instruments, '2025-01-03', 'AAPL')
    rows = {r['company_id']: r for r in result['prices']}
    assert rows['AAPL']['change_pct'] == pytest.approx(10)
    assert rows['SUP']['change_pct'] == pytest.approx(5)
    assert rows['SUP']['vs_apple_pp'] == pytest.approx(-5)
    assert rows['PRIVATE']['change_pct'] is None
    assert result['counts'] == {'companies':3,'priced':2,'up':2,'down':0,'flat':0,'unavailable':1,'comparable_with_apple':2}


def test_missing_day_never_forward_filled_or_flat(tmp_path):
    s = DailyPrices(tmp_path); companies, instruments = sample(s)
    r = s.day(companies, instruments, '2025-01-04', 'AAPL')
    assert r['counts']['priced'] == 0 and r['counts']['flat'] == 0
    assert all(row['close'] is None and row['change_pct'] is None for row in r['prices'])


def test_relative_requires_same_prior_session(tmp_path):
    s = DailyPrices(tmp_path); companies, instruments = sample(s)
    s.ingest(instruments['SUP'], [bar('2025-01-01',200),bar('2025-01-03',210)])
    row = s.day(companies,instruments,'2025-01-03','AAPL')['prices'][1]
    assert row['change_pct'] == pytest.approx(5)
    assert row['vs_apple_pp'] is None and not row['aligned_with_apple']


def test_adjusted_basis_and_first_observation(tmp_path):
    s=DailyPrices(tmp_path);i=instrument('AAPL')
    s.ingest(i,[bar('2025-01-02',100,98),bar('2025-01-03',99,99)])
    c=[{'id':'AAPL'}];ins={'AAPL':i}
    assert s.day(c,ins,'2025-01-03','AAPL','close')['apple_change_pct'] == pytest.approx(-1)
    assert s.day(c,ins,'2025-01-03','AAPL','adjusted')['apple_change_pct'] == pytest.approx(100*(99/98-1))
    assert s.day(c,ins,'2025-01-02','AAPL')['prices'][0]['availability'] == 'no_previous_close'


def test_zero_volume_not_a_traded_daily_observation(tmp_path):
    s=DailyPrices(tmp_path);i=instrument('AAPL')
    s.ingest(i,[bar('2025-01-02',100),bar('2025-01-03',100,volume=0),bar('2025-01-06',101)])
    assert len(s.timeline(i)) == 2
    assert s.day([{'id':'AAPL'}],{'AAPL':i},'2025-01-06','AAPL')['apple_previous_date'] == '2025-01-02'


def test_refresh_failure_keeps_existing_history(tmp_path):
    def fail(_):raise RuntimeError('fictional outage')
    s=DailyPrices(tmp_path,fetcher=fail);companies,instruments=sample(s)
    before=s.timeline(instruments['AAPL'])
    result=s._refresh_one(instruments['AAPL'])
    assert result['error'] and s.timeline(instruments['AAPL']) == before
    row=s.day(companies,instruments,'2025-01-03','AAPL')['prices'][0]
    assert row['change_pct'] == pytest.approx(10) and row['refresh_error']


def test_own_primary_line_no_parent_or_adr_duplication():
    s={'instruments':[instrument('PARENT'),{**instrument('PARENT'),'id':'secondary','ticker':'PARENT.ADR','is_primary':False}]}
    r=primary_instruments(s,['PARENT','CHILD'])
    assert len(r)==1 and r['PARENT']['ticker']=='PARENT' and 'CHILD' not in r


def test_refresh_deduplicates_active_jobs_and_cache(tmp_path):
    calls=[];ready=threading.Event()
    def fetch(i):
        calls.append(i['id']);ready.wait(3)
        return [bar('2025-01-02',100),bar('2025-01-03',101)],{}
    s=DailyPrices(tmp_path,fetcher=fetch);ins={'AAPL':instrument('AAPL')}
    first=s.refresh(ins);second=s.refresh(ins)
    assert first['running'] and second['started_at']==first['started_at']
    ready.set()
    for _ in range(100):
        if not s.status(ins)['job']['running']:break
        time.sleep(.01)
    assert calls==['i-AAPL']
    assert not s.refresh(ins)['running'] and s.status(ins)['job']['total']==0


def test_full_network_route_bypasses_explorer_cap_without_mutating_research(tmp_path):
    app=create_app(tmp_path,seed_path=tmp_path/'no-seed.json')
    with TestClient(app) as c:
        c.get('/api/health')
        snapshot=empty_snapshot()
        snapshot['companies']=[{'id':i,'name':i,'status':'public'} for i in ['AAPL']+[f'C{i}' for i in range(120)]]
        snapshot['relationships']=[{'id':'r'+str(i),'source_id':'AAPL','target_id':f'C{i}','type':'upstream_supplier','evidence_grade':'primary_explicit','status':'operational'} for i in range(120)]
        app.state.store.commit_snapshot(snapshot,'Fictional isolated fixture')
        before=digest(app.state.store.snapshot());revision=app.state.store.revision()
        assert len(c.get('/api/graph?root=AAPL').json()['nodes'])==100
        result=c.get('/api/market/network').json()
        assert len(result['nodes'])==121 and result['hidden_nodes']==0 and len(result['edges'])==120
        assert c.get('/api/market/day?date=2025-01-04').json()['counts']['unavailable']==121
        assert c.get('/api/market/day?date=wrong').status_code==422
        assert c.get('/api/market/day?date=2025-01-04&basis=bad').status_code==422
        assert digest(app.state.store.snapshot())==before and app.state.store.revision()==revision
