"""Energy model for the node, and the resolution of the Table 9 inconsistency.

Table 9 of the initial submission reports a measured weighted average of
11.6 mA (43 mW) over a 10 min cycle, and separately a duty column of 99.4 %
deep sleep at 7 uA, 0.5 % active sensing at 38 mA and 0.1 % display refresh at
22 mA. Those two statements are not compatible: the duty column implies about
0.22 mA. The measured average and the reported endurance on a 2600 mAh cell do
agree with each other, so the duty column is the item in error.

Taking the measured average and the active windows as given, this script solves
for the current drawn between samples. The result is about 11.5 mA, three
orders of magnitude above the 7 uA deep-sleep figure, which means the node does
not deep-sleep between samples: the radio and board peripherals stay powered.

It then tabulates mean current and endurance against sampling interval for the
measured always-on regime and for a gated regime in which the node does reach
the measured 7 uA sleep state between samples.

Writes results/energy_model.json.
"""
import json
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'results')

V_BATT = 3.7           # V, nominal cell voltage
CAP_MAH = 2600.0       # 18650 cell, nominal capacity at 20 C

I_ACT_MA = 38.0        # measured, active sensing (I2C + CPU)
T_ACT_S = 3.0          # per cycle, from the 0.5 % duty of a 10 min cycle
I_DISP_MA = 22.0       # measured, e-paper refresh
T_DISP_S = 0.6         # per cycle, from the 0.1 % duty of a 10 min cycle
I_SLEEP_MA = 0.007     # measured board deep-sleep current, includes regulator

I_MEAN_MEASURED_MA = 11.6     # measured weighted average over a 10 min cycle
I_REF_S = 600.0               # the cycle that average was measured over

# 18650 self-discharge, 2.5 % per month, expressed as a continuous current
I_LEAK_MA = 0.025 * CAP_MAH / (30.0 * 24.0)

INTERVALS_MIN = [5, 10, 15, 30, 60]


def idle_current_from_measurement():
    """Solve the measured 10 min cycle for the current drawn between samples."""
    charge = I_MEAN_MEASURED_MA * I_REF_S          # mA s
    charge -= I_ACT_MA * T_ACT_S
    charge -= I_DISP_MA * T_DISP_S
    return charge / (I_REF_S - T_ACT_S - T_DISP_S)


def mean_current(interval_s, i_idle_ma, i_leak_ma):
    idle_s = interval_s - T_ACT_S - T_DISP_S
    charge = I_ACT_MA * T_ACT_S + I_DISP_MA * T_DISP_S + i_idle_ma * idle_s
    return charge / interval_s + i_leak_ma


def main():
    i_idle = idle_current_from_measurement()
    implied_by_duty = (I_ACT_MA * T_ACT_S + I_DISP_MA * T_DISP_S
                       + I_SLEEP_MA * (I_REF_S - T_ACT_S - T_DISP_S)) / I_REF_S

    rows = []
    for mins in INTERVALS_MIN:
        s = mins * 60.0
        a = mean_current(s, i_idle, 0.0)             # measured regime
        b = mean_current(s, I_SLEEP_MA, I_LEAK_MA)   # gated regime
        rows.append({'interval_min': mins,
                     'measured_regime_mA': a,
                     'measured_regime_h': CAP_MAH / a,
                     'measured_regime_d': CAP_MAH / a / 24.0,
                     'gated_regime_mA': b,
                     'gated_regime_h': CAP_MAH / b,
                     'gated_regime_d': CAP_MAH / b / 24.0})

    res = {'cell_mAh': CAP_MAH, 'cell_Wh': CAP_MAH * V_BATT / 1000.0,
           'i_active_mA': I_ACT_MA, 't_active_s': T_ACT_S,
           'i_display_mA': I_DISP_MA, 't_display_s': T_DISP_S,
           'i_sleep_mA': I_SLEEP_MA, 'i_leak_mA': I_LEAK_MA,
           'i_mean_measured_mA': I_MEAN_MEASURED_MA,
           'implied_by_duty_column_mA': implied_by_duty,
           'inconsistency_factor': I_MEAN_MEASURED_MA / implied_by_duty,
           'idle_current_solved_mA': i_idle,
           'idle_vs_sleep_ratio': i_idle / I_SLEEP_MA,
           'rows': rows}

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'energy_model.json'), 'w') as fh:
        json.dump(res, fh, indent=2)

    print('cell %.0f mAh (%.2f Wh) at %.1f V' % (CAP_MAH, res['cell_Wh'], V_BATT))
    print('')
    print('Table 9 as published is internally inconsistent:')
    print('   duty column implies        %.3f mA' % implied_by_duty)
    print('   measured weighted average  %.3f mA' % I_MEAN_MEASURED_MA)
    print('   factor                     %.0fx' % res['inconsistency_factor'])
    print('')
    print('Solving the measured cycle for the current between samples:')
    print('   i_idle = %.2f mA, which is %.0fx the measured 7 uA sleep current'
          % (i_idle, res['idle_vs_sleep_ratio']))
    print('   -> the node does not deep-sleep between samples')
    print('')
    print('%-10s %12s %10s %12s %12s'
          % ('interval', 'measured', 'endurance', 'gated', 'endurance'))
    print('%-10s %12s %10s %12s %12s'
          % ('(min)', '(mA)', '(d)', '(mA)', '(d)'))
    for r in rows:
        print('%-10d %12.2f %10.1f %12.3f %12.0f'
              % (r['interval_min'], r['measured_regime_mA'],
                 r['measured_regime_d'], r['gated_regime_mA'],
                 r['gated_regime_d']))
    print('')
    print('leak term used in the gated regime: %.3f mA (2.5 %%/month self-discharge)'
          % I_LEAK_MA)


if __name__ == '__main__':
    main()
