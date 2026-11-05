"""Table 5: recompute the GUM budget once the self-heating term is known.

Every entry of the table except the self-heating column is a constant of the
instruments and is written here; u_B3 comes from the EXP-C measurement and is
read from results/expC_selfheating.json. The combined and expanded
uncertainties are then computed rather than typed, so the table cannot drift
out of step with the measurement behind it.

    u_c  = sqrt(u_A^2 + u_B1^2 + u_B2^2 + u_B3^2)
    U    = 2 u_c
    U_comp = 2 sqrt(u_c^2 + u_ref^2)

The self-heating offset biases the temperature reading directly. It biases the
humidity reading as well, because the sensor refers an unchanged vapour
pressure to the saturation pressure at its own warmer temperature. The RH term
is the shift that the measured temperature offset entails, not the shift
observed in the record: the observed shift is about 2.5 times larger, which we
attribute to the humidity channel settling over the first minutes after
power-on rather than to a steady-state bias, and we will not carry a transient
into a service-life budget. The observed figure is reported in Section 4.8 so
that a reader can disagree with that judgement. It is not propagated into the CO2 rows: the
SCD41 is a photoacoustic sensor with internal temperature compensation, and the
breach-trial record gives no evidence of a CO2 offset tracking board
temperature, so a term is not invented for it.

Writes results/table5_budget.json and prints the rows in manuscript order.
"""
import json
import math
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPC = os.path.join(BASE, 'results', 'expC_selfheating.json')
OUT = os.path.join(BASE, 'results', 'table5_budget.json')

SQRT3 = math.sqrt(3.0)

# parameter, band, u_A, u_B1, u_B1 label, u_B2, u_ref, channel
ROWS = [
    ('Temperature (degC)', 'Validation 15-35 degC', 0.084, 0.462, '+-0.8 degC',
     0.087, 0.462, 'T'),
    ('Temperature (degC)', 'Application 0-10 degC', 0.084, 0.866, '+-1.5 degC',
     0.087, 0.462, 'T'),
    ('RH (%)', 'Validation 20-65 %RH', 0.433, 3.464, '+-6 %RH',
     0.722, 2.309, 'RH'),
    ('RH (%)', 'Application, high RH', 0.433, 5.196, '+-9 %RH',
     0.722, 2.656, 'RH'),
    ('CO2 (ppm)', '400-2000 ppm @1200 ppm', 3.11, 49.65, '+-86 ppm',
     16.74, 34.64, 'CO2'),
]


def fmt(v, channel):
    if channel == 'CO2':
        return '%.2f' % v if v < 100 else '%.0f' % v
    return '%.3f' % v


def main():
    if not os.path.exists(EXPC):
        raise SystemExit('run analyze_expC.py first: ' + EXPC + ' is missing')
    with open(EXPC) as fh:
        c = json.load(fh)

    delta_T = abs(c['self_heating_C'])
    delta_RH = abs(c.get('RH_shift_predicted_pct', 0.0))
    u_b3 = {'T': delta_T / SQRT3, 'RH': delta_RH / SQRT3, 'CO2': 0.0}

    # The offset is deterministic and repeatable, so a build that subtracted it
    # would not carry the whole of it as a bound. What would remain is the
    # uncertainty of the correction itself, which EXP-C measures: the spread
    # between runs, the quantisation of the two readings differenced, and the
    # scatter of the plateau. Carrying that instead of the rectangular bound is
    # the "corrected" column below. It is a projection of what a firmware change
    # would buy, not a measurement of a build that exists, and is labelled so.
    u_corr_T = c['self_heating_u_C']
    u_b3_corr = {'T': u_corr_T,
                 'RH': delta_RH * u_corr_T / delta_T if delta_T else 0.0,
                 'CO2': 0.0}

    print('self-heating offset   %+.3f degC   -> u_B3(T)  = %.3f degC'
          % (c['self_heating_C'], u_b3['T']))
    print('humidity shift        %+.2f %%RH entailed  -> u_B3(RH) = %.3f %%RH'
          % (c.get('RH_shift_predicted_pct', 0.0), u_b3['RH']))
    print('                      %+.2f %%RH observed  (settling, not carried)'
          % c.get('RH_shift_observed_pct', 0.0))
    print('CO2                   no term propagated (see module docstring)')
    print('')

    out = []
    for name, band, u_a, u_b1, lab, u_b2, u_ref, ch in ROWS:
        b3 = u_b3[ch]
        u_c = math.sqrt(u_a ** 2 + u_b1 ** 2 + u_b2 ** 2 + b3 ** 2)
        u_comp = math.sqrt(u_c ** 2 + u_ref ** 2)
        u_c_old = math.sqrt(u_a ** 2 + u_b1 ** 2 + u_b2 ** 2)
        b3c = u_b3_corr[ch]
        u_c_corr = math.sqrt(u_a ** 2 + u_b1 ** 2 + u_b2 ** 2 + b3c ** 2)
        row = {'parameter': name, 'band': band, 'u_A': u_a,
               'u_B1': u_b1, 'u_B1_label': lab, 'u_B2': u_b2, 'u_B3': b3,
               'u_c': u_c, 'U': 2 * u_c, 'u_ref': u_ref,
               'U_comp': 2 * u_comp,
               'u_c_without_B3': u_c_old, 'U_without_B3': 2 * u_c_old,
               'u_B3_corrected': b3c, 'U_corrected': 2 * u_c_corr}
        out.append(row)
        print('%-20s %-24s u_A %s  u_B1 %s (%s)  u_B2 %s  u_B3 %s'
              % (name, band, fmt(u_a, ch), fmt(u_b1, ch), lab,
                 fmt(u_b2, ch), fmt(b3, ch)))
        print('%-45s u_c %s  U %s  u_ref %s  U_comp %s      [U was %s]'
              % ('', fmt(u_c, ch), fmt(2 * u_c, ch), fmt(u_ref, ch),
                 fmt(2 * u_comp, ch), fmt(2 * u_c_old, ch)))

    with open(OUT, 'w') as fh:
        json.dump({'self_heating_C': c['self_heating_C'],
                   'RH_shift_pct': c.get('RH_shift_observed_pct'),
                   'u_B3': u_b3, 'u_B3_corrected': u_b3_corr,
                   'u_correction_C': u_corr_T, 'rows': out}, fh, indent=2)
    print('')
    print('written: ' + OUT)

    # The point of the exercise, stated so it cannot be glossed over.
    t = out[0]
    print('')
    print('Validation-band temperature: U goes %.2f -> %.2f degC, a %+.0f %% change.'
          % (t['U_without_B3'], t['U'],
             100.0 * (t['U'] / t['U_without_B3'] - 1.0)))
    ta = out[1]
    print('Application band:            U = %.2f degC as built, %.2f degC if the'
          % (ta['U'], ta['U_corrected']))
    print('offset were subtracted in firmware (residual u = %.3f degC).'
          % ta['u_B3_corrected'])
    if t['u_B3'] > t['u_B1']:
        print('Self-heating is now the LARGEST term in the temperature budget.')
        print('That has to be said in the text, not buried in the table.')


if __name__ == '__main__':
    sys.exit(main())
