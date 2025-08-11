# Hercules Input Files

Hercules input files are YAML configuration files that define simulation parameters and component configurations. These files are processed by the `load_hercules_input()` function in `utilities.py` to create the `h_dict` structure that drives the simulation.

## Overview

Input files use YAML format for readability and flexibility. The `Loader` class in `utilities.py` extends the standard YAML loader to support `!include` tags, allowing you to reference external files within your configuration.

## Structure

The input file structure mirrors the `h_dict` structure documented in the [h_dict page](h_dict.md). Key sections include:

- **Top level parameters**: `dt`, `starttime`, `endtime`
- **Plant configuration**: `interconnect_limit`
- **Hybrid plant configurations**: `wind_farm`, `solar_farm`, `battery`, `electrolyzer`
- **Optional settings**: `verbose`, `name`, `description`, `output_file`
- **Output configuration**: `output_format`, `output_time_step`

## Loading Process

The `load_hercules_input()` function in `utilities.py` performs comprehensive validation:

1. Loads the YAML file using the custom `Loader` class
2. Validates required keys (`dt`, `starttime`, `endtime`, `plant`)
3. Ensures `plant.interconnect_limit` is present and numeric
4. Validates component configurations and types
5. Sets defaults for optional parameters (e.g., `verbose: False`)

## Example

```yaml
# Input YAML for hercules

name: example_simulation
description: Wind and Solar Farm Simulation

dt: 1.0
starttime: 0.0
endtime: 950.0
verbose: False

plant:
  interconnect_limit: 30000  # kW

wind_farm:
  component_type: Wind_MesoToPower
  floris_input_file: inputs/floris_input.yaml
  wind_input_filename: inputs/wind_input.csv
  turbine_file_name: inputs/turbine_filter_model.yaml
  log_file_name: outputs/log_wind_sim.log

solar_farm:
  component_type: SolarPySAMPVWatts
  solar_input_filename: inputs/solar_input.csv
  lat: 39.7442
  lon: -105.1778
  elev: 1829
  target_system_capacity: 10000
  target_dc_ac_ratio: 1.33
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
  initial_conditions:
    SOC: 0.5

controller:
  # Controller configuration here

output_file: outputs/hercules_output.csv
```

## Output Configuration Options

New in v2.0, Hercules supports advanced output configuration options to optimize file size and write performance:

### output_format
Controls the output file format. Options are:
- `feather` (default): Fastest read/write, good compression, Python/R compatible
- `parquet`: Best compression, excellent for analytics, cross-platform
- `csv`: Most compatible, human readable, larger file size

### output_time_step  
Controls output downsampling frequency. Must be ≥ `dt`. Examples:
- If `dt: 1.0` and `output_time_step: 5.0`, saves every 5th simulation step
- If `dt: 0.1` and `output_time_step: 1.0`, saves every 10th simulation step
- Default: same as `dt` (no downsampling)



### Example with Output Configuration

```yaml
# Advanced output configuration example
dt: 1.0
starttime: 0.0  
endtime: 3600.0

# Output every 10 seconds in compact Parquet format
output_format: parquet
output_time_step: 10.0
output_file: outputs/my_simulation.parquet

plant:
  interconnect_limit: 5000

wind_farm:
  component_type: Wind_MesoToPower
  # ... other wind farm config

controller:
```

## Validation

The `load_hercules_input()` function performs strict validation on input files to catch configuration errors early. This includes checking for:

- Required keys at the top level
- Valid component types and configurations
- Numeric validation for timing and power parameters
- File existence checks for referenced input files
- Output configuration validation (format, time step)

Invalid configurations will raise descriptive `ValueError` exceptions to help with debugging. 