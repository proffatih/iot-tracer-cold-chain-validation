"""Segment the logging-multimeter trace of the node's supply current.

The meter was placed in series with the cell and logged at about 2 Hz while the
node was taken through its states. The trace is reduced here into runs above
and below a threshold, so that the duration and level of each active window can
be read off rather than timed by eye, and so that the mean current over the
part of the record where the node is cycling autonomously can be integrated
rather than modelled.

Everything printed is derived from the file; nothing is assumed about which
minute corresponds to which state.

Writes results/current_log.json.
"""
import datetime as dt
import io
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, 'data')
OUT = os.path.join(BASE, 'results')

THRESHOLD_MA = 10.0      # anything above this is an active window
MIN_RUN_S = 1.0          # ignore runs shorter than this when listing


def find_logs():
    out = []
    for root in (DATA, os.path.join(BASE, 'RTEU_Tracer')):
        if not os.path.isdir(root):
            continue
        for fn in sorted(os.listdir(root)):
            if fn.lower().startswith('bdm') and fn.lower().endswith('.csv'):
                out.append(os.path.join(root, fn))
    if not out:
        raise SystemExit('no BDM*.csv ammeter log found')
    return out


def read_log(path):
    rows = []
    for line in io.open(path, encoding='latin-1'):
        parts = [q.strip() for q in line.split(',')]
        if len(parts) < 6:
            continue
        try:
            val = float(parts[2])
        except ValueError:
            continue
        unit = parts[3].lower()
        if unit.startswith('ua') or unit.startswith('\xb5a'):
            val /= 1000.0
        elif unit == 'a':
            val *= 1000.0
        try:
            stamp = dt.datetime.strptime(parts[5] + ' ' + parts[4],
                                         '%d.%m.%Y %H:%M:%S')
        except ValueError:
            continue
        rows.append({'t': stamp, 'mA': val})
    rows.sort(key=lambda r: r['t'])
    return rows


def runs(rows, threshold=THRESHOLD_MA):
    """Split into consecutive stretches above and below the threshold."""
    out = []
    cur = None
    for r in rows:
        hi = r['mA'] > threshold
        if cur is None or cur['high'] != hi:
            if cur is not None:
                out.append(cur)
            cur = {'high': hi, 'start': r['t'], 'stop': r['t'], 'v': [r['mA']]}
        else:
            cur['stop'] = r['t']
            cur['v'].append(r['mA'])
    if cur is not None:
        out.append(cur)
    for c in out:
        c['dur_s'] = (c['stop'] - c['start']).total_seconds()
        c['mean'] = sum(c['v']) / len(c['v'])
        c['max'] = max(c['v'])
        c['min'] = min(c['v'])
        c['n'] = len(c['v'])
    return out


def integrate(rows):
    """Time-weighted mean over the samples given, trapezoid on the timestamps."""
    if len(rows) < 2:
        return float('nan'), 0.0
    num = 0.0
    den = 0.0
    for a, b in zip(rows, rows[1:]):
        dtv = (b['t'] - a['t']).total_seconds()
        if dtv <= 0 or dtv > 10:        # skip gaps
            continue
        num += 0.5 * (a['mA'] + b['mA']) * dtv
        den += dtv
    return (num / den if den else float('nan')), den


CYCLE_IDLE_S = (25.0, 55.0)      # a clean cycle's idle stretch
CYCLE_ACTIVE_S = (8.0, 30.0)     # and its active window
CELL_MAH = 2600.0
I_LEAK_MA = 0.025 * CELL_MAH / (30.0 * 24.0)
PROJECT_MIN = [1, 5, 10, 15, 30, 60]


def charge_mAs(rows, start, stop):
    """Integrate current over a window, trapezoid on the timestamps."""
    seg = [r for r in rows if start <= r['t'] <= stop]
    q = 0.0
    for a, b in zip(seg, seg[1:]):
        d = (b['t'] - a['t']).total_seconds()
        if 0 < d <= 10:
            q += 0.5 * (a['mA'] + b['mA']) * d
    return q


def clean_cycles(rows, seq):
    """Idle stretch of the expected length followed by one active window.

    The record also contains operator-initiated events - a long block at
    start-up and several further long or back-to-back active windows - which
    are not part of the node's own schedule. Requiring both parts of a cycle
    to fall in the expected range excludes them without having to label them.
    """
    out = []
    for a, b in zip(seq, seq[1:]):
        if a['high'] or not b['high']:
            continue
        if not (CYCLE_IDLE_S[0] <= a['dur_s'] <= CYCLE_IDLE_S[1]):
            continue
        if not (CYCLE_ACTIVE_S[0] <= b['dur_s'] <= CYCLE_ACTIVE_S[1]):
            continue
        out.append({'idle_start': a['start'], 'idle_s': a['dur_s'],
                    'idle_mA': a['mean'],
                    'active_start': b['start'], 'active_s': b['dur_s'],
                    'active_mA': b['mean'], 'active_max': b['max'],
                    'q_active_mAs': charge_mAs(rows, b['start'], b['stop']),
                    'period_s': a['dur_s'] + b['dur_s']})
    return out


def project(q_active_mAs, t_active_s, i_idle_mA):
    """Mean current and endurance if the same active window ran every I."""
    rows = []
    for m in PROJECT_MIN:
        i_s = m * 60.0
        if i_s <= t_active_s:
            continue
        mean = (q_active_mAs + i_idle_mA * (i_s - t_active_s)) / i_s + I_LEAK_MA
        rows.append({'interval_min': m, 'mean_mA': mean,
                     'days': CELL_MAH / mean / 24.0})
    return rows


def main():
    paths = find_logs()
    all_res = []
    for path in paths:
        rows = read_log(path)
        if len(rows) < 20:
            continue
        span = (rows[-1]['t'] - rows[0]['t']).total_seconds()
        rate = (len(rows) - 1) / span if span else float('nan')
        print('=' * 72)
        print('%s' % os.path.basename(path))
        print('   %d samples, %s to %s, %.1f min, about %.1f Hz'
              % (len(rows), rows[0]['t'].strftime('%H:%M:%S'),
                 rows[-1]['t'].strftime('%H:%M:%S'), span / 60.0, rate))

        seq = runs(rows)
        print('')
        print('   runs above/below %.0f mA:' % THRESHOLD_MA)
        print('      %-10s %-6s %7s %9s %9s %9s'
              % ('start', 'state', 'dur s', 'mean mA', 'min mA', 'max mA'))
        for c in seq:
            if c['dur_s'] < MIN_RUN_S and c['n'] < 3:
                continue
            print('      %-10s %-6s %7.1f %9.2f %9.2f %9.2f'
                  % (c['start'].strftime('%H:%M:%S'),
                     'ACTIVE' if c['high'] else 'idle',
                     c['dur_s'], c['mean'], c['min'], c['max']))

        lows = [c for c in seq if not c['high'] and c['dur_s'] >= 5]
        highs = [c for c in seq if c['high'] and c['dur_s'] >= 2]
        idle_v = [v for c in lows for v in c['v'] if v > 0.2]
        off_v = [v for c in lows for v in c['v'] if v <= 0.2]

        print('')
        if idle_v:
            print('   idle level      %.3f mA   (%d samples, spread %.3f-%.3f)'
                  % (sum(idle_v) / len(idle_v), len(idle_v),
                     min(idle_v), max(idle_v)))
        if off_v:
            print('   zero/off level  %d samples at or below 0.2 mA' % len(off_v))
        if highs:
            durs = sorted(c['dur_s'] for c in highs)
            print('   active windows  %d of them, %.1f-%.1f s (median %.1f s)'
                  % (len(highs), durs[0], durs[-1], durs[len(durs) // 2]))
            print('   active level    %.1f mA mean, %.1f mA peak'
                  % (sum(c['mean'] * c['dur_s'] for c in highs)
                     / sum(c['dur_s'] for c in highs),
                     max(c['max'] for c in highs)))

        # the autonomous part: from the first idle run that is followed by a
        # repeating pattern, i.e. skip the startup block at the beginning
        tail_start = None
        for i, c in enumerate(seq):
            if not c['high'] and c['dur_s'] >= 15 and i > 2:
                tail_start = c['start']
                break
        if tail_start is not None:
            tail = [r for r in rows if r['t'] >= tail_start]
            mean, dur = integrate(tail)
            print('')
            print('   from %s to the end (%.1f min of autonomous cycling):'
                  % (tail_start.strftime('%H:%M:%S'), dur / 60.0))
            print('      time-weighted mean current  %.2f mA' % mean)
            print('      projected endurance on 2600 mAh  %.1f days'
                  % (2600.0 / mean / 24.0))
            cyc = [c for c in runs(tail) if c['high'] and c['dur_s'] >= 2]
            if len(cyc) > 1:
                periods = [(b['start'] - a['start']).total_seconds()
                           for a, b in zip(cyc, cyc[1:])]
                periods.sort()
                print('      %d active windows, period %.0f-%.0f s (median %.0f s)'
                      % (len(cyc), periods[0], periods[-1],
                         periods[len(periods) // 2]))
                dd = sorted(c['dur_s'] for c in cyc)
                print('      window duration %.1f-%.1f s (median %.1f s), duty %.1f %%'
                      % (dd[0], dd[-1], dd[len(dd) // 2],
                         100.0 * sum(c['dur_s'] for c in cyc) / dur))
        else:
            mean, dur = integrate(rows)
            print('')
            print('   whole-record time-weighted mean %.2f mA over %.1f min'
                  % (mean, dur / 60.0))

        cycles = clean_cycles(rows, seq)
        proj = []
        cyc_summary = None
        if cycles:
            n = len(cycles)
            idle_mA = sum(c['idle_mA'] for c in cycles) / n
            t_act = sum(c['active_s'] for c in cycles) / n
            q_act = sum(c['q_active_mAs'] for c in cycles) / n
            period = sum(c['period_s'] for c in cycles) / n
            sd_t = (sum((c['active_s'] - t_act) ** 2 for c in cycles)
                    / max(n - 1, 1)) ** 0.5
            sd_q = (sum((c['q_active_mAs'] - q_act) ** 2 for c in cycles)
                    / max(n - 1, 1)) ** 0.5
            print('')
            print('   CLEAN CYCLES (idle %.0f-%.0f s then one active window'
                  ' %.0f-%.0f s)' % (CYCLE_IDLE_S + CYCLE_ACTIVE_S))
            print('      %d of them, period %.0f s' % (n, period))
            print('      idle          %.3f mA' % idle_mA)
            print('      active window %.1f +/- %.1f s, %.0f mA mean, %.0f mA peak'
                  % (t_act, sd_t,
                     sum(c['active_mA'] for c in cycles) / n,
                     max(c['active_max'] for c in cycles)))
            print('      charge per window %.0f +/- %.0f mA*s' % (q_act, sd_q))
            measured = (q_act + idle_mA * (period - t_act)) / period + I_LEAK_MA
            print('      mean current at the %.0f s period actually logged'
                  '  %.2f mA' % (period, measured))
            print('      endurance there  %.1f days'
                  % (CELL_MAH / measured / 24.0))
            print('')
            print('      projected to other sampling intervals, same window:')
            proj = project(q_act, t_act, idle_mA)
            for r in proj:
                print('         %3d min  %8.2f mA  %7.1f days'
                      % (r['interval_min'], r['mean_mA'], r['days']))
            cyc_summary = {'n': n, 'idle_mA': idle_mA,
                           'active_s': t_act, 'active_s_sd': sd_t,
                           'q_active_mAs': q_act, 'q_active_sd': sd_q,
                           'period_s': period, 'measured_mean_mA': measured,
                           'measured_days': CELL_MAH / measured / 24.0,
                           'projection': proj}

        all_res.append({
            'file': os.path.basename(path),
            'start': rows[0]['t'].strftime('%Y-%m-%d %H:%M:%S'),
            'stop': rows[-1]['t'].strftime('%H:%M:%S'),
            'n': len(rows), 'rate_hz': rate,
            'idle_mA': (sum(idle_v) / len(idle_v)) if idle_v else None,
            'cycles': cyc_summary,
            'runs': [{'start': c['start'].strftime('%H:%M:%S'),
                      'state': 'active' if c['high'] else 'idle',
                      'dur_s': c['dur_s'], 'mean_mA': c['mean'],
                      'max_mA': c['max']} for c in seq],
        })

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'current_log.json'), 'w') as fh:
        json.dump(all_res, fh, indent=2)
    print('')
    print('written: ' + os.path.join(OUT, 'current_log.json'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
