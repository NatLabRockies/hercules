# Analysis regions

Region market data (seasons, zones, accreditation fractions, capacity prices and time
series) is kept in a YAML file per region and read with `regions.load_region`:

```python
from hercules.analysis.regions import load_region

region = load_region("miso")  # built-in file
region = load_region("my_miso.yaml")  # edited copy, by path
```

Paths in `data_files` are relative to the YAML file. The dict is passed to
`capacity_market` functions and region modules.

## YAML keys

| Key | Contents |
|---|---|
| `name` | Region name (e.g. `MISO`); selects the region's accreditation rules in `enpax` |
| `sources` | Source and vintage of each table |
| `seasons` | Months of each season |
| `zones` | Zone id -> zone attributes (MISO: `subregion` for RA hours, `peak_zone` for peak hours) |
| `accreditation_fraction` | Accredited fraction of rated power by resource class (`solar`, `wind`, `battery`) and season |
| `capacity_price_USD_per_MW_day` | Capacity price by year, zone and season |
| `peak_block_duration_hours` | Length of the daily peak block (h) |
| `data_files` | Time-series files, relative to the YAML |

MISO also has `market_time_offset_hours` (EST, -5) and `RA_hours_coverage_utc` (time range
covered by the RA and AAOC hour files).

## Capacity market (any region)

`capacity_market.compute_capacity_accredited_seasonal_MW(ho, region, component)` is the
class fraction times the component's rated AC power (`capacity_rated`, or
`power_discharge_max` for storage), capped at `plant.interconnect_limit`.
`compute_capacity_accredited_MW` is the day-weighted mean over seasons and
`compute_revenue_capacity_annual` sums accredited MW x price x days per season. Both accept
seasonal values from a region module.

## MISO

- `miso.add_is_peak_column(ho, zone)` adds `analysis.is_peak`: 1 inside the 4 h block
  starting at each day's forecast (MTLF) peak-load hour of the zone.
- `miso.add_RA_hour_columns(ho, zone)` adds `analysis.season` (by the date in EST),
  `analysis.RA_hour` and `analysis.AAOC_hour` for the zone's subregion; NaN outside
  `RA_hours_coverage_utc`.
- `miso.compute_capacity_accredited_seasonal_MW(ho, zone, component)` applies MISO's
  hourly availability at a shared POI, with storage served first. Storage keeps the class
  value; a generator sharing the POI with storage is scaled, per season over the RA hours in
  the simulation, by

  $$\frac{\sum_h \min(P_h, \max(\mathrm{POI} - A_h, 0))}{\sum_h \min(P_h, \mathrm{POI})}$$

  where $P_h$ is the hourly mean `power_hypothetical` of the generators and $A_h$ the
  storage's available discharge (rated `power_discharge_max`, or a logged column passed in
  `storage_available_columns`).

The MISO time series and the scripts that make them are in
`hercules/analysis/regions/miso_data/` (see its README).
