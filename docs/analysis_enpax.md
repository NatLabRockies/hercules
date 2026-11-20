# ENPAX hand-off

`enpax.build_enpax_case(ho, region, zone, price_year=None)` returns the case block that the
ENPAX cost and ProFAST finance workflow reads for one simulation; `write_enpax_case_yaml`
writes it to a file. Collating cases and sites is done outside Hercules, and Hercules does
not import `enpax`.

```python
from hercules.analysis import enpax
from hercules.analysis.regions import load_region

case = enpax.write_enpax_case_yaml(ho, "case.yaml", load_region("miso"), zone=8)
```

There is one entry per component, keyed by component name. PVWatts solar maps to `solar`
and batteries to `battery`; other component types raise.

- Energy and energy revenue use the POI-limited columns.
- Energy revenue is two-settlement with `controller.<component>.power_cleared_DA` when
  logged; otherwise all energy settles at the RT LMP. Battery revenue is net of charging.
- Accredited capacity uses the region's rules (MISO: hourly availability at a shared POI,
  see [Analysis regions](analysis_regions)); capacity revenue uses the `price_year` prices
  (default: the latest year in the region data).

| Field | Applies to | Source |
|---|---|---|
| `interconnect_limit_MW` | plant | `plant.interconnect_limit` |
| `energy_annual_MWh` | plant | `analysis.plant.power_export_POI_limited`, annualized |
| `price_year` | plant | Argument |
| `type` | component | `solar` or `battery` |
| `DC_capacity_rated_MW` | component | Solar `DC_capacity_rated`; battery `null` |
| `capacity_rated_MW` | component | Solar `capacity_rated`; battery `power_discharge_max` |
| `energy_annual_MWh` | solar | `analysis.<component>.power_POI_limited`, annualized |
| `energy_capacity_MWh`, `duration_hours` | battery | `energy_capacity`, and divided by `power_discharge_max` |
| `energy_discharged_annual_MWh` | battery | Positive `<component>.power`, annualized |
| `cycle_count_equivalent_annual` | battery | Energy discharged / energy capacity |
| `revenue_energy_annual_USD` | component | Two-settlement total, annualized |
| `revenue_capacity_annual_USD` | component | Accredited MW x price x days, summed over seasons |
| `capacity_accredited_MW` | component | Day-weighted mean of the seasonal accredited capacity |
