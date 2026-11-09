"""Known-factor recovery, timing boundaries and nonpublishing visual controls."""
from datetime import date,timedelta
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.daily_prices import DailyPrices
from backend.market_factors import BENCHMARKS,control_universe,fit_two_factor,market_adjustments
from backend.store import empty_snapshot,digest


def fixture_prices(tmp_path,observations=300):
    service=DailyPrices(tmp_path)
    rng=np.random.default_rng(84)
    spy=rng.normal(0,.8,observations)
    xlk=1.2*spy+rng.normal(0,.5,observations)
    target=.03+.8*spy+.4*xlk
    target[-1]+=.7
    company={'id':'company-AAPL','ticker':'AAPL'}
    def bars(returns):
        close=100.;rows=[{'day':'2024-01-01','close':close,'adjusted_close':close}]
        for index,value in enumerate(returns,1):
            close*=1+value/100
            rows.append({'day':(date(2024,1,1)+timedelta(days=index)).isoformat(),'close':close,'adjusted_close':close})
        return rows
    source={company['id']:bars(target),BENCHMARKS['SPY']['id']:bars(spy),BENCHMARKS['XLK']['id']:bars(xlk)}
    for i in [company,*BENCHMARKS.values()]:service.ingest(i,source[i['id']])
    return service,company,source,spy,xlk


def test_orthogonalized_fit_matches_joint_two_factor_OLS():
    rng=np.random.default_rng(12);spy=rng.normal(size=252);xlk=1.5*spy+rng.normal(scale=.1,size=252)
    y=.04+.7*spy+.3*xlk
    result=fit_two_factor(y,spy,xlk,.5,.8)
    assert result['alpha_pct']==pytest.approx(.04,abs=1e-10)
    assert result['beta_spy']==pytest.approx(.7,abs=1e-10)
    assert result['beta_xlk']==pytest.approx(.3,abs=1e-10)
    assert result['expected_pct']==pytest.approx(.04+.7*.5+.3*.8)


def test_current_shock_excluded_from_fit_and_known_residual_recovered(tmp_path):
    service,company,source,spy,xlk=fixture_prices(tmp_path)
    selected=source[company['id']][-1]['day']
    result,meta=market_adjustments(service,{'AAPL':company},selected,'close')
    row=result[company['id']]
    assert row['market_adjusted_pp']==pytest.approx(.7,abs=1e-8)
    assert row['market_fit_observations']==252 and row['market_fit_end']<selected
    assert row['market_beta_spy']==pytest.approx(.8,abs=1e-8)
    assert row['market_beta_xlk']==pytest.approx(.4,abs=1e-8)
    assert not meta['fitting_uses_selected_or_future_return']


def test_future_bars_do_not_change_historical_adjustment(tmp_path):
    service,company,source,_,_=fixture_prices(tmp_path)
    selected=source[company['id']][-2]['day']
    before=market_adjustments(service,{'AAPL':company},selected,'close')[0][company['id']]
    for i in [company,*BENCHMARKS.values()]:
        rows=source[i['id']]+[{'day':'2030-01-01','close':9999,'adjusted_close':1}]
        service.ingest(i,rows)
    after=market_adjustments(service,{'AAPL':company},selected,'close')[0][company['id']]
    assert before==after


def test_short_history_and_singular_factors_are_unresolved(tmp_path):
    service,company,source,_,_=fixture_prices(tmp_path,80)
    result=market_adjustments(service,{'AAPL':company},source[company['id']][-1]['day'],'close')[0][company['id']]
    assert result['market_adjusted_pp'] is None and 'Insufficient' in result['market_reason']
    spy=np.arange(150,dtype=float)
    assert fit_two_factor(spy,spy,2*spy,1,2) is None


def test_market_return_window_mismatch_is_not_colored(tmp_path):
    service,company,source,_,_=fixture_prices(tmp_path)
    rows=source[company['id']];service.ingest(company,rows[:-2]+rows[-1:])
    result=market_adjustments(service,{'AAPL':company},rows[-1]['day'],'close')[0][company['id']]
    assert result['market_adjusted_pp'] is None and 'prior-session' in result['market_reason']


def test_controls_unique_different_industries_and_no_graph_mutation(tmp_path):
    companies,instruments,policy=control_universe()
    assert len(companies)==len(instruments)==30
    assert len({c['industry'] for c in companies})==10
    assert len({i['ticker'] for i in instruments.values()})==30
    app=create_app(tmp_path/'app',seed_path=tmp_path/'none.json')
    with TestClient(app) as client:
        client.get('/api/health');snapshot=empty_snapshot()
        snapshot['companies']=[{'id':'AAPL','name':'Apple','status':'public'}]
        snapshot['instruments']=[{'id':'i-aapl','company_id':'AAPL','ticker':'AAPL','is_primary':True}]
        app.state.store.commit_snapshot(snapshot,'Isolated fictional fixture')
        before=digest(app.state.store.snapshot());revision=app.state.store.revision()
        response=client.get('/api/market/network?panel=controls').json()
        assert len(response['nodes'])==31 and response['edges']==[]
        assert response['panel']=='controls' and response['control_policy']['statistical_status']
        assert client.get('/api/market/day?panel=controls&date=2025-01-02').status_code==200
        assert client.get('/api/market/network?panel=arbitrary').status_code==422
        assert digest(app.state.store.snapshot())==before and app.state.store.revision()==revision
