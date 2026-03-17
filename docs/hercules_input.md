# Hercules Input Files

Hercules input files are YAML configuration files that define simulation parameters and component configurations. These files are processed by the `load_hercules_input()` function in `utilities.py` to create the `h_dict` structure that drives the simulation.

## Overview

Input files use YAML format for readability and flexibility. The `Loader` class in `utilities.py` extends the standard YAML loader to support `!include` tags, allowing you to reference external files within your configuration.

## Structure

The input file structure mirrors the `h_dict` structure documented in the [h_dict page](h_dict.md). Key sections include:

- **Top level parameters**: `dt`, `starttime_utc`, `endtime_utc` (see [timing](timing.md) for details)
- **Plant configuration**: `interconnect_limit`
- **Plant component sections**: any number of user-named sections, each containing a `component_type` key that identifies the component class to use (see [Component Names, Types, and Categories](component_types.md))
- **External data**: `external_data` for external time series data (e.g., LMP prices, weather forecasts)
- **Optional settings**: `verbose`, `name`, `description`, `output_file`


## Loading Process

The `load_hercules_input()` function in `utilities.py` performs comprehensive validation:

1. Loads the YAML file using the custom `Loader` class
2. Validates required keys (`dt`, `starttime_utc`, `endtime_utc`, `plant`)
3. Parses and validates UTC datetime strings for `starttime_utc` and `endtime_utc`
4. Computes derived values: `starttime` (always 0.0) and `endtime` (duration in seconds)
5. Ensures `plant.interconnect_limit` is present and numeric
6. Validates component configurations and types
7. Sets defaults for optional parameters (e.g., `verbose: False`)

## Example

```yaml
# Input YAML for hercules

name: example_simulation
description: Wind and Solar Farm Simulation

dt: 1.0
starttime_utc: "2020-01-01T00:00:00Z"  # Simulation start in UTC
endtime_utc: "2020-01-01T00:15:50Z"    # Simulation end (15 min 50 sec later)
verbose: False

plant:
  interconnect_limit: 30000  # kW

wind_farm:  # User-chosen component_name; component_type determines the class
  component_type: WindFarm
  wake_method: dynamic
  floris_input_file: inputs/floris_input.yaml
  wind_input_filename: inputs/wind_input.csv
  turbine_file_name: inputs/turbine_filter_model.yaml
  log_file_name: outputs/log_wind_sim.log
  log_channels:
    - power
    - wind_speed_mean_background
    - wind_speed_mean_withwakes
    - wind_direction_mean
  floris_update_time_s: 30.0

solar_farm:  # User-chosen component_name
  component_type: SolarPySAMPVWatts
  solar_input_filename: inputs/solar_input.csv
  lat: 39.7442
  lon: -105.1778
  elev: 1829
  system_capacity: 10000  # kW (10 MW)
  tilt: 0  # degrees
  log_channels:
    - power
    - dni
    - poa
    - aoi
  initial_conditions:
    power: 2000  # kW
    dni: 1000
    poa: 1000

battery:  # User-chosen component_name
  component_type: BatterySimple
  energy_capacity: 100.0  # MWh
  charge_rate: 50.0  # MW
  discharge_rate: 50.0  # MW
  max_SOC: 0.95
  min_SOC: 0.05
  log_channels:
    - power
    - soc
    - power_setpoint
  initial_conditions:
    SOC: 0.5

controller:
  # Controller configuration here

output_file: outputs/hercules_output.h5
log_every_n: 1
```

## External Data Configuration

Hercules supports loading external time series data from CSV files (e.g., electricity prices, weather forecasts, or other external signals). This data becomes available to controllers through `h_dict["external_signals"]`.

### New Format (Preferred)

```yaml
external_data:
  external_data_file: path/to/data.csv
  log_channels:
    - lmp_rt
    - wind_forecast
```

**Key features:**
- `external_data_file`: Path to CSV file with `time_utc` column and data columns
- `log_channels`: Optional list of channels to log to HDF5 output
  - If **omitted**: all channels are logged (default behavior)
  - If **empty list** (`log_channels: []`): no channels are logged
  - If **non-empty list**: only listed channels are written to HDF5
  - **Important**: All channels are always available to the controller via `h_dict["external_signals"]`, regardless of `log_channels`

### Old Format (Deprecated)

```yaml
external_data_file: path/to/data.csv  # Logs all channels, shows deprecation warning
```

The old format is still supported for backward compatibility but will show a deprecation warning. It automatically logs all external data channels to the output file.

### External Data File Format

The CSV file must contain:
- A `time_utc` column with UTC timestamps in ISO 8601 format
- One or more data columns with external signals. Note that the names of the other columns are arbitrary; any column names will be carried forward and interpolated. However, the values must be floats. Additionally, some controllers and plotting utilities that work on external signals may require specific column names like `lmp_rt`, `lmp_da`, `wind_forecast`, etc.

Example `lmp_data.csv`:
```csv
time_utc,lmp_rt,lmp_da,wind_forecast
2024-06-24T16:59:08Z,25.5,20.0,12.3
2024-06-24T17:04:08Z,26.1,20.0,12.5
2024-06-24T17:09:08Z,27.3,20.0,12.8
...
```

Hercules automatically interpolates external data to match the simulation time step.

### Usage in Controllers

All external data channels are accessible in the controller through `h_dict["external_signals"]`:

```python
class MyController:
    def step(self, h_dict):
        # Access external signals (all channels available)
        lmp_rt = h_dict["external_signals"]["lmp_rt"]
        lmp_da = h_dict["external_signals"]["lmp_da"]
        wind_forecast = h_dict["external_signals"]["wind_forecast"]
        
        # Use signals for control logic
        if lmp_rt < 15:
            h_dict["battery"]["power_setpoint"] = -10000  # charge
        elif lmp_rt > 35:
            h_dict["battery"]["power_setpoint"] = 10000  # discharge
        else:
            h_dict["battery"]["power_setpoint"] = 0
        
        return h_dict
```

Even if `log_channels` only specifies `["lmp_rt"]`, the controller can still access all channels. The `log_channels` setting only controls what gets written to the HDF5 output file.

### Selective Logging Examples

**Example 1: Log all channels (default)**
```yaml
external_data:
  external_data_file: data.csv
  # log_channels not specified → logs all channels
```

**Example 2: Log specific channels**
```yaml
external_data:
  external_data_file: data.csv
  log_channels:
    - lmp_rt
    - wind_forecast
  # Only logs lmp_rt and wind_forecast (but all channels available to controller)
```

**Example 3: Log no channels**
```yaml
external_data:
  external_data_file: data.csv
  log_channels: []  # Empty list → logs nothing (but all channels available to controller)
```

This is useful when you want external data available for control decisions but don't need it saved in the output file.

## Output Configuration Options

Hercules supports several output configuration options to optimize file size and write performance:

### log_every_n
Controls how often simulation data is logged to the output file:
- Default: 1 (log every simulation step)
- Example: `log_every_n: 60` logs data every 60 simulation steps
- This reduces output file size and improves performance for long simulations

### output_file
Specifies the output file path. Hercules automatically ensures the file has a `.h5` extension for HDF5 format.

### output_use_compression
Controls HDF5 compression (default: True). Disable for faster writes if storage space is not a concern.

### output_buffer_size
Controls the memory buffer size for writing data (default: 50000 rows). Larger buffers improve performance but use more memory.

### Example with Output Configuration

```yaml
# Advanced output configuration example
dt: 1.0
starttime_utc: "2020-06-15T12:00:00Z"
endtime_utc: "2020-06-15T13:00:00Z"  # 1 hour simulation

# Log every 60 seconds (1 minute) to reduce file size
log_every_n: 60
output_file: outputs/my_simulation.h5
output_use_compression: true
output_buffer_size: 10000

plant:
  interconnect_limit: 5000

wind_farm:
  component_type: WindFarm
  wake_method: dynamic
  floris_input_file: inputs/floris_input.yaml
  wind_input_filename: inputs/wind_input.csv
  turbine_file_name: inputs/turbine_filter_model.yaml
  log_channels:
    - power
    - wind_speed_mean_background
    - wind_speed_mean_withwakes
    - wind_direction_mean
  floris_update_time_s: 30.0

controller:
```

## Validation

The `load_hercules_input()` function performs strict validation on input files to catch configuration errors early. This includes checking for:

- Required keys at the top level (`dt`, `starttime_utc`, `endtime_utc`, `plant`)
- Valid UTC datetime strings (ISO 8601 format) for `starttime_utc` and `endtime_utc`
  - Accepts: strings ending with "Z" (explicit UTC) or naive strings (no timezone)
  - Rejects: strings with timezone offsets (e.g., `+05:00`, `-08:00`) since the field must be UTC
- Logical time ordering (`endtime_utc` must be after `starttime_utc`)
- Valid component types and configurations
- Numeric validation for timing and power parameters
- File existence checks for referenced input files
- Output configuration validation (`log_every_n` must be a positive integer)
- Component-specific validation (e.g., `log_channels` must be a list of valid channel names)

Invalid configurations will raise descriptive `ValueError` exceptions to help with debugging.
