# Analysis

`hercules.analysis` post-processes one Hercules simulation: POI limiting, energy, revenue,
storage metrics, accredited capacity, plotting and the ENPAX hand-off. Every public function
takes a single `HerculesOutput` as its first argument; combining simulations is left to the
user.

```python
from hercules import HerculesOutput
from hercules.analysis import energy_market, utilities

ho = HerculesOutput("outputs/hercules_output.h5")
utilities.add_POI_limited_columns(ho)
energy = utilities.compute_energy_annual_MWh(ho)
revenue = energy_market.compute_revenue_RT_annual(ho)
```

See example 05 (`analyze_outputs.py`) for a complete script.

## Rules

1. **Logged, not reconstructed.** Anything known during the simulation (prices, offers,
   offer prices, cleared amounts, SOC, peak flags) is logged by Hercules or Hycon and read
   back. Post-processing only computes integrals and aggregates of logged signals,
   settlement (two-settlement revenue, POI limiting), control-independent benchmarks (TBX)
   and region market determinations (RA hours, peak blocks, capacity prices).
2. **POI limiting comes first.** Hercules lets `plant.power_export` exceed
   `plant.interconnect_limit`. `utilities.add_POI_limited_columns` adds
   `analysis.plant.power_export_POI_limited`, `analysis.plant.power_export_POI_excess` and
   `analysis.<component>.power_POI_limited`. The cut is converted to the bus with
   `plant.efficiency_bus_to_poi` and taken only from components with positive power. It is
   distributed by an explicit `curtailment_order`, else the order logged by Hycon's
   supervisory controller (`controller.<name>.curtailment_rank_<component>`), else in
   proportion to positive power. A warning is raised when the removed energy exceeds
   `warn_fraction` of the exported energy.
3. **Delivered vs physical.** Energy, revenue, capacity factor, capacity market and ENPAX
   functions use the POI-limited columns (and add them if missing). Storage metrics use the
   raw logged signals, since the POI cut does not change what the equipment did.
4. **Names.** Columns added by analysis are prefixed `analysis.`. Function names are
   quantity-first with explicit non-default units (`compute_energy_total_MWh`,
   `compute_revenue_RT_annual`). Power is kW, energy kWh unless suffixed (`_MW`, `_MWh`),
   LMPs $/MWh, money `_USD`. Default column names are used only for Hercules channels;
   controller columns (`controller.<name>.<signal>`) are passed explicitly.
5. **Annual values** scale the simulation total by `hours_per_year` (default 8760) over the
   simulated hours.

## Modules

| Module | Contents |
|---|---|
| `utilities` | POI limiting, `add_columns`, simulation hours, energy (MWh), capacity factor |
| `storage` | Energy discharged, equivalent cycles (energy and SOC based), SOC mileage, mean SOC, rainflow damage |
| `energy_market` | RT, DA and two-settlement revenue; TBX arbitrage benchmark |
| `capacity_market` | Accredited capacity (class fraction x rating) and capacity revenue from region data |
| `regions` | `load_region` and region rules (`regions.miso`), see [Analysis regions](analysis_regions) |
| `plotting` | `plot_timeseries_plotly` |
| `enpax` | Case block for the ENPAX cost workflow, see [ENPAX hand-off](analysis_enpax) |

## Energy market

- `compute_revenue_RT_*` and `compute_revenue_DA_*` settle all energy at one price; charging
  is a cost.
- `compute_revenue_two_settlement_*(ho, power_column, power_cleared_DA_column)` pays the
  logged cleared DA power at the DA LMP and the deviation (delivered minus cleared) at the
  RT LMP. Returns `(total, DA, RT)`. `add_revenue_two_settlement_columns` adds the per-step
  values as `analysis.<name>_revenue_DA` and `analysis.<name>_revenue_RT`. Cleared DA above
  the POI is not curtailed; the shortfall settles at RT.
- `compute_revenue_TBX_*(ho, power_rated, duration_hours=4, ...)` is the perfect-foresight
  daily arbitrage benchmark, independent of the control. Prices are averaged into
  `block_minutes` blocks (60 for the published hourly TBX, 5 for sub-hourly RT); each day
  discharges in the most expensive `duration_hours` and charges in the cheapest
  `duration_hours / roundtrip_efficiency`. Days with too few blocks are dropped, and with
  `allow_skip` negative days earn 0. `day_timezone` sets the calendar day.

## Plotting

`plotting.plot_timeseries_plotly(ho, columns, ...)` draws one row per entry of `columns` (a
list entry shares a row), then plant export with its POI-limited value and the interconnect
limit, then the LMPs. `shade_columns` shades 0/1 columns (e.g. a logged peak flag) over all
rows. Long simulations are subsampled to at most 20000 points unless `plot_dt` is given.
