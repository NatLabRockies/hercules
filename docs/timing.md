# Timing

Hercules uses a simplified, UTC-first time model where all simulations are referenced to coordinated universal time (UTC).

## Core Concepts

Timing in Hercules is specified using two complementary representations:

- `time` (float): Simulation time in seconds, where `time=0` corresponds to `starttime_utc`
- `time_utc` (datetime): Absolute UTC timestamp

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

Both wind and solar input CSV/Feather/Parquet files must contain a `time_utc` column with UTC timestamps:

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
  component_type: Wind_MesoToPower
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
