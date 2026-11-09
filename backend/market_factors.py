"""A descriptive rolling two-factor adjustment, fitted on strictly older daily returns."""
from __future__ import annotations

from pathlib import Path
import json
import numpy as np

WINDOW = 252
MIN_OBSERVATIONS = 120
BENCHMARKS = {ticker: {'id': 'market-benchmark:'+ticker, 'company_id': 'benchmark:'+ticker,
                      'ticker': ticker, 'currency': 'USD', 'exchange': 'NYSE Arca', 'is_primary': True}
              for ticker in ['SPY', 'XLK']}


def control_universe():
    roster = json.loads(Path(__file__).with_name('control_companies.json').read_text(encoding='utf-8'))
    companies, instruments = [], {}
    for item in roster['companies']:
        identifier = 'CTRL_'+item['ticker']
        companies.append({'id': identifier, 'name': item['name'], 'primary_ticker': item['ticker'],
                          'country': item.get('country','United States'), 'status': 'public',
                          'industry': item['industry'], 'official_url': item['official_url'],
                          'visual_control': True, 'relationship_count': 0})
        instruments[identifier] = {'id': 'visual-control:'+item['ticker'], 'company_id': identifier,
                                    'ticker': item['ticker'], 'currency': 'USD',
                                    'exchange': 'US-listed', 'is_primary': True}
    return companies, instruments, roster


def fit_two_factor(y, spy, xlk, current_spy, current_xlk):
    """Orthogonalized OLS is algebraically a joint SPY+XLK regression with intercept."""
    y, spy, xlk = [np.asarray(v,dtype=float) for v in [y,spy,xlk]]
    if len(y) < MIN_OBSERVATIONS:
        return None
    mean_spy, mean_xlk = spy.mean(), xlk.mean()
    market_sd = spy.std()
    if market_sd < 1e-8:
        return None
    gamma = np.mean((spy-mean_spy)*(xlk-mean_xlk)) / market_sd**2
    tech_alpha = mean_xlk-gamma*mean_spy
    tech = xlk-(tech_alpha+gamma*spy)
    tech_sd = tech.std()
    if tech_sd < max(1e-8,xlk.std()*1e-4):
        return None
    design = np.column_stack([np.ones(len(y)),(spy-mean_spy)/market_sd,tech/tech_sd])
    coefficients,_,rank,_ = np.linalg.lstsq(design,y,rcond=None)
    if rank != 3:
        return None
    beta_xlk = coefficients[2]/tech_sd
    beta_spy = coefficients[1]/market_sd-beta_xlk*gamma
    alpha = coefficients[0]-coefficients[1]*mean_spy/market_sd-beta_xlk*tech_alpha
    expected = alpha+beta_spy*current_spy+beta_xlk*current_xlk
    return {'expected_pct':float(expected),'alpha_pct':float(alpha),
            'beta_spy':float(beta_spy),'beta_xlk':float(beta_xlk),
            'orthogonalization_gamma':float(gamma),'observations':len(y)}


def market_adjustments(service, instruments, selected_date, basis):
    key = 'adjusted_change_pct' if basis=='adjusted' else 'change_pct'
    with service.connect() as db:
        current = {}
        for ticker,instrument in BENCHMARKS.items():
            row = db.execute('SELECT * FROM daily_bars WHERE instrument_id=? AND day=?',
                             (instrument['id'],selected_date)).fetchone()
            current[ticker] = dict(row) if row else {}
        past = [dict(r) for r in db.execute(
            f'SELECT day,previous_day,{key} AS value FROM daily_bars WHERE instrument_id=? AND day<? ORDER BY day DESC LIMIT ?',
            (BENCHMARKS['SPY']['id'],selected_date,WINDOW))]
        cutoff = past[-1]['day'] if past else selected_date
        ids = list({i['id'] for i in instruments.values()} | {i['id'] for i in BENCHMARKS.values()})
        records = list(db.execute(f'SELECT instrument_id,day,previous_day,{key} AS value FROM daily_bars WHERE instrument_id IN ('+
                                  ','.join('?' for _ in ids)+') AND day>=? AND day<=?',ids+[cutoff,selected_date]))
    histories = {}
    for row in records:
        histories.setdefault(row['instrument_id'],{})[row['day']] = (row['previous_day'],row['value'])
    spy_history, xlk_history = [histories.get(BENCHMARKS[t]['id'],{}) for t in ['SPY','XLK']]
    benchmark_days = []
    for row in reversed(past):
        other = xlk_history.get(row['day'])
        if other and row['value'] is not None and other[1] is not None and row['previous_day']==other[0]:
            benchmark_days.append((row['day'],row['previous_day'],row['value'],other[1]))
    benchmark_ok = all(current[t].get(key) is not None for t in ['SPY','XLK']) and current['SPY'].get('previous_day')==current['XLK'].get('previous_day')
    results = {}
    for instrument in instruments.values():
        history = histories.get(instrument['id'],{})
        observation = history.get(selected_date)
        result = {'market_adjusted_pp':None,'market_expected_pct':None,'market_fit_observations':0,
                  'market_fit_start':None,'market_fit_end':None,'market_beta_spy':None,'market_beta_xlk':None,
                  'market_alpha_pct':None,'market_reason':None}
        if not benchmark_ok:
            result['market_reason']='SPY or XLK has no comparable return on this date'
        elif not observation or observation[1] is None:
            result['market_reason']='No company return for the selected date and price measure'
        elif observation[0] != current['SPY']['previous_day']:
            result['market_reason']='Company and ETF prior-session dates differ'
        else:
            training = [row for row in benchmark_days if row[0] in history and history[row[0]][1] is not None and history[row[0]][0]==row[1]]
            result['market_fit_observations']=len(training)
            if training:
                result['market_fit_start'],result['market_fit_end']=training[0][0],training[-1][0]
            if len(training)<MIN_OBSERVATIONS:
                result['market_reason']=f'Insufficient prior aligned history: {len(training)}/{MIN_OBSERVATIONS} required'
            else:
                fitted = fit_two_factor([history[r[0]][1] for r in training],[r[2] for r in training],
                                        [r[3] for r in training],current['SPY'][key],current['XLK'][key])
                if fitted is None:
                    result['market_reason']='Prior benchmark factors have insufficient independent variation'
                else:
                    residual=float(observation[1]-fitted['expected_pct'])
                    result.update(market_adjusted_pp=0.0 if abs(residual)<1e-10 else residual,
                                  market_expected_pct=fitted['expected_pct'],market_beta_spy=fitted['beta_spy'],
                                  market_beta_xlk=fitted['beta_xlk'],market_alpha_pct=fitted['alpha_pct'])
        results[instrument['id']]=result
    metadata = {'window_sessions':WINDOW,'minimum_aligned_observations':MIN_OBSERVATIONS,
                'method':'Joint OLS with intercept; XLK orthogonalized to SPY on the same strictly prior training rows. Residual = observed return minus fitted SPY+XLK return.',
                'benchmarks':{t:{'ticker':t,'date':selected_date,'change_pct':current[t].get(key),
                                  'previous_date':current[t].get('previous_day')} for t in BENCHMARKS},
                'fitting_uses_selected_or_future_return':False}
    return results,metadata
