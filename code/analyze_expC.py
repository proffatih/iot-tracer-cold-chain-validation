"""EXP-C: PCB self-heating offset of the assembled node.

Two runs were recorded on 2026-11-04, each with the node beside the reference
logger in still room air, the node switched on at the start of the run and left
under its normal duty cycle for the best part of an hour. Working with the
difference between the two instruments,

    D(t) = T_node(t) - T_reference(t),

each record has the same three parts:

  * the first sample, taken at the instant of power-on. The sensing element has
    a thermal time constant of seconds and is still at air temperature, so this
    sample gives the calibration offset between the two instruments alone. It
    is the only sample in the record with the element at air temperature.
  * a fast excursion over the following minute as the element equilibrates with
    the board, which is warm at power-on, and then a decay as the assembly
    settles. Fitting that decay returns its thermal time constant in still air.
  * a plateau, which is the operating equilibrium: calibration offset plus the
    self-heating of the board under its normal duty cycle.

The self-heating offset is the plateau minus the first sample. The calibration
offset cancels in that difference, as does any slow drift of the room, and the
estimate does not depend on why the board was warm at power-on. It requires
only that the element was at air temperature for the first sample, which is
testable: the two runs were taken two hours apart with the room at different
temperatures, so if the first sample tracks the air rather than reporting a
fixed power-on value, both runs must return the same D(0). That test is printed
below and must be read before the result is used.

Writes results/expC_selfheating.json.
"""
import csv
import datetime as dt
import json
import math
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, 'data')
OUT = os.path.join(BASE, 'results')

PLATEAU_MIN = 20.0        # window at the end of the run taken as the plateau
PEAK_SEARCH_MIN = 5.0     # the excursion peaks within this of power-on
TAU_LO, TAU_HI, TAU_STEP = 0.5, 60.0, 0.05
MAX_PAIR_GAP_S = 45
RESOLUTION_C = 0.1        # both instruments report to 0.1 degC


def read_node(path):
    rec = []
    with open(path, 'r', encoding='utf-8-sig') as fh:
        for row in csv.reader(fh):
            if len(row) < 4:
                continue
            try:
                stamp = dt.datetime.strptime(row[3], '%d/%m/%Y %H:%M')
                rec.append({'t': stamp, 'T': float(row[0]), 'RH': float(row[1]),
                            'co2': float(row[2])})
            except ValueError:
                continue
    return rec            # order as logged: the first row is the first sample


def read_reference(path):
    rec = []
    try:
        with open(path, 'r', encoding='latin-1') as fh:
            raw = fh.read()
    except OSError:
        return rec
    for line in raw.replace('\r', '\n').split('\n'):
        q = line.split('\t')
        if len(q) < 9:
            continue
        try:
            rec.append({'t': dt.datetime.strptime(q[1] + ' ' + q[2],
                                                  '%Y/%m/%d %H:%M:%S'),
                        'RH': float(q[3]), 'T': float(q[5]), 'co2': float(q[7])})
        except ValueError:
            continue
    rec.sort(key=lambda r: r['t'])
    return rec


def find_runs():
    """Every node export under data/ whose name carries 'exp c' or 'expc'."""
    out = []
    for fn in sorted(os.listdir(DATA)):
        low = fn.lower()
        if low.endswith('.csv') and ('exp c' in low or 'expc' in low):
            out.append(os.path.join(DATA, fn))
    if not out:
        raise SystemExit('no EXP-C node export found in ' + DATA)
    return out


def pick_reference(lo, hi):
    """Choose the reference log by the window it covers, not by its name.

    The instrument exports under a serial name such as CHA01001.XLS, and other
    trials have left their own logs in the same directory.
    """
    best, best_n, seen = None, 0, []
    for fn in sorted(os.listdir(DATA)):
        if not fn.lower().endswith(('.tsv', '.xls', '.txt', '.csv')):
            continue
        path = os.path.join(DATA, fn)
        rows = read_reference(path)
        if not rows:
            continue
        n = sum(1 for r in rows if lo <= r['t'] <= hi)
        seen.append((fn, n, len(rows)))
        if n > best_n:
            best, best_n = path, n
    if best is None or best_n < 20:
        lines = ['no reference log covers %s - %s (need 20+ samples).'
                 % (lo.strftime('%Y-%m-%d %H:%M'), hi.strftime('%H:%M'))]
        for fn, n, tot in seen:
            lines.append('   %-44s %4d inside / %6d rows' % (fn, n, tot))
        raise SystemExit('\n'.join(lines))
    return best


def pair(node, ref):
    out = []
    j = 0
    for n in node:
        while j + 1 < len(ref) and abs((ref[j + 1]['t'] - n['t']).total_seconds()) \
                <= abs((ref[j]['t'] - n['t']).total_seconds()):
            j += 1
        gap = abs((ref[j]['t'] - n['t']).total_seconds())
        if gap <= MAX_PAIR_GAP_S:
            out.append({'t': n['t'], 'T_node': n['T'], 'T_ref': ref[j]['T'],
                        'RH_node': n['RH'], 'RH_ref': ref[j]['RH'],
                        'D': n['T'] - ref[j]['T'],
                        'D_RH': n['RH'] - ref[j]['RH']})
    return out


def fit_decay(x, y):
    """y = y_inf + A exp(-x/tau); search tau, solve the rest by least squares."""
    n = len(x)
    best = None
    tau = TAU_LO
    while tau <= TAU_HI:
        e = [math.exp(-xi / tau) for xi in x]
        me, my = sum(e) / n, sum(y) / n
        see = sum((ei - me) ** 2 for ei in e)
        if see > 1e-12:
            sey = sum((ei - me) * (yi - my) for ei, yi in zip(e, y))
            a = sey / see
            inf = my - a * me
            sse = sum((yi - (inf + a * ei)) ** 2 for ei, yi in zip(e, y))
            if best is None or sse < best['sse']:
                syy = sum((yi - my) ** 2 for yi in y)
                best = {'tau_min': tau, 'A': a, 'y_inf': inf, 'sse': sse,
                        'rmse': math.sqrt(sse / max(n - 3, 1)),
                        'r2': 1 - sse / syy if syy > 0 else float('nan'), 'n': n}
        tau += TAU_STEP
    return best


def mean_sd(v):
    m = sum(v) / len(v)
    if len(v) < 2:
        return m, 0.0
    return m, math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def dln_esat_dT(t_c):
    """d ln(e_sat)/dT from the Magnus form, per kelvin."""
    return 17.625 * 243.04 / (243.04 + t_c) ** 2


def analyse(path):
    node = read_node(path)
    lo = node[0]['t'] - dt.timedelta(minutes=2)
    hi = node[-1]['t'] + dt.timedelta(minutes=2)
    ref = read_reference(pick_reference(lo, hi))
    rows = pair(node, ref)
    if len(rows) < 20:
        raise SystemExit('%s: only %d paired samples' % (path, len(rows)))

    t0 = rows[0]['t']
    x = [(r['t'] - t0).total_seconds() / 60.0 for r in rows]

    first = rows[0]
    plateau = [r for xi, r in zip(x, rows) if xi >= x[-1] - PLATEAU_MIN]
    d_plat, sd_plat = mean_sd([r['D'] for r in plateau])

    rest = list(zip(x, rows))[1:]          # drop the power-on sample
    head = [(xi, r) for xi, r in rest if xi <= PEAK_SEARCH_MIN]
    xpk, rpk = max(head, key=lambda q: q[1]['D'])
    ipk = next(i for i, (xi, r) in enumerate(rest) if r is rpk)
    tail = [(xi - xpk, r['D']) for xi, r in rest[ipk:]]
    f = fit_decay([q[0] for q in tail], [q[1] for q in tail])

    delta = d_plat - first['D']
    t_air = sum(r['T_ref'] for r in rows) / len(rows)
    rh_air = sum(r['RH_ref'] for r in rows) / len(rows)

    rh_node_plat, _ = mean_sd([r['RH_node'] for r in plateau])
    rh_ref_plat, _ = mean_sd([r['RH_ref'] for r in plateau])
    rh_ratio = rh_ref_plat / first['RH_ref'] if first['RH_ref'] else float('nan')
    rh_pred_plat = (first['RH_node'] * rh_ratio
                    * math.exp(-delta * dln_esat_dT(t_air)))
    rh_delta = rh_node_plat - first['RH_node']
    rh_pred = rh_pred_plat - first['RH_node']

    return {
        'file': os.path.basename(path),
        'reference': os.path.basename(pick_reference(lo, hi)),
        'start': t0.strftime('%Y-%m-%d %H:%M'),
        'stop': rows[-1]['t'].strftime('%H:%M'),
        'duration_min': x[-1], 'n_paired': len(rows),
        'D_at_power_on_C': first['D'],
        'T_node_first_C': first['T_node'], 'T_ref_first_C': first['T_ref'],
        'D_peak_C': rpk['D'], 'peak_at_min': xpk,
        'D_plateau_C': d_plat, 'D_plateau_sd_C': sd_plat,
        'n_plateau': len(plateau),
        'self_heating_C': delta,
        'tau_still_air_min': f['tau_min'], 'decay_fit_r2': f['r2'],
        'decay_fit_rmse_C': f['rmse'],
        'RH_node_at_power_on_pct': first['RH_node'],
        'RH_node_plateau_pct': rh_node_plat,
        'RH_ref_at_power_on_pct': first['RH_ref'],
        'RH_ref_plateau_pct': rh_ref_plat,
        'RH_shift_observed_pct': rh_delta, 'RH_shift_predicted_pct': rh_pred,
        'room_T_mean_C': t_air, 'room_RH_mean_pct': rh_air,
        'room_T_drift_C': rows[-1]['T_ref'] - rows[0]['T_ref'],
        'room_RH_drift_pct': rows[-1]['RH_ref'] - rows[0]['RH_ref'],
    }


def main():
    runs = [analyse(p) for p in find_runs()]

    for r in runs:
        print('=' * 70)
        print('%s   %s to %s   %.0f min, %d paired'
              % (r['file'], r['start'], r['stop'], r['duration_min'],
                 r['n_paired']))
        print('   reference        ' + r['reference'])
        print('   power-on sample  node %.2f  ref %.2f  ->  D(0) = %+.2f C'
              % (r['T_node_first_C'], r['T_ref_first_C'], r['D_at_power_on_C']))
        print('   excursion peak   %+.2f C at %.0f min'
              % (r['D_peak_C'], r['peak_at_min']))
        print('   plateau          %+.3f +/- %.3f C  (last %.0f min, n = %d)'
              % (r['D_plateau_C'], r['D_plateau_sd_C'], PLATEAU_MIN,
                 r['n_plateau']))
        print('   self-heating     %+.3f C' % r['self_heating_C'])
        print('   decay            tau %.1f min, R2 %.3f, residual sd %.3f C'
              % (r['tau_still_air_min'], r['decay_fit_r2'],
                 r['decay_fit_rmse_C']))
        print('   humidity         node %.1f -> %.1f %%RH  (observed %+.2f),'
              % (r['RH_node_at_power_on_pct'], r['RH_node_plateau_pct'],
                 r['RH_shift_observed_pct']))
        print('                    predicted %+.2f %%RH from the offset and the'
              % r['RH_shift_predicted_pct'])
        print('                    air going %.1f -> %.1f %%RH'
              % (r['RH_ref_at_power_on_pct'], r['RH_ref_plateau_pct']))
        print('   room             %.2f C mean, drift %+.2f C; RH drift %+.1f %%'
              % (r['room_T_mean_C'], r['room_T_drift_C'],
                 r['room_RH_drift_pct']))

    print('=' * 70)
    d0 = [r['D_at_power_on_C'] for r in runs]
    sh = [r['self_heating_C'] for r in runs]
    m_d0, sd_d0 = mean_sd(d0)
    m_sh, sd_sh = mean_sd(sh)

    print('CONSISTENCY TEST on the power-on sample')
    print('   room air at power-on was %s C'
          % ', '.join('%.2f' % r['T_ref_first_C'] for r in runs))
    print('   and D(0) came out        %s C'
          % ', '.join('%+.2f' % v for v in d0))
    spread = max(d0) - min(d0)
    if spread <= 2 * RESOLUTION_C:
        print('   they agree within %.2f C, one display step, although the air'
              % spread)
        print('   differed. The first sample is tracking the air rather than')
        print('   reporting a fixed power-on value, so it can be read as the')
        print('   calibration offset.')
    else:
        print('   they differ by %.2f C, more than the display resolution allows'
              % spread)
        print('   for one offset. Do NOT use this as a calibration offset until')
        print('   the discrepancy is understood.')

    u_quant = RESOLUTION_C / math.sqrt(12.0) * math.sqrt(2.0)
    u_between = sd_sh / math.sqrt(len(sh)) if len(sh) > 1 else 0.0
    u_plateau = math.sqrt(sum(r['D_plateau_sd_C'] ** 2 / r['n_plateau']
                              for r in runs)) / len(runs)
    u_comb = math.sqrt(u_quant ** 2 + u_between ** 2 + u_plateau ** 2)

    print('')
    print('COMBINED')
    print('   calibration offset D(0)   %+.3f C  (sd %.3f over %d runs)'
          % (m_d0, sd_d0, len(d0)))
    print('   self-heating              %+.3f C  (runs: %s)'
          % (m_sh, ', '.join('%+.3f' % v for v in sh)))
    print('   standard uncertainty      %.3f C'
          ' = quantisation %.3f, between-run %.3f, plateau %.3f'
          % (u_comb, u_quant, u_between, u_plateau))
    u_b3 = abs(m_sh) / math.sqrt(3.0)
    print('   u_B3 = |%.3f| / sqrt(3)   %.3f C' % (m_sh, u_b3))

    tau = [r['tau_still_air_min'] for r in runs]
    m_tau, sd_tau = mean_sd(tau)
    print('   still-air time constant   %.1f min (runs: %s)'
          % (m_tau, ', '.join('%.1f' % v for v in tau)))

    res = {'runs': runs,
           'calibration_offset_C': m_d0, 'calibration_offset_sd_C': sd_d0,
           'self_heating_C': m_sh, 'self_heating_sd_C': sd_sh,
           'self_heating_u_C': u_comb,
           'u_quantisation_C': u_quant, 'u_between_run_C': u_between,
           'u_plateau_C': u_plateau, 'u_B3_C': u_b3,
           'tau_still_air_min': m_tau, 'tau_sd_min': sd_tau,
           'RH_shift_observed_pct': sum(r['RH_shift_observed_pct']
                                        for r in runs) / len(runs),
           'RH_shift_predicted_pct': sum(r['RH_shift_predicted_pct']
                                         for r in runs) / len(runs)}

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'expC_selfheating.json'), 'w') as fh:
        json.dump(res, fh, indent=2)
    print('')
    print('written: ' + os.path.join(OUT, 'expC_selfheating.json'))


if __name__ == '__main__':
    sys.exit(main())
