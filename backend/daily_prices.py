"""Cached daily observations for the graph price replay, isolated from research facts."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import math
import sqlite3
import threading
from zoneinfo import ZoneInfo


START_DATE = '2015-01-01'
TTL_SECONDS = 900


def primary_instruments(snapshot, company_ids):
    """One own instrument per legal company; never substitute its parent's shares."""
    result = {}
    for company_id in company_ids:
        candidates = [i for i in snapshot['instruments'] if i.get('company_id') == company_id and i.get('ticker')]
        if candidates:
            result[company_id] = sorted(candidates, key=lambda i: (not i.get('is_primary', False), i['id']))[0]
    return result


class DailyPrices:
    def __init__(self, data_dir, fetcher=None, clock=None):
        self.directory = Path(data_dir)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'daily_prices.sqlite3'
        self.fetcher = fetcher or self._fetch
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.guard = threading.Lock()
        self.job = None
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS daily_bars(
                    instrument_id TEXT NOT NULL, day TEXT NOT NULL, close REAL NOT NULL,
                    adjusted_close REAL, previous_day TEXT, previous_close REAL,
                    previous_adjusted_close REAL, change_pct REAL, adjusted_change_pct REAL,
                    PRIMARY KEY(instrument_id,day));
                CREATE INDEX IF NOT EXISTS daily_bar_dates ON daily_bars(day,instrument_id);
                CREATE TABLE IF NOT EXISTS daily_catalog(instrument_id TEXT PRIMARY KEY,payload TEXT NOT NULL);
            ''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def number(value):
        try:
            result = float(value)
            return result if math.isfinite(result) else None
        except (TypeError, ValueError):
            return None

    def ingest(self, instrument, records, *, retrieved_at=None, metadata=None):
        """Rows have explicit local session dates. Gaps are never filled with prices."""
        metadata = metadata or {}
        retrieved = retrieved_at or self.clock().isoformat()
        clean = {}
        for row in records:
            close = self.number(row.get('close'))
            adj = self.number(row.get('adjusted_close'))
            volume = self.number(row.get('volume'))
            if not close or close <= 0 or volume == 0:
                continue
            clean[row['day']] = (close, adj if adj and adj > 0 else None)
        values, previous = [], None
        for day, (close, adj) in sorted(clean.items()):
            prior_day, prior_close, prior_adj = previous if previous else (None, None, None)
            change = 100 * (close / prior_close - 1) if prior_close else None
            adjusted = 100 * (adj / prior_adj - 1) if adj and prior_adj else None
            values.append((instrument['id'], day, close, adj, prior_day, prior_close, prior_adj, change, adjusted))
            previous = day, close, adj
        if not values:
            raise ValueError('No valid completed daily observations were returned.')
        catalog = {'instrument_id': instrument['id'], 'ticker': instrument['ticker'],
                   'currency': metadata.get('currency') or instrument.get('currency'),
                   'exchange': metadata.get('exchange') or instrument.get('exchange'),
                   'timezone': metadata.get('timezone'), 'retrieved_at': retrieved,
                   'first_date': values[0][1], 'last_date': values[-1][1], 'rows': len(values),
                   'provider': 'Yahoo Finance via yfinance', 'error': None,
                   'observation_type': 'completed_local_session_daily_close'}
        with self.connect() as db:
            # Replace one instrument atomically. Failed refreshes never erase its prior prices.
            db.execute('DELETE FROM daily_bars WHERE instrument_id=?', (instrument['id'],))
            db.executemany('INSERT INTO daily_bars VALUES(?,?,?,?,?,?,?,?,?)', values)
            db.execute('INSERT OR REPLACE INTO daily_catalog VALUES(?,?)', (instrument['id'], json.dumps(catalog)))
        return catalog

    def _fetch(self, instrument):
        import yfinance as yf
        yf.set_tz_cache_location(str(self.directory / 'yfinance_cache'))
        ticker = yf.Ticker(instrument['ticker'])
        frame = ticker.history(start='2013-12-01', interval='1d', auto_adjust=False,
                               actions=True, repair=False, keepna=True, timeout=15, raise_errors=True)
        if frame.empty:
            raise ValueError('Provider returned no daily history for this instrument.')
        timezone_name = str(frame.index.tz) if frame.index.tz else None
        today = self.clock().astimezone(ZoneInfo(timezone_name)).date() if timezone_name else self.clock().date()
        records = []
        for stamp, row in frame.iterrows():
            # A bar dated today can still be changing; replay uses prior local dates only.
            if stamp.date() >= today:
                continue
            records.append({'day': stamp.date().isoformat(), 'close': row.get('Close'),
                            'adjusted_close': row.get('Adj Close'), 'volume': row.get('Volume')})
        metadata = ticker.get_history_metadata() or {}
        return records, {'timezone': timezone_name, 'currency': metadata.get('currency'),
                         'exchange': metadata.get('exchangeName') or metadata.get('fullExchangeName')}

    def catalogs(self):
        with self.connect() as db:
            return {row['instrument_id']: json.loads(row['payload']) for row in db.execute('SELECT * FROM daily_catalog')}

    def _refresh_one(self, instrument):
        try:
            rows, metadata = self.fetcher(instrument)
            return self.ingest(instrument, rows, metadata=metadata)
        except Exception as error:
            catalog = self.catalogs().get(instrument['id'], {
                'instrument_id': instrument['id'], 'ticker': instrument['ticker'], 'rows': 0,
                'currency': instrument.get('currency'), 'exchange': instrument.get('exchange'),
                'first_date': None, 'last_date': None, 'retrieved_at': None})
            catalog.update(error=f'{type(error).__name__}: {str(error)[:220]}', last_attempt_at=self.clock().isoformat())
            with self.connect() as db:
                db.execute('INSERT OR REPLACE INTO daily_catalog VALUES(?,?)', (instrument['id'], json.dumps(catalog)))
            return catalog

    def refresh(self, instruments, force=False):
        """Deduplicated explicit refresh. Browsing a date never downloads prices."""
        with self.guard:
            if self.job and self.job['running']:
                return dict(self.job)
            catalog = self.catalogs()
            pending = []
            for instrument in {i['id']: i for i in instruments.values()}.values():
                old = catalog.get(instrument['id'], {})
                stamp = old.get('last_attempt_at') if old.get('error') else old.get('retrieved_at')
                fresh = stamp and (self.clock() - datetime.fromisoformat(stamp)).total_seconds() < TTL_SECONDS
                if force or not fresh:
                    pending.append(instrument)
            self.job = {'running': bool(pending), 'total': len(pending), 'completed': 0,
                        'successful': 0, 'failed': 0, 'started_at': self.clock().isoformat(),
                        'finished_at': None, 'current': None}
            if pending:
                threading.Thread(target=self._worker, args=(pending,), daemon=True).start()
            return dict(self.job)

    def _worker(self, instruments):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(self._refresh_one, i): i for i in instruments}
            for future in as_completed(futures):
                result = future.result()
                with self.guard:
                    self.job['completed'] += 1
                    self.job['failed' if result.get('error') else 'successful'] += 1
                    self.job['current'] = result['ticker']
        with self.guard:
            self.job.update(running=False, finished_at=self.clock().isoformat(), current=None)

    def status(self, instruments):
        catalogs = self.catalogs()
        rows = [catalogs.get(i['id'], {}) for i in instruments.values()]
        return {'job': dict(self.job) if self.job else None, 'instruments': len(instruments),
                'with_history': sum(bool(row.get('rows')) for row in rows),
                'failed': sum(bool(row.get('error')) for row in rows),
                'retrieved_at': max((row.get('retrieved_at') for row in rows if row.get('retrieved_at')), default=None)}

    def timeline(self, instrument):
        if not instrument:
            return []
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT day,close,change_pct,adjusted_change_pct FROM daily_bars WHERE instrument_id=? AND day>=? ORDER BY day', (instrument['id'], START_DATE))]

    def day(self, companies, instruments, selected_date, root, basis='close'):
        datetime.strptime(selected_date, '%Y-%m-%d')
        ids = [i['id'] for i in instruments.values()]
        catalogs = self.catalogs()
        with self.connect() as db:
            rows = {r['instrument_id']: dict(r) for r in db.execute(
                'SELECT * FROM daily_bars WHERE day=? AND instrument_id IN ('+','.join('?' for _ in ids)+')',
                [selected_date] + ids)} if ids else {}
        key = 'adjusted_change_pct' if basis == 'adjusted' else 'change_pct'
        anchor_instrument = instruments.get(root, {})
        anchor = rows.get(anchor_instrument.get('id'), {})
        anchor_return = anchor.get(key)
        results = []
        for company in companies:
            instrument = instruments.get(company['id'])
            row = rows.get(instrument['id'], {}) if instrument else {}
            catalog = catalogs.get(instrument['id'], {}) if instrument else {}
            value = row.get(key)
            aligned = bool(value is not None and anchor_return is not None
                           and row.get('previous_day') == anchor.get('previous_day'))
            relative = value - anchor_return if aligned else None
            if not instrument:
                reason = 'No own public-share instrument mapped'  # Do not silently borrow a parent price.
                availability = 'unlisted_or_unmapped'
            elif not row:
                if not catalog.get('rows'):
                    reason = 'History unavailable' if catalog.get('error') else 'History not downloaded'
                    availability = 'unavailable' if catalog.get('error') else 'not_loaded'
                elif selected_date < catalog['first_date']:
                    reason, availability = 'Before available listing history', 'before_history'
                elif selected_date > catalog['last_date']:
                    reason, availability = 'No observation for this date; cached history ends '+catalog['last_date'], 'after_history'
                else:
                    reason, availability = 'No traded observation: holiday, suspension or missing bar', 'no_session'
            elif value is None:
                reason, availability = 'No prior comparable close for this basis', 'no_previous_close'
            else:
                reason, availability = None, 'available'
            results.append({'company_id': company['id'], 'instrument_id': instrument.get('id') if instrument else None,
                            'ticker': instrument.get('ticker') if instrument else None,
                            'currency': catalog.get('currency') or (instrument.get('currency') if instrument else None),
                            'exchange': catalog.get('exchange') or (instrument.get('exchange') if instrument else None),
                            'timezone': catalog.get('timezone'), 'date': selected_date,
                            'close': row.get('close'), 'adjusted_close': row.get('adjusted_close'),
                            'previous_date': row.get('previous_day'), 'previous_close': row.get('previous_close'),
                            'previous_adjusted_close': row.get('previous_adjusted_close'),
                            'change_pct': value, 'vs_apple_pp': relative, 'aligned_with_apple': aligned,
                            'relative_note': None if aligned else 'Apple or company return unavailable, or prior-session dates differ',
                            'availability': availability, 'missing_reason': reason,
                            'retrieved_at': catalog.get('retrieved_at'), 'refresh_error': catalog.get('error'),
                            'history_last_date': catalog.get('last_date'), 'provider': 'Yahoo Finance via yfinance'})
        from .market_factors import market_adjustments
        adjustments, market_model = market_adjustments(self, instruments, selected_date, basis)
        for row in results:
            row.update(adjustments.get(row['instrument_id'], {
                'market_adjusted_pp':None,'market_expected_pct':None,'market_fit_observations':0,
                'market_fit_start':None,'market_fit_end':None,'market_reason':'No own mapped public-share instrument'}))
        return {'date': selected_date, 'root': root, 'basis': basis, 'prices': results,
                'market_model':market_model,
                'apple_change_pct': anchor_return, 'apple_previous_date': anchor.get('previous_day'),
                'counts': {'companies': len(results), 'priced': sum(r['change_pct'] is not None for r in results),
                           'up': sum(r['change_pct'] is not None and r['change_pct'] > 0 for r in results),
                           'down': sum(r['change_pct'] is not None and r['change_pct'] < 0 for r in results),
                           'flat': sum(r['change_pct'] == 0 for r in results),
                           'unavailable': sum(r['change_pct'] is None for r in results),
                           'comparable_with_apple': sum(r['aligned_with_apple'] for r in results)},
                'method': '100*(selected session close / previous available local session close - 1). No filling missing dates. Relative values subtract Apple only when both start/end calendar dates match. Cross-market closes are not simultaneous.'}
