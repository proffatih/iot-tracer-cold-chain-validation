"""Mean current and endurance, from a logged ammeter trace at the cell.

Inputs come from results/current_log.json, which analyze_current_log.py
produces from the logging multimeter placed in series with the battery. Two
quantities are taken from it and nothing is assumed:

    i_idle      current between acquisitions
    q_active    charge drawn per acquisition, integrated over the window,
                together with the window's duration

so that for a sampling interval I,

    I_mean = (q_active + i_idle * (I - t_active)) / I + i_leak

with i_leak the cell self-discharge, taken as 2.5 % per month.

This supersedes two earlier accounts. The initial submission measured per-mode
currents with a USB meter in the charging lead and tabulated them as cell
currents, which they are not. The first correction measured the levels at the
cell but timed the windows by eye, and the eye was wrong by an order of
magnitude: the acquisition window is not one or two seconds but about
eighteen. Only the logged trace settles it, and the conclusion it supports is
the opposite of the one the eye suggested.

Writes results/energy_model.json.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'results')
LOG = os.path.join(OUT, 'current_log.json')

CELL_MAH = 2600.0
CELL_V = 3.7
I_LEAK_MA = 0.025 * CELL_MAH / (30.0 * 24.0)
I_DEEP_SLEEP_MA = 0.007          # datasheet figure for the part

INTERVALS_MIN = [1, 5, 10, 15, 30, 60]
SHORT_WINDOW_S = 3.0             # what a partial-refresh acquisition might cost


def mean_current(interval_s, q_active_mAs, t_active_s, i_idle_mA):
    if interval_s <= t_active_s:
        return float('nan')
    return ((q_active_mAs + i_idle_mA * (interval_s - t_active_s)) / interval_s
            + I_LEAK_MA)


def days(ma):
    return CELL_MAH / ma / 24.0


def main():
    if not os.path.exists(LOG):
        raise SystemExit('run code/analyze_current_log.py first')
    with open(LOG) as fh:
        logs = json.load(fh)
    c = next((l['cycles'] for l in logs if l.get('cycles')), None)
    if c is None:
        raise SystemExit('no clean cycles found in the ammeter log')

    i_idle = c['idle_mA']
    q_act = c['q_active_mAs']
    t_act = c['active_s']

    print('from the logged trace, %d clean cycles of %.0f s:'
          % (c['n'], c['period_s']))
    print('   idle            %.3f mA' % i_idle)
    print('   acquisition     %.1f +/- %.1f s, %.0f +/- %.0f mA*s per cycle'
          % (t_act, c['active_s_sd'], q_act, c['q_active_sd']))
    print('   as logged       %.2f mA, %.1f days'
          % (c['measured_mean_mA'], c['measured_days']))
    print('   self-discharge carried as %.3f mA' % I_LEAK_MA)
    print('')

    scenarios = [
        ('as built', q_act, t_act, i_idle),
        ('shorter acquisition', q_act * SHORT_WINDOW_S / t_act,
         SHORT_WINDOW_S, i_idle),
        ('shorter + deep sleep', q_act * SHORT_WINDOW_S / t_act,
         SHORT_WINDOW_S, I_DEEP_SLEEP_MA),
    ]

    print('%-8s' % 'interval', end='')
    for name, _, _, _ in scenarios:
        print('%24s' % name, end='')
    print('')
    rows = []
    for m in INTERVALS_MIN:
        s = m * 60.0
        row = {'interval_min': m}
        print('%-8s' % ('%d min' % m), end='')
        for name, q, t, i in scenarios:
            v = mean_current(s, q, t, i)
            row[name] = {'mean_mA': v, 'days': days(v)}
            print('%14s %9s' % ('%.2f mA' % v, '%.1f d' % days(v)), end='')
        print('')
        rows.append(row)

    base10 = next(r for r in rows if r['interval_min'] == 10)
    share_act = q_act / 600.0 / base10['as built']['mean_mA']
    print('')
    print('At ten-minute sampling the acquisition window accounts for %.0f %% of'
          % (100 * share_act))
    print('the mean current and the idle state for %.0f %%. The lever is the'
          % (100 * i_idle * (600 - t_act) / 600.0
             / base10['as built']['mean_mA']))
    print('window, not the idle current: shortening it to %.0f s would take'
          % SHORT_WINDOW_S)
    print('endurance from %.0f to %.0f days, and only then is deep sleep worth'
          % (base10['as built']['days'], base10['shorter acquisition']['days']))
    print('the effort, taking it to %.0f days.'
          % base10['shorter + deep sleep']['days'])

    res = {'source': 'results/current_log.json',
           'i_idle_mA': i_idle, 'q_active_mAs': q_act, 't_active_s': t_act,
           'q_active_sd': c['q_active_sd'], 't_active_sd': c['active_s_sd'],
           'n_cycles': c['n'], 'logged_period_s': c['period_s'],
           'logged_mean_mA': c['measured_mean_mA'],
           'logged_days': c['measured_days'],
           'i_leak_mA': I_LEAK_MA, 'i_deep_sleep_mA': I_DEEP_SLEEP_MA,
           'short_window_s': SHORT_WINDOW_S,
           'cell_mAh': CELL_MAH, 'cell_Wh': CELL_MAH * CELL_V / 1000.0,
           'acquisition_share_at_10min': share_act,
           'rows': rows}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'energy_model.json'), 'w') as fh:
        json.dump(res, fh, indent=2)
    print('')
    print('written: ' + os.path.join(OUT, 'energy_model.json'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
