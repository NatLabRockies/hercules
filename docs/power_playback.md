# Power Playback

`PowerPlayback` plays back pre-recorded power data from a file, treating the recorded values as the output of a generic power-generating unit. There is no control interface — the power values are replayed exactly as stored.

This component is useful for incorporating measured or externally modeled power output into a hybrid plant simulation without needing to model the underlying physics of the generator.

The PowerPlayback model is intended for use for using the power output from a generator component in a Hercules simulation. This component can be used for all generators, but will only take in the total plant power from a wind farm (and not individual turbine powers). For individual turbine power granularity, please use theWindFarmSCADAPower class.



## Configuration

### Required Parameters

- `component_type`: Must be `"PowerPlayback"`
- `scada_filename`: Path to the power data file (CSV, pickle, or feather format)
- `log_channels`: List of output channels to log (see [Logging Configuration](#logging-configuration) below)

See [timing](timing.md) for the time-related parameters (`dt`, `starttime_utc`, `endtime_utc`) that are set at the top level of the input YAML.

### Example YAML Configuration

```yaml
power_unit_1:
  component_type: PowerPlayback
  scada_filename: ../inputs/power_playback_input.ftr
  log_channels:
    - power
```

### Input File Format

The input file must contain the following columns:

- `time_utc`: Timestamps in UTC (ISO 8601 format or parseable datetime strings)
- `power`: Power output in kW

Supported file formats: `.csv`, `.p`, `.pkl` (pickle), `.f`, `.ftr` (feather).

The `time_utc` range in the input file must span at least the simulation's `starttime_utc` to `endtime_utc`. The data is interpolated onto the simulation's time grid at initialization.

#### Example CSV

```
time_utc,power
2020-01-01T00:00:00Z,0.0
2020-01-01T00:07:30Z,15000.0
2020-01-01T00:15:50Z,15000.0
```

## Outputs

At each simulation step, `PowerPlayback` writes the following to `h_dict`:

| Channel | Units | Description |
|---|---|---|
| `power` | kW | Power output at the current time step (interpolated from input file) |

## Logging Configuration

The `log_channels` parameter controls which outputs are written to the HDF5 output file. The `power` channel is always logged, even if not explicitly listed.

```yaml
log_channels:
  - power
```

## Notes

- `PowerPlayback` has `component_category = "generator"`, so its power contributes to `h_dict["plant"]["locally_generated_power"]`.
- There is no setpoint or control interface; the output power is read-only.
- The component is intended as a drop-in replacement when measured power data is available and no physics model is needed.
