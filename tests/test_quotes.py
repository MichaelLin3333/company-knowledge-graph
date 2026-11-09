from datetime import datetime,timezone,timedelta
from concurrent.futures import ThreadPoolExecutor
import time
import pytest
from backend.quotes import QuoteService

I={'id':'AAPL:NASDAQ','ticker':'AAPL','currency':'USD','exchange':'NASDAQ'}
NOW=datetime(2026,10,24,16,tzinfo=timezone.utc)

def observation(**kw):
    return dict(price=100.,currency='USD',exchange='NASDAQ',observed_at='2026-10-23T20:00:00+00:00',observation_date='2026-10-23',date_precision='second',observation_type='provider_regular_market',**kw)

def test_cache_has_distinct_observed_and_fetched_time(tmp_path):
    calls=[]
    s=QuoteService(tmp_path,fetcher=lambda i:(calls.append(i) or observation()),clock=lambda:NOW)
    a=s.refresh(I);b=s.refresh(I)
    assert len(calls)==1 and b['cached'] and not b['stale']
    assert a['observed_at']!=a['retrieved_at']
    assert a['observation_type']=='provider_regular_market'

def test_failure_retains_previous_observation_and_labels_stale(tmp_path):
    now=[NOW]
    s=QuoteService(tmp_path,fetcher=lambda i:observation(),clock=lambda:now[0]);original=s.refresh(I)
    now[0]+=timedelta(minutes=16)
    def fail(_):raise RuntimeError('provider unavailable')
    s.fetcher=fail;failed=s.refresh(I)
    assert failed['price']==100 and failed['stale']
    assert failed['observed_at']==original['observed_at'] and failed['retrieved_at']==original['retrieved_at']
    assert 'provider unavailable' in failed['error']
    assert s.get_cached(I)['stale']

def test_empty_response_is_unavailable_without_zero_price(tmp_path):
    s=QuoteService(tmp_path,fetcher=lambda i:{},clock=lambda:NOW)
    q=s.refresh(I)
    assert q['price'] is None and q['stale'] and q['observation_type']=='unavailable'
    assert s.get_cached(I) is None

def test_no_timestamp_cannot_be_misrepresented_as_live_quote(tmp_path):
    q=observation();q['observed_at']=None
    s=QuoteService(tmp_path,fetcher=lambda i:q,clock=lambda:NOW)
    assert s.refresh(I)['price'] is None

def test_daily_close_keeps_date_only_precision(tmp_path):
    q=dict(price=321.,currency='TWD',exchange='TWSE',observed_at=None,observation_date='2026-10-23',date_precision='date',observation_type='daily_close')
    s=QuoteService(tmp_path,fetcher=lambda i:q,clock=lambda:NOW)
    out=s.refresh({'id':'TSMC:TWSE','ticker':'2330.TW','currency':'TWD'})
    assert out['observed_at'] is None and out['observation_date']=='2026-10-23'
    assert out['currency']=='TWD' and out['price']==321.

def test_preserves_minor_currency_unit_and_adr_identity(tmp_path):
    q=observation();q['currency']='GBp';q['price']=1200
    s=QuoteService(tmp_path,fetcher=lambda i:q,clock=lambda:NOW)
    out=s.refresh({'id':'issuer:london','ticker':'EXAMPLE.L','currency':'GBP'})
    assert out['currency']=='GBp' and out['price']==1200
    assert s.get_cached({'id':'issuer:adr','ticker':'EXAMPLE'}) is None

def test_concurrent_requests_deduplicate_selected_instrument(tmp_path):
    calls=[]
    def fetch(i):calls.append(i);time.sleep(.03);return observation()
    s=QuoteService(tmp_path,fetcher=fetch,clock=lambda:NOW)
    with ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(lambda _:s.refresh(I),range(5)))
    assert len(calls)==1 and all(q['price']==100 for q in results)

def test_private_company_cannot_inherit_parent_price(tmp_path):
    s=QuoteService(tmp_path,fetcher=lambda i:observation(),clock=lambda:NOW)
    with pytest.raises(ValueError):s.refresh({'id':'private','parent_id':'MSFT'})

@pytest.mark.parametrize('price',[float('nan'),float('inf'),-10,0])
def test_invalid_price_is_not_cached_as_real_value(tmp_path,price):
    q=observation();q['price']=price
    s=QuoteService(tmp_path,fetcher=lambda i:q,clock=lambda:NOW)
    assert s.refresh(I)['price'] is None
