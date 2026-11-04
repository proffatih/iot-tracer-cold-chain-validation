"""EXP-A detection and persistence.

Two questions a cold-chain operator actually asks:

  1. How long after the breach does an on-node rule flag it, using temperature
     alone and using the CO2 accumulation slope alone?
  2. Once the temperature has recovered, is there anything left in the record
     that says the excursion happened?

The second question is where a CO2 channel earns its place: headspace CO2 does
not relax when the product is re-cooled, so it integrates the excursion, while
temperature returns to baseline and erases the evidence unless the whole trace
was logged.

Writes results/expA_detection.json.
"""
import datetime as dt
import json
import math
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_expA import read_node, ols, NODE, MARKS, OUT, DAY

WIN_MIN = 15          # rolling window for the slope detector
BASE_MIN = 20         # baseline taken from the last BASE_MIN of phase A
K_SIGMA = 3.0         # alarm threshold in baseline standard deviations
CONSEC = 2            # consecutive exceedances required


def rolling_slopes(rec, win_min):
    out = []
    for i, r in enumerate(rec):
        lo = r['t'] - dt.timedelta(minutes=win_min)
        seg = [q for q in rec[:i + 1] if q['t'] >= lo]
        if len(seg) < 8:
            continue
        anchor = seg[0]['t']
        x = [(q['t'] - anchor).total_seconds() / 3600.0 for q in seg]
        fit = ols(x, [q['co2'] for q in seg])
        out.append({'t': r['t'], 'slope': fit['slope'], 'se': fit['se'],
                    'T': r['T'], 'co2': r['co2'], 'n': fit['n']})
    return out


def first_alarm(series, key, thresh, after, consec):
    run = 0
    for s in series:
        if s['t'] < after:
            continue
        if s[key] > thresh:
            run += 1
            if run >= consec:
                return s['t']
        else:
            run = 0
    return None


def main():
    rec = read_node(NODE)
    rec = [r for r in rec if MARKS['t0'] <= r['t'] <= MARKS['tend']]
    t1, t2, tend = MARKS['t1'], MARKS['t2'], MARKS['tend']

    # ---- baseline from the settled tail of phase A -------------------------
    base_from = t1 - dt.timedelta(minutes=BASE_MIN)
    base_rec = [r for r in rec if base_from <= r['t'] <= t1]

    temps = [r['T'] for r in base_rec]
    t_mu, t_sd = st.mean(temps), st.pstdev(temps)
    t_thresh = t_mu + K_SIGMA * t_sd

    roll = rolling_slopes(rec, WIN_MIN)
    base_roll = [s for s in roll if base_from <= s['t'] <= t1]
    s_mu = st.mean([s['slope'] for s in base_roll])
    s_sd = st.pstdev([s['slope'] for s in base_roll])
    s_thresh = s_mu + K_SIGMA * s_sd

    a_temp = first_alarm([{'t': r['t'], 'T': r['T']} for r in rec],
                         'T', t_thresh, t1, CONSEC)
    a_co2 = first_alarm(roll, 'slope', s_thresh, t1, CONSEC)

    lat_t = (a_temp - t1).total_seconds() / 60.0 if a_temp else None
    lat_c = (a_co2 - t1).total_seconds() / 60.0 if a_co2 else None

    # ---- persistence: what the record still shows once T has recovered -----
    tail = [r for r in rec if r['t'] >= tend - dt.timedelta(minutes=10)]
    base_tail = [r for r in rec if base_from <= r['t'] <= t1]
    t_end_mean = st.mean([r['T'] for r in tail])
    t_base_mean = st.mean([r['T'] for r in base_tail])
    co2_end = st.mean([r['co2'] for r in tail])

    co2_at_t1 = [r['co2'] for r in rec if r['t'] <= t1][-1]
    observed_rise = co2_end - co2_at_t1

    # counterfactual: phase A had settled to this rate and the jar would have
    # stayed at that temperature had it never been removed
    cf_rate = s_mu
    hours = (tend - t1).total_seconds() / 3600.0
    cf_rise = cf_rate * hours
    excess = observed_rise - cf_rise

    # noise floor on the excess: baseline slope scatter propagated over t1..tend
    cf_sd = s_sd * hours

    res = {
        'date': DAY.isoformat(), 'window_min': WIN_MIN,
        'baseline_window': [base_from.strftime('%H:%M'), t1.strftime('%H:%M')],
        'baseline': {
            'T_mean': t_mu, 'T_sd': t_sd, 'T_threshold': t_thresh,
            'slope_mean': s_mu, 'slope_sd': s_sd, 'slope_threshold': s_thresh,
            'k_sigma': K_SIGMA, 'consecutive': CONSEC},
        'detection': {
            'breach_at': t1.strftime('%H:%M'),
            'temperature_alarm': a_temp.strftime('%H:%M') if a_temp else None,
            'temperature_latency_min': lat_t,
            'co2_slope_alarm': a_co2.strftime('%H:%M') if a_co2 else None,
            'co2_slope_latency_min': lat_c},
        'persistence': {
            'T_baseline_mean': t_base_mean,
            'T_final_mean': t_end_mean,
            'T_recovered_within_C': abs(t_end_mean - t_base_mean),
            'co2_at_breach': co2_at_t1,
            'co2_final': co2_end,
            'observed_rise_ppm': observed_rise,
            'counterfactual_rise_ppm': cf_rise,
            'excess_ppm': excess,
            'excess_noise_sd_ppm': cf_sd,
            'excess_sigma': excess / cf_sd if cf_sd else None},
    }

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'expA_detection.json'), 'w') as fh:
        json.dump(res, fh, indent=2)

    print('EXP-A detection, %d min rolling window, %.0f sigma, %d consecutive'
          % (WIN_MIN, K_SIGMA, CONSEC))
    print('baseline %s-%s' % (base_from.strftime('%H:%M'), t1.strftime('%H:%M')))
    print('   temperature  %.2f +/- %.2f C   -> threshold %.2f C'
          % (t_mu, t_sd, t_thresh))
    print('   CO2 slope    %.0f +/- %.0f ppm/h -> threshold %.0f ppm/h'
          % (s_mu, s_sd, s_thresh))
    print('')
    print('breach at %s' % t1.strftime('%H:%M'))
    print('   temperature alarm  %s   latency %s'
          % (a_temp.strftime('%H:%M') if a_temp else 'none',
             ('%.0f min' % lat_t) if lat_t is not None else '-'))
    print('   CO2 slope alarm    %s   latency %s'
          % (a_co2.strftime('%H:%M') if a_co2 else 'none',
             ('%.0f min' % lat_c) if lat_c is not None else '-'))
    print('')
    print('persistence after re-cooling')
    print('   temperature  baseline %.1f C, final %.1f C  (recovered to %.1f C)'
          % (t_base_mean, t_end_mean, abs(t_end_mean - t_base_mean)))
    print('   CO2          %.0f ppm at breach -> %.0f ppm at end'
          % (co2_at_t1, co2_end))
    print('   observed rise        %.0f ppm' % observed_rise)
    print('   no-breach expectation %.0f ppm (%.0f ppm/h for %.2f h)'
          % (cf_rise, cf_rate, hours))
    print('   excess attributable to the breach  %.0f ppm  (%.1f sigma)'
          % (excess, res['persistence']['excess_sigma']))


if __name__ == '__main__':
    main()
