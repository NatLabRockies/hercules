# MISO region data

Time series read by `hercules.analysis.regions.miso` through the paths in `../miso.yaml`,
which also lists their sources (`sources`).

| File | Contents | Made by |
|---|---|---|
| `miso_ra_hours.csv` | Flagged hours only: `time_utc` (start of hour), `subregion`, `hour_type` (`RA` or `AAOC`). Hours not listed but inside `RA_hours_coverage_utc` are not flagged | `generate_miso_ra_hours.py` |
| `miso_daily_peak_hours.ftr` | Start of each day's forecast (MTLF) peak-load hour (UTC) by peak zone | `prep_miso_inputs.py` |

To regenerate, put the raw MISO files in `untracked_raw_files/` (git-ignored; RA-hour
`*.xlsx` files at its top level, load files in `untracked_raw_files/load_forecast_and_actual/`),
run the scripts and update `sources` (and `RA_hours_coverage_utc`) in `../miso.yaml`. Within
NLR the raw files are on the NLR_Only team under `hercules_toolkit/raw_data`.
