# IoT-Tracer — cold-chain validation data and analysis

Measurement records, analysis code and derived results supporting the metrological
validation of IoT-Tracer, a battery-powered sensor node that logs temperature,
relative humidity and CO₂ for food cold-chain monitoring.

Everything here is raw instrument output plus the scripts that turn it into the
numbers and figures in the paper. No value in the paper is entered by hand.

## What is in here

### `data/`

| File | What it is |
|---|---|
| `node_7CDFA1FE05B5_breach_2026-11-03.csv` | Cold-chain breach trial. Node inside a sealed 1.7 L glass jar with 13.49 g of whole button mushrooms. Columns: temperature (°C), relative humidity (%), CO₂ (ppm), timestamp (`d/m/Y H:M`), flag. One-minute sampling. |
| `reference_extech_sd800_2026-11-03.tsv` | Extech SD800 reference logger, carried alongside the jar through all three phases, logging the air immediately beside it. Tab-separated as written by the instrument; only the rows dated `2026/11/03` belong to this trial, the earlier blocks are leftover records with the instrument clock unset. |
| `refrigerator _7CDFA1FE05B5_05102026.csv` | 2026-10-02 to 2026-10-04 run in a domestic refrigerator with no produce present: the control condition, and the source of the compressor-cycle and step-response results. Four separate logging blocks appended end to end. |
| `parsed_05102026_two_streams.csv` | The same record split into its blocks and labelled. |
| `fridge_steady_window.csv` | The steady 31.6 h window used for the compressor-cycle statistics. |

### `code/`

| Script | What it does |
|---|---|
| `analyze_expA.py` | Segments the breach trial into its three phases, fits CO₂ accumulation slopes with standard errors, converts to mass-specific respiration. |
| `analyze_expA_kinetics.py` | Non-overlapping 15-minute blocks; log-linear fit of accumulation rate against temperature, giving Q₁₀. |
| `analyze_expA_detection.py` | Rolling-window alarm latency for both channels, and the CO₂ excess that persists after the temperature has recovered. |
| `analyze_expA_thermal.py` | First-order fits for the thermal time constant of the sealed package. |
| `energy_model.py` | Mean current and projected endurance against sampling interval; also resolves the internal inconsistency in the published per-mode energy table. |
| `make_fig_breach.py`, `make_fig_setup.py`, `make_fig_fridge.py` | Figures. |
| `make_data_repo.py` | Assembles this repository from the working tree. |

Run them from the repository root, in any order except that the figure scripts
need the analysis scripts to have written `results/` first:

```
python code/analyze_expA.py
python code/analyze_expA_kinetics.py
python code/analyze_expA_detection.py
python code/analyze_expA_thermal.py
python code/energy_model.py
python code/make_fig_breach.py
```

Python 3.8 or later. The analysis scripts use only the standard library; the
figure scripts additionally need `matplotlib`.

### `results/`

JSON written by the analysis scripts. Every number quoted in the paper for the
breach trial and for the energy model can be found in one of these files.

### `figures/`

Vector PDF and 600 dpi PNG, as submitted.

### `docs/`

Bench run log for the breach trial, and photographs of the rig at each stage:
the produce on the balance, the reference logger in the refrigerator, the sealed
jar in place, the jar at ambient during the breach, and the return to
refrigeration.

## What is not in here

Device firmware and the mobile application source are not included in this
repository. The data-availability statement in the paper should be read as
covering the measurement records and analysis code only.

## Headline results from the breach trial

| Phase | Condition | CO₂ accumulation |
|---|---|---|
| A, 65 min | refrigerated | +549 ± 8 ppm h⁻¹ |
| B, 45 min | ambient breach | +1126 ± 20 ppm h⁻¹ |
| C, 45 min | re-refrigerated | +498 ± 20 ppm h⁻¹ |

The excursion raised the accumulation rate by a factor of 2.05, a separation of
26.5 standard errors. After re-cooling the temperature returned to within 0.2 °C
of its pre-breach baseline while headspace CO₂ retained a 441 ppm excess over the
no-breach expectation, at 7.5 σ. A log-linear fit across the 11.0–21.3 °C range
the run sweeps gives Q₁₀ = 2.74 (95 % CI 2.15–3.48), recovered from the node's
own temperature and CO₂ channels with no external reference.

## Licence

Code is released under the MIT Licence (see `LICENSE`). The measurement records
and photographs are released under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Citation

A citation block will be added here when the paper is published.
