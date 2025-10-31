# Hercules Input Files

Hercules input files are YAML configuration files that define simulation parameters and component configurations. These files are processed by the `load_hercules_input()` function in `utilities.py` to create the `h_dict` structure that drives the simulation.

## Overview

Input files use YAML format for readability and flexibility. The `Loader` class in `utilities.py` extends the standard YAML loader to support `!include` tags, allowing you to reference external files within your configuration.

## Structure

The input file structure mirrors the `h_dict` structure documented in the [h_dict page](h_dict.md). Key sections include:

- **Top level parameters**: `dt`, `starttime_utc`, `endtime_utc` (see [timing](timing.md) for details)
- **Plant configuration**: `interconnect_limit`
- **Hybrid plant configurations**: `wind_farm`, `solar_farm`, `battery`, `electrolyzer`
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

wind_farm:
  component_type: Wind_MesoToPower
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

solar_farm:
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

battery:
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
  component_type: Wind_MesoToPower
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
