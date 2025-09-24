# Hercules Input Files

Hercules input files are YAML configuration files that define simulation parameters and component configurations. These files are processed by the `load_hercules_input()` function in `utilities.py` to create the `h_dict` structure that drives the simulation.

## Overview

Input files use YAML format for readability and flexibility. The `Loader` class in `utilities.py` extends the standard YAML loader to support `!include` tags, allowing you to reference external files within your configuration.

## Structure

The input file structure mirrors the `h_dict` structure documented in the [h_dict page](h_dict.md). Key sections include:

- **Top level parameters**: `dt`, `starttime`, `endtime` (see [timing](timing.md) for details)
- **Plant configuration**: `interconnect_limit`
- **Hybrid plant configurations**: `wind_farm`, `solar_farm`, `battery`, `electrolyzer`
- **Optional settings**: `verbose`, `name`, `description`, `output_file`


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
  logging_option: all
  floris_update_time_s: 30.0

solar_farm:
  component_type: SolarPySAMPVWatts
  solar_input_filename: inputs/solar_input.csv
  lat: 39.7442
  lon: -105.1778
  elev: 1829
  system_capacity: 10000  # kW (10 MW)
  tilt: 0  # degrees
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
starttime: 0.0  
endtime: 3600.0

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
  logging_option: all
  floris_update_time_s: 30.0

controller:
```

## Validation

The `load_hercules_input()` function performs strict validation on input files to catch configuration errors early. This includes checking for:

- Required keys at the top level (`dt`, `starttime`, `endtime`, `plant`)
- Valid component types and configurations
- Numeric validation for timing and power parameters
- File existence checks for referenced input files
- Output configuration validation (`log_every_n` must be a positive integer)
- Component-specific validation (e.g., wind farm `logging_option` must be "base", "turb_subset", or "all")

Invalid configurations will raise descriptive `ValueError` exceptions to help with debugging. 