# EXP-A — Cold-chain interruption trial, run log

**Date:** 2026-11-03
**Node:** 7CDFA1FE05B5, sampling interval 60 s
**Reference instrument:** Extech SD800, placed beside the jar, moved with it through all three phases
**Container:** 1.7 L sealed glass jar (screw lid, no penetrations), headspace 1.4 L
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

- `data/A_breach_node.csv`   — node record (SCD41 CO2, T, RH), 60 s
- `data/A_breach_extech.csv` — Extech SD800 record, same window

## Notes

Phase A ran 65 min rather than the planned 45 min; this lengthens the pre-breach
baseline and improves the Phase A slope uncertainty rather than harming it.
