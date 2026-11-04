"""Figures for the cold-chain breach trial (EXP-A, 2026-11-03).

fig12b_breach_timeseries : temperature, RH and CO2 through the three phases,
                           node inside the sealed jar against the reference
                           instrument in the air beside it.
fig12c_breach_kinetics   : CO2 accumulation rate against headspace temperature,
                           from non-overlapping 15 min blocks, with the Q10 fit.
"""
import datetime as dt
import json
import math
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append('D:/claude_ai/_templates')
import pro_style
pro_style.apply()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_expA import read_node, read_extech, NODE, EXTECH, MARKS, OUT, DAY

FIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'figures')
C = pro_style.PALETTE
NODE_C, REF_C = C[0], C[6]
PHASE_FILL = {'A': '#DCE6F0', 'B': '#F6DCDC', 'C': '#DCE6F0'}


def load():
    node = [r for r in read_node(NODE)
            if MARKS['t0'] <= r['t'] <= MARKS['tend']]
    ref = [r for r in read_extech(EXTECH, DAY)
           if MARKS['t0'] <= r['t'] <= MARKS['tend']]
    det = json.load(open(os.path.join(OUT, 'expA_detection.json')))
    kin = json.load(open(os.path.join(OUT, 'expA_kinetics.json')))
    summ = json.load(open(os.path.join(OUT, 'expA_summary.json')))
    return node, ref, det, kin, summ


def shade(ax, lo, hi):
    for (a, b), key in (((MARKS['t0'], MARKS['t1']), 'A'),
                        ((MARKS['t1'], MARKS['t2']), 'B'),
                        ((MARKS['t2'], MARKS['tend']), 'C')):
        ax.axvspan(a, b, color=PHASE_FILL[key], zorder=0, lw=0)
    for m in (MARKS['t1'], MARKS['t2']):
        ax.axvline(m, color='#888', lw=0.8, ls=(0, (4, 3)), zorder=1)
    ax.set_ylim(lo, hi)
    ax.set_xlim(MARKS['t0'], MARKS['tend'])


def timeseries(node, ref, det, summ):
    fig, axes = plt.subplots(3, 1, figsize=(7.0, 7.2), sharex=True)
    t_n = [r['t'] for r in node]
    t_r = [r['t'] for r in ref]

    ax = axes[0]
    ax.plot(t_n, [r['T'] for r in node], color=NODE_C, lw=1.6,
            label='node, inside sealed jar')
    ax.plot(t_r, [r['T'] for r in ref], color=REF_C, lw=1.2, ls='--',
            label='reference, air beside jar')
    shade(ax, 0, 26)
    ax.set_ylabel('Temperature (\u00b0C)')
    ax.legend(loc='lower left', ncol=1, handlelength=2.4, borderaxespad=0.6)
    ax.text(0.012, 0.93, '(a)', transform=ax.transAxes, fontweight='bold',
            va='top')

    ax = axes[1]
    ax.plot(t_n, [r['RH'] for r in node], color=NODE_C, lw=1.6)
    ax.plot(t_r, [r['RH'] for r in ref], color=REF_C, lw=1.2, ls='--')
    shade(ax, 50, 105)
    ax.set_ylabel('Relative humidity (%)')
    ax.text(0.012, 0.93, '(b)', transform=ax.transAxes, fontweight='bold',
            va='top')

    ax = axes[2]
    ax.plot(t_n, [r['co2'] for r in node], color=NODE_C, lw=1.6)
    ax.plot(t_r, [r['co2'] for r in ref], color=REF_C, lw=1.2, ls='--')
    shade(ax, 400, 3650)
    ax.set_ylabel('CO$_2$ (ppm)')
    ax.set_xlabel('Clock time on 3 November 2026')
    ax.text(0.012, 0.93, '(c)', transform=ax.transAxes, fontweight='bold',
            va='top')

    # fitted slope annotations, placed inside each shaded band
    for p, frac in zip(summ['phases'], (0.210, 0.565, 0.855)):
        f = p['full']
        ax.text(frac, 0.935,
                '%+.0f ppm h$^{-1}$' % f['slope'],
                transform=ax.transAxes, ha='center', fontsize=8.5,
                color='#1a1a1a',
                bbox=dict(boxstyle='round,pad=0.28', fc='white', ec='#bbb',
                          lw=0.6, alpha=0.92))

    # phase captions along the top of panel (a)
    for label, frac in (('A  refrigerated', 0.210),
                        ('B  ambient breach', 0.565),
                        ('C  re-refrigerated', 0.855)):
        axes[0].text(frac, 1.035, label, transform=axes[0].transAxes,
                     ha='center', fontsize=9, color='#333')

    # breach alarm markers on the CO2 panel
    alarm = det['detection']['co2_slope_alarm']
    if alarm:
        at = dt.datetime.combine(DAY, dt.time(*map(int, alarm.split(':'))))
        ax.annotate('slope alarm\n+%.0f min'
                    % det['detection']['co2_slope_latency_min'],
                    xy=(at, 1850), xytext=(0.355, 0.60),
                    textcoords=axes[2].transAxes,
                    ha='right', fontsize=8, color=C[1],
                    arrowprops=dict(arrowstyle='->', color=C[1], lw=0.9,
                                    shrinkA=2, shrinkB=3))

    axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    axes[2].xaxis.set_major_locator(mdates.MinuteLocator(byminute=[0, 30]))
    fig.align_ylabels(axes)
    fig.subplots_adjust(hspace=0.12)
    for ext in ('pdf', 'png'):
        fig.savefig(os.path.join(FIG, 'fig12b_breach_timeseries.' + ext),
                    dpi=600 if ext == 'png' else None)
    plt.close(fig)


def kinetics(kin):
    fig, ax = plt.subplots(figsize=(5.4, 4.0))
    marks = {'A': ('o', C[0], 'A  refrigerated'),
             'B': ('s', C[1], 'B  ambient breach'),
             'C': ('^', C[2], 'C  re-refrigerated')}
    seen = set()
    for b in kin['blocks']:
        m, col, lab = marks[b['phase']]
        ax.errorbar(b['T_mean'], b['slope'], yerr=b['se'], fmt=m, color=col,
                    ms=6, capsize=2.5, lw=1.0, mec='white', mew=0.6,
                    label=lab if b['phase'] not in seen else None, zorder=3)
        seen.add(b['phase'])

    lo = min(b['T_mean'] for b in kin['blocks']) - 0.8
    hi = max(b['T_mean'] for b in kin['blocks']) + 0.8
    q10 = kin['Q10']
    rate = kin['rate_at_Tref_ppm_h']
    tref = kin['T_ref_C']
    xs = [lo + i * (hi - lo) / 120.0 for i in range(121)]
    ys = [rate * q10 ** ((x - tref) / 10.0) for x in xs]
    ax.plot(xs, ys, color='#555', lw=1.3, zorder=2,
            label='$Q_{10}$ fit, $Q_{10}$ = %.2f' % q10)
    los = [rate * kin['Q10_ci95'][0] ** ((x - tref) / 10.0) for x in xs]
    his = [rate * kin['Q10_ci95'][1] ** ((x - tref) / 10.0) for x in xs]
    ax.fill_between(xs, los, his, color='#555', alpha=0.10, lw=0, zorder=1)

    ax.set_yscale('log')
    ax.set_xlabel('Mean headspace temperature (\u00b0C)')
    ax.set_ylabel('CO$_2$ accumulation rate (ppm h$^{-1}$)')
    ax.set_xlim(lo, hi)
    ax.legend(loc='upper left')
    ax.grid(True, which='minor', alpha=0.12, lw=0.5)
    for ext in ('pdf', 'png'):
        fig.savefig(os.path.join(FIG, 'fig12c_breach_kinetics.' + ext),
                    dpi=600 if ext == 'png' else None)
    plt.close(fig)


def main():
    node, ref, det, kin, summ = load()
    os.makedirs(FIG, exist_ok=True)
    timeseries(node, ref, det, summ)
    kinetics(kin)
    print('wrote fig12b_breach_timeseries and fig12c_breach_kinetics')


if __name__ == '__main__':
    main()
