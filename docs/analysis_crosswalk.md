# Analysis crosswalk (hercules-toolkit)

`hercules.analysis` replaces hercules-toolkit. Each public toolkit function is
listed with its replacement, or the reason it was dropped. Toolkit LMP columns
`external_signals.lmp_da`/`lmp_rt` are now `external_signals.LMP_DA`/`LMP_RT`.

| Toolkit | `hercules.analysis` |
|---|---|
| `time.sim_hours` | `utilities.compute_simulation_hours` |
| `time.HOURS_IN_NON_LEAP_YEAR`, `HOURS_IN_LEAP_YEAR`, `DEFAULT_HOURS_IN_YEAR` | `utilities.HOURS_PER_YEAR`, `HOURS_PER_LEAP_YEAR` |
| `utilities.add_columns` | `utilities.add_columns` |
| `energy.compute_mwh_column` | `utilities.compute_energy_MWh_column` |
| `energy.compute_hourly_mwh_column` | `utilities.compute_energy_hourly_MWh_column` |
| `energy.compute_total_energy_mwh` | `utilities.compute_energy_total_MWh` |
| `energy.compute_annual_energy_mwh` | `utilities.compute_energy_annual_MWh` |
| `energy.compute_capacity_factor` | `utilities.compute_capacity_factor` (rating from the argument or the component; no fallback to `interconnect_limit`) |
| `revenue.add_poi_clipped_columns` | `utilities.add_POI_limited_columns` (plant limit distributed to components instead of clipping each column) |
| `revenue.compute_rt_revenue_total`, `_annual` | `energy_market.compute_revenue_RT_total`, `_annual` |
| `revenue.compute_da_revenue_total`, `_annual` | `energy_market.compute_revenue_DA_total`, `_annual` |
| `revenue.add_two_settlement_revenue_columns` | `energy_market.add_revenue_two_settlement_columns` (cleared DA power column only; missing cleared values count as 0) |
| `revenue.compute_two_settlement_revenue_total`, `_annual` | `energy_market.compute_revenue_two_settlement_total`, `_annual` (computed directly; no columns needed first) |
| `revenue.compute_tbx_revenue_total`, `_annual` | `energy_market.compute_revenue_TBX_total`, `_annual` |
| `revenue.compute_tbx_subhourly_revenue_total`, `_annual` | `energy_market.compute_revenue_TBX_total`, `_annual` with `block_minutes=5` |
| `revenue.add_cleared_da_columns` | Dropped: the controller logs `power_cleared_DA` |
| `revenue.add_grid_power_columns` | Dropped: the controller logs the surplus/grid charging split |
| `storage.compute_equivalent_cycles_total`, `_annual` | `storage.compute_cycle_count_equivalent_SOC_total`, `_annual` |
| `storage.compute_mileage_total`, `_annual` | `storage.compute_SOC_mileage_total`, `_annual` |
| `storage.compute_average_soc` | `storage.compute_SOC_mean` |
| `storage.compute_rainflow_cycle_damage_total`, `_annual` | `storage.compute_rainflow_damage_total`, `_annual` |
| `storage.add_charge_state` | Dropped: the controller logs its state |
| (new) | `storage.compute_energy_discharged_total_MWh`, `_annual_MWh`; `storage.compute_cycle_count_equivalent_total`, `_annual` (energy discharged / energy capacity) |
| `miso.get_ucap_percent`, `get_pra`, `get_subregion`, `get_valid_zones_for_peak_load_times` | `regions.load_region("miso")` tables |
| `miso.get_days_per_season` | Private in `capacity_market` |
| `miso.print_capacity_revenue_summary` | `capacity_market.compute_capacity_accredited_seasonal_MW`, `compute_capacity_accredited_MW`, `compute_revenue_capacity_annual` and `regions.miso.compute_capacity_accredited_seasonal_MW` (return values, no printing) |
| `miso.add_is_peak_column` | `regions.miso.add_is_peak_column(ho, zone)` (integer zone; adds `analysis.is_peak`) |
| `miso.add_ra_hour_columns` | `regions.miso.add_RA_hour_columns(ho, zone)` (adds `analysis.season`, `analysis.RA_hour`, `analysis.AAOC_hour`; planning year dropped) |
| `miso.add_battery_offer_columns` | Dropped: the controller logs offers |
| `plotting.plot_timeseries` | `plotting.plot_timeseries_plotly` (one simulation, no scenario overlay) |
| (new) | `enpax.build_enpax_case`, `enpax.write_enpax_case_yaml` |

## Behaviour changes

- Toolkit two-settlement sums skip rows where the cleared DA value is NaN, which also drops
  the RT revenue of those rows; missing cleared DA now counts as 0.
- Toolkit DA clearing curtailed the highest-priced cleared offer at the POI. Cleared DA is
  now logged by the controllers without POI curtailment, and any over-commitment settles
  at RT.
