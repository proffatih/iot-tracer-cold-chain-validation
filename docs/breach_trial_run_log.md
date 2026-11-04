# EXP-A — Cold-chain interruption trial, run log

**Date:** 2026-11-03
**Node:** 7CDFA1FE05B5, sampling interval 60 s
**Reference instrument:** Extech SD800, placed beside the jar, moved with it through all three phases
**Container:** 1.7 L sealed glass jar (screw lid, no penetrations); headspace taken as
1.65 L, the nominal volume less the volume displaced by the produce (13.49 g ≈ 13 mL)
and by the node assembly (≈ 40 mL). Not verified by filling; carry about 10 % on the
absolute respiration rates, none on Q10, which is a ratio of slopes.
**Load:** Agaricus bisporus, whole, unwashed, stem on, on greaseproof paper on the jar floor
**Node placement:** suspended from the lid, 5-10 cm above the load, sensor vent unobstructed

## Phase times (wall clock)

| Mark | Clock | t (min) | Event | Phase duration |
|------|-------|---------|-------|----------------|
| t0   | 14:10 | 0   | lid sealed, jar into refrigerator | — |
| t1   | 15:15 | 65  | jar removed to ambient (breach begins) | Phase A = 65 min |
| t2   | 16:00 | 110 | jar returned to refrigerator | Phase B = 45 min |
| tend | 16:45 | 155 | logging stopped | Phase C = 45 min |

Total run 155 min. Lid was not opened at any point during the run.

## Mass

Mushroom mass: 13.49 g (three whole caps, stems on, unwashed)

## Files

- `data/node_7CDFA1FE05B5_breach_2026-11-03.csv` — node record (SCD41 CO2, T, RH), 60 s
- `data/reference_extech_sd800_2026-11-03.tsv`  — Extech SD800 record; only the rows
  dated 2026/11/03 belong to this trial, earlier blocks are leftover records written
  with the instrument clock unset

## Notes

Phase A ran 65 min rather than the planned 45 min; this lengthens the pre-breach
baseline and improves the Phase A slope uncertainty rather than harming it.
