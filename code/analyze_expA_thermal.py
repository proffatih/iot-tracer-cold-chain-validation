"""EXP-A thermal lag of the sealed package.

Section 4.8 reports tau = 7.6 min for the bare node in moving air. Inside a
sealed 1.7 L glass jar the node no longer sees the store air directly, so the
relevant time constant is that of the package. Both cooling phases (A and C)
are fitted to a first-order relaxation,

    T(t) = T_inf + (T_0 - T_inf) exp(-t / tau),

by a grid search over the asymptote with a log-linear fit at each candidate.

Writes results/expA_thermal.json.
"""
import datetime as dt
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_expA import read_node, read_extech, ols, NODE, EXTECH, MARKS, OUT, DAY


def fit_first_order(seg, t_inf_lo, t_inf_hi, step=0.05):
    """Grid search the asymptote; return the best first-order fit."""
    anchor = seg[0]['t']
    x = [(r['t'] - anchor).total_seconds() / 60.0 for r in seg]
    best = None
    t_inf = t_inf_lo
    while t_inf <= t_inf_hi:
        y = []
        ok = True
        for r in seg:
            d = r['T'] - t_inf
            if d <= 0.05:
                ok = False
                break
            y.append(math.log(d))
        if ok:
            f = ols(x, y)
            if f['slope'] < 0 and (best is None or f['r2'] > best['r2']):
                best = {'T_inf': t_inf, 'tau': -1.0 / f['slope'],
                        'T0': t_inf + math.exp(f['intercept']),
                        'r2': f['r2'], 'n': f['n']}
        t_inf += step
    return best


def main():
    node = read_node(NODE)
    ref = read_extech(EXTECH, DAY)
    out = {'date': DAY.isoformat()}

    phases = [('A', MARKS['t0'], MARKS['t1']),
              ('C', MARKS['t2'], MARKS['tend'])]
    for name, lo, hi in phases:
        seg = [r for r in node if lo <= r['t'] <= hi]
        fit = fit_first_order(seg, 2.0, min(r['T'] for r in seg) - 0.1)
        if fit:
            fit['t90_min'] = 2.303 * fit['tau']
            fit['window'] = [lo.strftime('%H:%M'), hi.strftime('%H:%M')]
            fit['T_observed_end'] = seg[-1]['T']
            fit['approach_pct'] = 100.0 * (seg[0]['T'] - seg[-1]['T']) / \
                                  (seg[0]['T'] - fit['T_inf'])
        out['node_phase_' + name] = fit

        # The reference instrument sits in store air, which is compressor-cycled
        # rather than relaxing towards a single asymptote. These fits are kept
        # only to show that a first-order model does not describe that trace;
        # they are not reported as time constants.
        rseg = [r for r in ref if lo <= r['t'] <= hi]
        if rseg:
            rfit = fit_first_order(rseg, 0.0, min(r['T'] for r in rseg) - 0.1)
            if rfit:
                rfit['t90_min'] = 2.303 * rfit['tau']
                rfit['window'] = [lo.strftime('%H:%M'), hi.strftime('%H:%M')]
                rfit['note'] = ('not a time constant: store air is compressor-'
                                'cycled, first-order model does not apply')
            out['reference_phase_' + name] = rfit

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'expA_thermal.json'), 'w') as fh:
        json.dump(out, fh, indent=2)

    for k in sorted(out):
        if k == 'date' or not out[k]:
            continue
        f = out[k]
        print('%-20s tau = %5.1f min   t90 = %5.1f min   T_inf = %5.1f C   R2 = %.3f'
              % (k, f['tau'], f['t90_min'], f['T_inf'], f['r2']))
        if 'approach_pct' in f:
            print('%-20s reached %.1f C by end of window, %.0f%% of the way to T_inf'
                  % ('', f['T_observed_end'], f['approach_pct']))


if __name__ == '__main__':
    main()
