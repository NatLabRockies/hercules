# Timing

Timing in Hercules is specified by two primary variables:

- `time` (float): Time in seconds from `time=0` and the `zero_time_utc` value
- `time_utc` (datetime): Time in UTC (Coordinated Universal Time)

The `time` variable is always mandatory, while `time_utc` may be required for certain components (e.g., solar components).

## Important Metadata

- `zero_time_utc`: The UTC time corresponding to `time==0`. This is implied by the input data and doesn't need to be specified explicitly.
- `starttime`: The simulation start time value. Required in the [input file](hercules_input.md).
- `start_time_utc`: The UTC time corresponding to `starttime`. Implied by the data.
- `endtime`: The simulation end time value.  Required in the [input file](hercules_input.md).

## Input Requirements

Both [wind](wind.md) and [solar](solar_pv.md) inputs require a `time` column, while `time_utc` is optional for wind and mandatory for solar. A top-level `time` column is constructed based on the time step (`dt`) specified in the [input file](hercules_input.md) and logged at the top level of `h_dict`.

## Consistency

When both wind and solar inputs contain `time_utc` columns, the `HybridPlant` class ensures their `zero_time_utc` and `start_time_utc` values are consistent and brings them to the top level of `h_dict`.

## Logging

To save space, `time_utc` is not logged. However, `time`, `zero_time_utc`, and `start_time_utc` are logged, allowing `time_utc` to be reconstructed during [post-processing](output_files.md).

## Diagram

```
Timeline Visualization:

time (seconds):    0 -------- starttime -------- endtime
                   |           |               |
                   |           |               |
time_utc:          |           |               |
                   |           |               |
                   v           v               v
                   zero_time_utc start_time_utc end_time_utc
                   (datetime)   (datetime)     (datetime)

Key Points:
• time=0 corresponds to zero_time_utc
• starttime corresponds to start_time_utc  
• time_utc can be calculated as: zero_time_utc + timedelta(seconds=time)
```

