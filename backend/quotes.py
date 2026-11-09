"""Selected-instrument Yahoo observations, isolated from research revisions.

No automatic graph-wide downloads, price signal calculations, or broker services.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import json,math,sqlite3,threading,time
from typing import Callable

TTL_SECONDS=900
_NETWORK_LIMIT=threading.BoundedSemaphore(2)

class QuoteService:
    def __init__(self,data_dir=None,*,fetcher:Callable|None=None,clock:Callable|None=None):
        self.data_dir=Path(data_dir or Path(__file__).resolve().parents[1]/'data')
        self.data_dir.mkdir(parents=True,exist_ok=True)
        self.path=self.data_dir/'quotes.sqlite3'
        self.fetcher=fetcher or self._fetch_yahoo
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self._guard=threading.Lock();self._locks={}
        with self._connect() as db:db.execute('CREATE TABLE IF NOT EXISTS quotes (instrument_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')

    def _connect(self):return sqlite3.connect(self.path,timeout=15)
    @staticmethod
    def _key(i):return str(i.get('id') or i.get('instrument_id') or i.get('ticker') or '')
    @staticmethod
    def _parse(s):return datetime.fromisoformat(s.replace('Z','+00:00')) if s else None
    def _read(self,key):
        with self._connect() as db:row=db.execute('SELECT payload FROM quotes WHERE instrument_id=?',(key,)).fetchone()
        return json.loads(row[0]) if row else None
    def get_cached(self,instrument):
        result=self._read(self._key(instrument))
        if not result:return None
        result['cached']=True
        result['stale']=bool(result.get('error')) or self.clock()>=self._parse(result.get('cache_expires_at'))
        return result
    def _save(self,key,payload):
        with self._connect() as db:db.execute('INSERT INTO quotes VALUES (?,?) ON CONFLICT(instrument_id) DO UPDATE SET payload=excluded.payload',(key,json.dumps(payload,ensure_ascii=False)))

    def refresh(self,instrument,force=False):
        key=self._key(instrument)
        if not key or not instrument.get('ticker'):raise ValueError('A verified listed instrument is required.')
        with self._guard:lock=self._locks.setdefault(key,threading.Lock())
        # Serializing a ticker also deduplicates simultaneous requests after a completed fetch.
        request_started=self.clock()
        with lock:
            old=self.get_cached(instrument)
            if old and not old['stale'] and (not force or self._parse(old.get('retrieved_at'))>=request_started):return old
            now=self.clock()
            try:
                with _NETWORK_LIMIT:result=self.fetcher(instrument)
                now=self.clock()
                price=float(result['price'])
                if not math.isfinite(price) or price<=0:raise ValueError('Provider returned no valid positive price.')
                if result.get('observation_type')=='provider_regular_market' and not result.get('observed_at'):raise ValueError('Provider observation has no defensible timestamp.')
                if result.get('observation_type')=='daily_close' and not result.get('observation_date'):raise ValueError('Daily close has no session date.')
                quote={**result,'instrument_id':key,'ticker':instrument['ticker'],'price':price,
                    'currency':result.get('currency') or instrument.get('currency'),'exchange':result.get('exchange') or instrument.get('exchange'),
                    'observed_at':result.get('observed_at'),'observation_date':result.get('observation_date'),
                    'retrieved_at':now.isoformat(),'cache_expires_at':(now+timedelta(seconds=TTL_SECONDS)).isoformat(),
                    'stale':False,'cached':False,'error':None,'provider':'Yahoo Finance via yfinance',
                    'note':'Provider observation, potentially delayed. Graph evidence and quote timestamps are independent. Currency units are preserved; no ADR conversion.'}
                self._save(key,quote);return quote
            except Exception as exc:
                error=f'{type(exc).__name__}: {str(exc)[:250]}'
                if old:
                    result={**old,'stale':True,'cached':True,'error':error,'last_attempt_at':now.isoformat()}
                    self._save(key,result);return result
                return dict(instrument_id=key,ticker=instrument['ticker'],price=None,currency=instrument.get('currency'),exchange=instrument.get('exchange'),
                    observed_at=None,observation_date=None,date_precision='unknown',observation_type='unavailable',retrieved_at=None,
                    last_attempt_at=now.isoformat(),cache_expires_at=None,stale=True,cached=False,error=error,provider='Yahoo Finance via yfinance')

    def _fetch_yahoo(self,instrument):
        import yfinance as yf
        yf.set_tz_cache_location(str(self.data_dir/'yfinance_cache'))
        ticker=yf.Ticker(instrument['ticker'])
        # fast_info fields without an observed timestamp are deliberately not used.
        info={}
        try:info=ticker.get_info() or {}
        except Exception:pass
        value=info.get('regularMarketPrice');stamp=info.get('regularMarketTime')
        if value is not None and stamp:
            observed=datetime.fromtimestamp(float(stamp),timezone.utc)
            if observed>self.clock()+timedelta(minutes=5):raise ValueError('Provider timestamp is unexpectedly in the future.')
            return dict(price=value,currency=info.get('currency'),exchange=info.get('fullExchangeName') or info.get('exchange'),
                observed_at=observed.isoformat(),observation_date=observed.date().isoformat(),date_precision='second',observation_type='provider_regular_market')
        frame=ticker.history(period='5d',interval='1d',auto_adjust=False,actions=False,prepost=False,repair=False,keepna=True,timeout=12)
        if frame.empty or 'Close' not in frame:raise ValueError('No price history returned.')
        metadata={}
        try:metadata=dict(ticker.get_history_metadata() or {})
        except Exception:pass
        tz_name=metadata.get('exchangeTimezoneName') or info.get('exchangeTimezoneName')
        try:today=self.clock().astimezone(ZoneInfo(tz_name)).date() if tz_name else self.clock().date()
        except Exception:today=self.clock().date()
        # A daily bar dated today can still be moving. Only older dates are unambiguously completed.
        valid=frame.loc[[x.date()<today for x in frame.index]].dropna(subset=['Close'])
        if valid.empty:raise ValueError('No completed prior daily close was available.')
        last=valid.iloc[-1];day=valid.index[-1].date().isoformat()
        return dict(price=float(last['Close']),currency=metadata.get('currency') or info.get('currency'),
            exchange=metadata.get('fullExchangeName') or metadata.get('exchangeName') or info.get('exchange'),
            observed_at=None,observation_date=day,date_precision='date',observation_type='daily_close')
