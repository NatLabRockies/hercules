# Timing

Hercules uses a simplified, UTC-first time model where all simulations are referenced to coordinated universal time (UTC).

## Core Concepts

Timing in Hercules is specified using two complementary representations:

- `time` (float): Simulation time in seconds, where `time=0` corresponds to `starttime_utc`
- `time_utc` (datetime): Absolute UTC timestamp

## Time Interpretation: Inputs vs. Internal Values

### Input files: start-of-period convention

In external data sources such as weather files, SCADA records, and resource
databases, each `time_utc` timestamp marks the **beginning** of a reporting
period and the associated values (irradiance, wind speed, power, etc.)
represent an average or aggregate over that period.  For example, an hourly
weather file with a row at `2020-06-15T12:00:00Z` and GHI = 735 W/m² means
that 735 W/m² is the average GHI from 12:00 to 13:00.

### Hercules internal values: instantaneous convention

Inside the simulation, values at a given time step represent **instantaneous**
quantities at that moment.  All Hercules output values follow this same
instantaneous convention.

### Interpolation methods

The `interpolate_df` function in `utilities.py` accepts a mandatory
`interpolation_method` parameter that controls how numeric columns are
resampled onto the simulation time grid.  Two methods are available:

#### `"averaged_to_instantaneous"` (wind, solar, and similar resource and power signals)

Input values are period averages whose timestamps mark the **start** of each
period.  The best single-point estimate of a period-averaged value is at the
**midpoint** of its interval, not the start.  For example, the hourly average
from 12:00-13:00 is most representative of conditions at 12:30. This also ensures that an average of the signal back to the original time interval will match the original data.

1. Each numeric value is assigned to the midpoint of its input interval
   (using `_compute_interval_midpoints`).
2. Linear interpolation is then performed between these midpoints to produce
   values at the simulation time steps.

```
Input file (start-of-period):

time_utc             value
12:00                100        ← average over [12:00, 13:00)
13:00                200        ← average over [13:00, 14:00)

After midpoint correction:

time                 value
12:30                100        ← midpoint of [12:00, 13:00)
13:30                200        ← midpoint of [13:00, 14:00)

Querying at 13:00 yields 150 (halfway between midpoints).
```

#### `"instantaneous_to_instantaneous"`

Input values already represent instantaneous measurements at their
timestamps.  Standard linear interpolation is performed directly on the
original timestamps with no midpoint shift.

---

In both methods, datetime columns (e.g. `time_utc`) are linearly
interpolated on the raw timestamps without any shift, because they are
instantaneous coordinate mappings between simulation time and wall-clock
time, not period-averaged measurements.

#### Achieving zero-order-hold (ZOH) behaviour

`interpolate_df` does not provide a dedicated zero-order-hold mode.  If you
need step/piecewise-constant values -- for example, LMP prices that
should be held constant across each reporting interval -- pre-process your
input data to include an additional row at the end of each interval that
carries the same value as the start-of-interval row, and then use
`"instantaneous_to_instantaneous"`.  Linear interpolation between each pair
of identical endpoints reproduces the ZOH shape.

```
Original data (start-of-interval only):

time_utc             value
12:00                100
13:00                200

After inserting end-of-interval rows (just before the next start):

time_utc             value
12:00                100
12:59:59             100   ← added endpoint
13:00                200
13:59:59             200   ← added endpoint

Querying at 12:30 with "instantaneous_to_instantaneous" yields 100.
Querying at 13:00 yields 200.
```

See
[`generate_locational_marginal_price_dataframe_from_gridstatus`](../hercules/grid/grid_utilities.py)
in `hercules/grid/grid_utilities.py` for a worked example of this
endpoint-insertion pattern (it shifts a copy of the data by `dt - 1` seconds
and merges it back in before handing the frame to Hercules).

## Input Requirements

All Hercules input files must specify start and end times using UTC datetime strings:

- `starttime_utc`: The UTC datetime when the simulation begins (required in input YAML)
- `endtime_utc`: The UTC datetime when the simulation ends (required in input YAML)

These are the ONLY time parameters you need to specify in your input file. Example:

```yaml
dt: 1.0
starttime_utc: "2020-01-01T00:00:00Z"  # ISO 8601 format
endtime_utc: "2020-01-01T01:00:00Z"    # 1 hour simulation
```

### Datetime String Format (ISO 8601)

Hercules accepts UTC datetime strings in **ISO 8601** format. The variable names `starttime_utc` and `endtime_utc` indicate that these times must represent UTC (Coordinated Universal Time).

**Accepted formats:**
- **Explicit UTC with "Z" suffix**: `"2020-01-01T00:00:00Z"` - The "Z" (Zulu time) explicitly marks the time as UTC
- **Naive string (no timezone)**: `"2020-01-01T00:00:00"` - Without timezone info, treated as UTC

**Rejected formats:**
- **Timezone offsets**: `"2020-01-01T00:00:00+05:00"` or `"2020-01-01T00:00:00-08:00"` - These imply a different timezone, which contradicts the UTC requirement

**About ISO 8601:**
ISO 8601 is an international standard for representing dates and times. The format used by Hercules is:
- Date: `YYYY-MM-DD` (year-month-day)
- Separator: `T` (separates date and time)
- Time: `HH:MM:SS` (24-hour format)
- UTC marker: `Z` (optional but recommended for clarity)

Examples:
- `"2020-01-01T00:00:00Z"` - Midnight, January 1, 2020 UTC
- `"2020-06-15T12:30:45Z"` - 12:30:45 PM, June 15, 2020 UTC

When loading input files, Hercules validates that datetime strings don't contain timezone offsets and will raise a clear error if a non-UTC timezone is detected.

### Converting Local Time to UTC

If you only know your local time and need to convert it to UTC (accounting for daylight saving time), Hercules provides a utility function to help:

```python
from hercules.utilities import local_time_to_utc

# Midnight Jan 1, 2025 in Mountain Time (MST, UTC-7, no DST)
utc_time_jan = local_time_to_utc("2025-01-01T00:00:00", tz="America/Denver")
# Returns: "2025-01-01T07:00:00Z"

# Midnight July 1, 2025 in Mountain Time (MDT, UTC-6, DST in effect)
utc_time_july = local_time_to_utc("2025-07-01T00:00:00", tz="America/Denver")
# Returns: "2025-07-01T06:00:00Z"
```

**Note:** The `tz` parameter is **required**. You must specify your timezone using IANA timezone names.

**Available Timezone Names:**

Common timezone names:
- **US**: `"America/New_York"`, `"America/Chicago"`, `"America/Denver"`, `"America/Los_Angeles"`
- **Europe**: `"Europe/London"`, `"Europe/Paris"`, `"Europe/Berlin"`, `"Europe/Madrid"`
- **Asia**: `"Asia/Tokyo"`, `"Asia/Shanghai"`, `"Asia/Dubai"`, `"Asia/Kolkata"`
- **Pacific**: `"Pacific/Auckland"`, `"Pacific/Honolulu"`, `"Pacific/Sydney"`

**Complete list of timezones:**

For a complete list of all available IANA timezone names, see:
- [Wikipedia: List of tz database time zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)
- Or in Python:
```python
import zoneinfo
print(sorted(zoneinfo.available_timezones()))
```

The function automatically handles daylight saving time conversions based on the date you provide.

**Example usage in your input YAML:**

```python
from hercules.utilities import local_time_to_utc

# If you want midnight local time (Mountain Time) on Jan 1, 2025
start_utc = local_time_to_utc("2025-01-01T00:00:00", tz="America/Denver")
end_utc = local_time_to_utc("2025-07-01T00:00:00", tz="America/Denver")

# Use these values in your YAML:
# starttime_utc: "2025-01-01T07:00:00Z"
# endtime_utc: "2025-07-01T06:00:00Z"
```

## Computed Time Values

When Hercules loads your input file, it automatically computes:

- `starttime`: Always 0.0 (seconds)
- `endtime`: Simulation duration in seconds, computed as `(endtime_utc - starttime_utc).total_seconds()`

For the example above, `endtime` would be 3600.0 seconds.

## Data File Requirements

### Wind and Solar Input Data

Both wind and solar input CSV/Feather/Parquet files must contain a `time_utc` column with UTC timestamps.  Each `time_utc` value marks the **start of a reporting period**; the data values on that row are treated as period averages.  These are interpolated with `"averaged_to_instantaneous"`.  See [Interpolation methods](#interpolation-methods) above for details.

### External Data (LMP, etc.)

External data files loaded via `_read_external_data_file` are upsampled onto
the simulation time grid with `"instantaneous_to_instantaneous"` (linear
interpolation between the supplied timestamps).  If you want zero-order-hold
(piecewise-constant) behaviour for signals like LMP prices, pre-process the
file to include end-of-interval rows that repeat the previous value as
described in [Achieving zero-order-hold (ZOH) behaviour](#achieving-zero-order-hold-zoh-behaviour).
The helper
[`generate_locational_marginal_price_dataframe_from_gridstatus`](../hercules/grid/grid_utilities.py)
in `hercules/grid/grid_utilities.py` is a concrete example of adding those
endpoint rows for LMP data.

```text
time_utc,wd_mean,ws_000,ws_001,ws_002
2020-01-01T00:00:00Z,270.0,8.0,8.1,8.2
2020-01-01T00:00:01Z,270.5,8.1,8.2,8.3
...
```

The `time` column (numeric seconds from t=0) is computed internally by Hercules components and should NOT be included in your input files.

## Time Coordinate System

```
Timeline Visualization:

time (seconds):    0.0 ----------- duration (endtime) ----------->
                   |                                        |
                   |                                        |
time_utc:          |                                        |
                   v                                        v
                   starttime_utc                         endtime_utc
                   (datetime)                            (datetime)

Key Points:
• time=0 corresponds to starttime_utc
• time is always relative to starttime_utc
• All times advance together: time_utc = starttime_utc + timedelta(seconds=time)
```

## Output Files

All values in Hercules output files represent **instantaneous** quantities at each time step, not period averages.  See [Time Interpretation](#time-interpretation-inputs-vs-internal-values) for the distinction from input files.

Hercules output HDF5 files store:

- `time` array: Simulation time points (seconds from t=0)
- `step` array: Simulation step numbers
- `starttime_utc` metadata: Starting UTC timestamp (Unix timestamp format)
- `time_utc` column: Reconstructed UTC timestamps for each time point

The `time_utc` column in output data is reconstructed during read using:

```python
time_utc = starttime_utc + timedelta(seconds=time)
```

## Backward Compatibility

**Note for users with old output files:** Hercules maintains backward compatibility with output files created before this timing model change. Old files may contain `zero_time_utc` metadata instead of `starttime_utc`. The output reader automatically handles both formats.

## Consistency Validation

When multiple plant components (wind, solar) provide time-series data:

1. All input data files must contain `time_utc` columns
2. The `HybridPlant` class validates that all components' `starttime_utc` values match
3. A single `starttime_utc` value is promoted to the top level of `h_dict`

This ensures temporal consistency across all simulation components.

## Best Practices

1. **Always use UTC timestamps** in your input files to avoid timezone confusion
2. **Use ISO 8601 format** for datetime strings: `"YYYY-MM-DDTHH:MM:SSZ"`
3. **Ensure data coverage**: Your input data files must cover the full range from `starttime_utc` to `endtime_utc`
4. **Don't include `time` columns** in your input CSV files - Hercules computes these internally
5. **Match your dt**: Ensure your input data's temporal resolution is compatible with your simulation `dt`

## Example: Complete Timing Setup

```yaml
# hercules_input.yaml
name: example_simulation
dt: 1.0  # seconds

# Specify UTC times (REQUIRED)
starttime_utc: "2020-06-15T12:00:00Z"
endtime_utc: "2020-06-15T13:00:00Z"  # 1 hour simulation

plant:
  interconnect_limit: 50000  # kW

wind_farm:
  component_type: WindFarm
  wind_input_filename: inputs/wind_data.ftr
  # wind_data.ftr must have time_utc column covering the simulation period
  ...
```

Your `wind_data.ftr` file should contain:

```
time_utc                 | wd_mean | ws_000 | ws_001 | ...
-------------------------|---------|--------|--------|----
2020-06-15T12:00:00Z     | 270.0   | 8.0    | 8.1    | ...
2020-06-15T12:00:01Z     | 270.1   | 8.0    | 8.1    | ...
...
2020-06-15T13:00:00Z     | 271.5   | 8.2    | 8.3    | ...
```

Hercules will automatically compute the `time` column internally:

```
time_utc                 | time | ...
-------------------------|------|----
2020-06-15T12:00:00Z     | 0.0  | ...
2020-06-15T12:00:01Z     | 1.0  | ...
...
2020-06-15T13:00:00Z     | 3600.0 | ...
```
