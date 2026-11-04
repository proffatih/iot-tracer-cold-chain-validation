"""EXP-A: cold-chain interruption trial on whole mushrooms (2026-11-03).

Reads the node record (sealed 1.7 L jar) and the Extech SD800 reference record
(air beside the jar, carried with it through all three phases), segments the run
into the three phases, and fits CO2 accumulation slopes with uncertainties.

Writes results/expA_summary.json and prints a report.
"""
import csv
import json
import datetime as dt
import math
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = os.path.join(BASE, 'data', 'node_7CDFA1FE05B5_breach_2026-11-03.csv')
EXTECH = os.path.join(BASE, 'data', 'reference_extech_sd800_2026-11-03.tsv')
OUT = os.path.join(BASE, 'results')

DAY = dt.date(2026, 11, 3)
MARKS = {
    't0': dt.datetime.combine(DAY, dt.time(14, 10)),
    't1': dt.datetime.combine(DAY, dt.time(15, 15)),
    't2': dt.datetime.combine(DAY, dt.time(16, 0)),
    'tend': dt.datetime.combine(DAY, dt.time(16, 45)),
}

MASS_G = 13.49       # mushroom mass in grams, weighed on the bench label
HEADSPACE_L = 1.65     # jar nominal 1.7 L less displaced volume:
                       #   produce 13.49 g ~ 13 mL, node assembly ~ 40 mL.
                       # Not verified by filling; carry ~10 % on absolute rates.
SETTLE_MIN = 10        # discarded after each thermal transition
STEADY_DTDT = 0.05     # |dT/dt| threshold in C/min for the quasi-steady window
MIN_STEADY = 12        # minimum points in a quasi-steady window


def read_node(path):
    rec = []
    with open(path, 'r', encoding='utf-8-sig') as fh:
        for row in csv.reader(fh):
            if len(row) < 4:
                continue
            stamp = dt.datetime.strptime(row[3], '%d/%m/%Y %H:%M')
            rec.append({'t': stamp, 'T': float(row[0]), 'RH': float(row[1]),
                        'co2': float(row[2])})
    rec.sort(key=lambda r: r['t'])
    return rec


def read_extech(path, day):
    rec = []
    with open(path, 'r', encoding='latin-1') as fh:
        raw = fh.read()
    for line in raw.replace('\r', '\n').split('\n'):
        p = line.split('\t')
        if len(p) < 9 or p[1] != day.strftime('%Y/%m/%d'):
            continue
        stamp = dt.datetime.strptime(p[1] + ' ' + p[2], '%Y/%m/%d %H:%M:%S')
        rec.append({'t': stamp, 'RH': float(p[3]), 'T': float(p[5]),
                    'co2': float(p[7])})
    rec.sort(key=lambda r: r['t'])
    return rec


def ols(x, y):
    """Least-squares slope with its standard error and residual statistics."""
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    b = sxy / sxx
    a = my - b * mx
    resid = [yi - (a + b * xi) for xi, yi in zip(x, y)]
    s2 = sum(r * r for r in resid) / (n - 2)
    se = math.sqrt(s2 / sxx)
    syy = sum((yi - my) ** 2 for yi in y)
    r2 = 1 - sum(r * r for r in resid) / syy if syy > 0 else float('nan')
    return {'slope': b, 'intercept': a, 'se': se, 'rmse': math.sqrt(s2),
            'r2': r2, 'n': n}


def smooth_dtdt(rec, half=3):
    """Central-difference dT/dt in C/min over a plus/minus half-window."""
    out = []
    for i in range(len(rec)):
        lo = max(0, i - half)
        hi = min(len(rec) - 1, i + half)
        span = (rec[hi]['t'] - rec[lo]['t']).total_seconds() / 60.0
        out.append((rec[hi]['T'] - rec[lo]['T']) / span if span else 0.0)
    return out


def fit_phase(rec, t_start, t_stop, label):
    """Full-phase slope after settling, plus a quasi-steady sub-window."""
    seg = [r for r in rec if t_start <= r['t'] <= t_stop]
    settled = [r for r in seg
               if r['t'] >= t_start + dt.timedelta(minutes=SETTLE_MIN)]
    anchor = settled[0]['t']
    x = [(r['t'] - anchor).total_seconds() / 3600.0 for r in settled]
    full = ols(x, [r['co2'] for r in settled])

    rates = smooth_dtdt(settled)
    steady = [r for r, g in zip(settled, rates) if abs(g) < STEADY_DTDT]
    sub = None
    if len(steady) >= MIN_STEADY:
        anchor_s = steady[0]['t']
        xs = [(r['t'] - anchor_s).total_seconds() / 3600.0 for r in steady]
        sub = ols(xs, [r['co2'] for r in steady])
        sub['t_start'] = steady[0]['t'].strftime('%H:%M')
        sub['t_stop'] = steady[-1]['t'].strftime('%H:%M')
        sub['T_mean'] = sum(r['T'] for r in steady) / len(steady)

    return {'label': label,
            'window': [t_start.strftime('%H:%M'), t_stop.strftime('%H:%M')],
            'fit_from': anchor.strftime('%H:%M'),
            'n_raw': len(seg),
            'co2_start': seg[0]['co2'], 'co2_stop': seg[-1]['co2'],
            'T_start': seg[0]['T'], 'T_stop': seg[-1]['T'],
            'T_mean': sum(r['T'] for r in seg) / len(seg),
            'RH_mean': sum(r['RH'] for r in seg) / len(seg),
            'full': full, 'steady': sub}


def respiration(slope_ppm_h, t_celsius, headspace_l, mass_g):
    """Convert ppm/h in a fixed headspace to mg CO2 per kg of produce per hour."""
    if not mass_g:
        return None
    vm = 22.414 * (t_celsius + 273.15) / 273.15     # molar volume, L/mol at 1 atm
    litres_per_h = slope_ppm_h * 1e-6 * headspace_l
    return litres_per_h / vm * 44010.0 / (mass_g / 1000.0)


def main():
    node = read_node(NODE)
    extech = read_extech(EXTECH, DAY)
    node = [r for r in node if MARKS['t0'] <= r['t'] <= MARKS['tend']]
    ex = [r for r in extech if MARKS['t0'] <= r['t'] <= MARKS['tend']]

    phases = [fit_phase(node, MARKS['t0'], MARKS['t1'], 'A refrigerated'),
              fit_phase(node, MARKS['t1'], MARKS['t2'], 'B ambient breach'),
              fit_phase(node, MARKS['t2'], MARKS['tend'], 'C re-refrigerated')]

    ext_phases = [fit_phase(ex, MARKS['t0'], MARKS['t1'], 'A reference air'),
                  fit_phase(ex, MARKS['t1'], MARKS['t2'], 'B reference air'),
                  fit_phase(ex, MARKS['t2'], MARKS['tend'], 'C reference air')]

    for p in phases:
        use = p['steady'] or p['full']
        temp = use.get('T_mean', p['T_mean'])
        p['respiration_mg_kg_h'] = respiration(use['slope'], temp,
                                               HEADSPACE_L, MASS_G)

    res = {'date': DAY.isoformat(),
           'marks': {k: v.strftime('%H:%M') for k, v in MARKS.items()},
           'mass_g': MASS_G, 'headspace_l': HEADSPACE_L,
           'settle_min': SETTLE_MIN,
           'node': {'n': len(node), 'co2_first': node[0]['co2'],
                    'co2_last': node[-1]['co2']},
           'extech': {'n': len(ex),
                      'co2_min': min(r['co2'] for r in ex),
                      'co2_max': max(r['co2'] for r in ex),
                      'T_min': min(r['T'] for r in ex),
                      'T_max': max(r['T'] for r in ex)},
           'phases': phases, 'reference_phases': ext_phases}

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'expA_summary.json'), 'w') as fh:
        json.dump(res, fh, indent=2, default=str)

    print('EXP-A  %s   node n=%d   reference n=%d'
          % (DAY.isoformat(), len(node), len(ex)))
    print('headspace %.1f L, settling allowance %d min'
          % (HEADSPACE_L, SETTLE_MIN))
    print('')
    for p in phases:
        f = p['full']
        print('%-20s %s-%s   T %.1f to %.1f C (mean %.1f), RH %.0f pct'
              % (p['label'], p['window'][0], p['window'][1],
                 p['T_start'], p['T_stop'], p['T_mean'], p['RH_mean']))
        print('   CO2 %.0f to %.0f ppm' % (p['co2_start'], p['co2_stop']))
        print('   full phase    %+8.1f +/- %.1f ppm/h   n=%d  R2=%.3f  RMSE=%.0f ppm'
              % (f['slope'], f['se'], f['n'], f['r2'], f['rmse']))
        s = p['steady']
        if s:
            print('   quasi-steady  %+8.1f +/- %.1f ppm/h   %s-%s  n=%d  R2=%.3f  T=%.1f C'
                  % (s['slope'], s['se'], s['t_start'], s['t_stop'], s['n'],
                     s['r2'], s['T_mean']))
        else:
            print('   quasi-steady  none, temperature never settled')
        if p['respiration_mg_kg_h']:
            print('   respiration   %.0f mg CO2 per kg h' % p['respiration_mg_kg_h'])
        print('')

    print('Reference instrument, air beside the jar:')
    print('   T %.1f to %.1f C,  CO2 %.0f to %.0f ppm'
          % (res['extech']['T_min'], res['extech']['T_max'],
             res['extech']['co2_min'], res['extech']['co2_max']))
    for p in ext_phases:
        f = p['full']
        print('   %-18s %+8.1f +/- %.1f ppm/h   T mean %.1f C'
              % (p['label'], f['slope'], f['se'], p['T_mean']))


if __name__ == '__main__':
    main()
