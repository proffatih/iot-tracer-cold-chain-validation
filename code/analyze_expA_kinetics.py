"""EXP-A kinetics: recover the temperature dependence of CO2 accumulation
from the node's synchronous temperature and CO2 record.

The run sweeps the headspace from about 11 to 23 C twice (once while cooling in
phase A, once while cooling in phase C) and once while warming in phase B. Each
non-overlapping 15 min block gives one local accumulation slope and one mean
temperature; a log-linear fit of slope against temperature yields Q10.

Blocks that straddle a phase boundary are dropped. Because the three phases
sample overlapping temperatures at different times, agreement between phases is
itself a consistency check on the synchronous record.

Writes results/expA_kinetics.json.
"""
import datetime as dt
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_expA import read_node, ols, NODE, MARKS, OUT, DAY, HEADSPACE_L

BLOCK_MIN = 15
MIN_PTS = 10
T_REF = 15.0


def blocks(rec, marks):
    """Non-overlapping BLOCK_MIN windows that lie inside a single phase."""
    bounds = [(marks['t0'], marks['t1'], 'A'),
              (marks['t1'], marks['t2'], 'B'),
              (marks['t2'], marks['tend'], 'C')]
    out = []
    for lo, hi, name in bounds:
        edge = lo
        while edge + dt.timedelta(minutes=BLOCK_MIN) <= hi:
            stop = edge + dt.timedelta(minutes=BLOCK_MIN)
            seg = [r for r in rec if edge <= r['t'] < stop]
            if len(seg) >= MIN_PTS:
                anchor = seg[0]['t']
                x = [(r['t'] - anchor).total_seconds() / 3600.0 for r in seg]
                fit = ols(x, [r['co2'] for r in seg])
                out.append({
                    'phase': name,
                    'start': edge.strftime('%H:%M'),
                    'stop': stop.strftime('%H:%M'),
                    'T_mean': sum(r['T'] for r in seg) / len(seg),
                    'T_span': max(r['T'] for r in seg) - min(r['T'] for r in seg),
                    'RH_mean': sum(r['RH'] for r in seg) / len(seg),
                    'co2_mean': sum(r['co2'] for r in seg) / len(seg),
                    'slope': fit['slope'], 'se': fit['se'], 'n': fit['n'],
                    'r2': fit['r2']})
            edge = stop
    return out


def main():
    rec = read_node(NODE)
    rec = [r for r in rec if MARKS['t0'] <= r['t'] <= MARKS['tend']]
    bl = blocks(rec, MARKS)

    usable = [b for b in bl if b['slope'] > 0]
    xs = [b['T_mean'] - T_REF for b in usable]
    ys = [math.log(b['slope']) for b in usable]
    fit = ols(xs, ys)

    q10 = math.exp(10.0 * fit['slope'])
    q10_lo = math.exp(10.0 * (fit['slope'] - 1.96 * fit['se']))
    q10_hi = math.exp(10.0 * (fit['slope'] + 1.96 * fit['se']))
    rate_ref = math.exp(fit['intercept'])

    # Per-phase residuals: does a block from phase C sit on the same curve as a
    # block from phase A at the same temperature?
    by_phase = {}
    for b, lx, ly in zip(usable, xs, ys):
        pred = fit['intercept'] + fit['slope'] * lx
        b['pred_ppm_h'] = math.exp(pred)
        b['resid_pct'] = 100.0 * (b['slope'] - b['pred_ppm_h']) / b['pred_ppm_h']
        by_phase.setdefault(b['phase'], []).append(b['resid_pct'])

    res = {'date': DAY.isoformat(), 'block_min': BLOCK_MIN, 'T_ref_C': T_REF,
           'headspace_l': HEADSPACE_L, 'n_blocks': len(usable),
           'Q10': q10, 'Q10_ci95': [q10_lo, q10_hi],
           'rate_at_Tref_ppm_h': rate_ref,
           'log_fit_r2': fit['r2'], 'log_fit_rmse': fit['rmse'],
           'phase_mean_resid_pct': {k: sum(v) / len(v)
                                    for k, v in by_phase.items()},
           'blocks': usable}

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'expA_kinetics.json'), 'w') as fh:
        json.dump(res, fh, indent=2)

    print('EXP-A kinetics: %d non-overlapping %d min blocks'
          % (len(usable), BLOCK_MIN))
    print('')
    print('%-6s %-13s %7s %7s %10s %10s %8s'
          % ('phase', 'window', 'T mean', 'T span', 'slope', 'predicted', 'resid'))
    for b in usable:
        print('%-6s %s-%s %6.1fC %6.1fC %7.0f+/-%-3.0f %9.0f %7.1f%%'
              % (b['phase'], b['start'], b['stop'], b['T_mean'], b['T_span'],
                 b['slope'], b['se'], b['pred_ppm_h'], b['resid_pct']))
    print('')
    print('Q10 = %.2f  (95%% CI %.2f to %.2f)' % (q10, q10_lo, q10_hi))
    print('accumulation at %.0f C = %.0f ppm/h' % (T_REF, rate_ref))
    print('log-linear fit R2 = %.3f, residual sd = %.1f%%'
          % (fit['r2'], 100.0 * fit['rmse']))
    print('')
    print('mean residual by phase (agreement between separate temperature sweeps):')
    for k in sorted(res['phase_mean_resid_pct']):
        print('   phase %s  %+.1f%%' % (k, res['phase_mean_resid_pct'][k]))


if __name__ == '__main__':
    main()
