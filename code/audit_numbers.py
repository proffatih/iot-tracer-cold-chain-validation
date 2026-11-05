"""Audit the built manuscript against the results files.

Checks the compiled .docx, not the source, because a number can be correct in
one paragraph of the source and stale in another, and because the table may be
generated. Two lists are applied:

  RETIRED  values that an earlier draft quoted and that must no longer appear
           anywhere in the document;
  REQUIRED values that a results file now supports and that must appear.

Run after every rebuild. Exits non-zero if anything fails.
"""
import json
import os
import re
import sys

from docx import Document

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCX = os.path.join(BASE, 'manuscript', 'IPA_R1_manuscript.docx')
RESULTS = os.path.join(BASE, 'results')

# A paragraph may quote a retired value on purpose. Section 4.8 states what the
# expanded uncertainty was before the self-heating term and what it is after,
# which is the whole point of the measurement; that sentence is exempt by name.
EXEMPT = 'raises the expanded uncertainty'

# expanded uncertainties before the self-heating term was measured
RETIRED = [
    ('0.95 °C', 'U(T) validation without u_B3'),
    ('1.75 °C', 'U(T) application without u_B3'),
    ('7.13 %', 'U(RH) validation without u_B3'),
    ('10.53 %', 'U(RH) application without u_B3'),
    ('1.33 °C', 'U_comp(T) without u_B3'),
    ('8.50 %', 'U_comp(RH) without u_B3'),
    ('three hours', 'breach excursion lasted 45 min'),
    ('repeated three times', 'the step test was a single transition'),
    ('11.46', 'idle current solved from a USB-side mean, disproved at the cell'),
    ('0.219 mA', 'mean implied by the withdrawn duty column'),
    ('factor of 53', 'the inconsistency as framed before the cell-side measurement'),
    ('11.74', 'Table 9a mean current built on the withdrawn idle figure'),
    ('5.52 mA', 'mean at one-minute sampling from the eyeballed durations'),
    ('50.9 days', 'endurance from the eyeballed durations'),
    ('1.66 mA', 'handheld idle reading, superseded by the logged 1.64 mA'),
    ('103 mA', 'display level from the handheld reading'),
    ('150 mA', 'peak from the handheld reading, logged peak is 162 mA'),
    ('62 days', 'idle-only ceiling from the eyeballed model'),
]

REQUIRED = [
    ('1.79 °C', 'U(T) validation'),
    ('2.32 °C', 'U(T) application'),
    ('7.66 %', 'U(RH) validation'),
    ('10.89 %', 'U(RH) application'),
    ('+1.32 °C', 'self-heating offset'),
    ('+0.60 °C', 'calibration offset from the power-on sample'),
    ('0.76 °C', 'u_B3'),
    ('+549', 'phase A accumulation slope'),
    ('+1126', 'phase B accumulation slope'),
    ('2.74', 'Q10'),
    ('441', 'persistent CO2 excess'),
    ('1.64 mA', 'idle current from the logged trace'),
    ('17.8', 'acquisition window, seconds'),
    ('1989', 'charge per acquisition, mA.s'),
    ('111 mA', 'mean current during the acquisition window'),
    ('4.99 mA', 'mean at ten-minute sampling'),
    ('35.1 mA', 'mean at the 59 s period logged'),
    ('3.2 days', 'endurance at one-minute sampling'),
]


def text_of(doc):
    parts = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return '\n'.join(parts)


def check_results_agree():
    """The prose figures must match what the results files actually say."""
    bad = []
    t5 = os.path.join(RESULTS, 'table5_budget.json')
    expc = os.path.join(RESULTS, 'expC_selfheating.json')
    if not os.path.exists(t5) or not os.path.exists(expc):
        return ['results/table5_budget.json or expC_selfheating.json is missing']
    b = json.load(open(t5))
    c = json.load(open(expc))
    want = {('Temperature (degC)', 'Validation 15-35 degC'): 1.79,
            ('Temperature (degC)', 'Application 0-10 degC'): 2.32,
            ('RH (%)', 'Validation 20-65 %RH'): 7.66,
            ('RH (%)', 'Application, high RH'): 10.89}
    for r in b['rows']:
        key = (r['parameter'], r['band'])
        if key in want and abs(r['U'] - want[key]) > 0.005:
            bad.append('%s %s: results say U = %.3f, audit expects %.2f'
                       % (key[0], key[1], r['U'], want[key]))
    if abs(c['self_heating_C'] - 1.316) > 0.005:
        bad.append('self-heating in results is %.3f, audit expects 1.316'
                   % c['self_heating_C'])
    em = os.path.join(RESULTS, 'energy_model.json')
    if os.path.exists(em):
        e = json.load(open(em))
        if abs(e['t_active_s'] - 17.8) > 0.1:
            bad.append('acquisition window in results is %.1f s, audit expects 17.8'
                       % e['t_active_s'])
        ten = next(r for r in e['rows'] if r['interval_min'] == 10)
        if abs(ten['as built']['mean_mA'] - 4.99) > 0.01:
            bad.append('10-min mean in results is %.2f mA, audit expects 4.99'
                       % ten['as built']['mean_mA'])
    else:
        bad.append('results/energy_model.json is missing')
    return bad


def main():
    if not os.path.exists(DOCX):
        raise SystemExit('build the manuscript first: ' + DOCX)
    body = text_of(Document(DOCX))
    body_nbsp = body.replace(' ', ' ')

    fails = []
    print('RETIRED values that must be gone:')
    for needle, why in RETIRED:
        lines = body_nbsp.split('\n')
        bad = [l for l in lines if needle in l and EXEMPT not in l]
        exempted = [l for l in lines if needle in l and EXEMPT in l]
        state = 'FOUND' if bad else ('ok (exempt)' if exempted else 'ok')
        print('   %-24s %-46s %s' % (needle, why, state))
        for l in bad[:1]:
            fails.append('stale %r (%s) in: %s' % (needle, why, l.strip()[:110]))

    print('')
    print('REQUIRED values that must be present:')
    for needle, why in REQUIRED:
        hit = needle in body_nbsp
        print('   %-24s %-46s %s' % (needle, why, 'ok' if hit else 'MISSING'))
        if not hit:
            fails.append('missing %r (%s)' % (needle, why))

    print('')
    print('Results files agree with the audit:')
    for msg in check_results_agree():
        print('   ' + msg)
        fails.append(msg)
    if not check_results_agree():
        print('   ok')

    print('')
    left = re.findall(r'\[PENDING[^\]]*\]', body_nbsp)
    print('PENDING markers left in the document: %d' % len(left))
    for m in left:
        print('   ' + m[:100])

    if fails:
        print('')
        print('FAILED, %d problem(s):' % len(fails))
        for f in fails:
            print('   ' + f)
        return 1
    print('')
    print('PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
