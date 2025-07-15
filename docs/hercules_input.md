# Hercules Input Files

Hercules input files are YAML configuration files that define simulation parameters and component configurations. These files are processed by the `load_hercules_input()` function in `utilities.py` to create the `h_dict` structure that drives the simulation.

## Overview

Input files use YAML format for readability and flexibility. The `Loader` class in `utilities.py` extends the standard YAML loader to support `!include` tags, allowing you to reference external files within your configuration.

## Structure

The input file structure mirrors the `h_dict` structure documented in the [h_dict page](h_dict.md). Key sections include:

- **Top level parameters**: `dt`, `starttime`, `endtime`
- **Plant configuration**: `interconnect_limit`
- **Pysims configurations**: `wind_farm`, `solar_farm`, `battery`, `electrolyzer`
- **Optional settings**: `verbose`, `name`, `description`, `output_file`

## Loading Process

The `load_hercules_input()` function in `utilities.py` performs comprehensive validation:

1. Loads the YAML file using the custom `Loader` class
2. Validates required keys (`dt`, `starttime`, `endtime`, `plant`)
3. Ensures `plant.interconnect_limit` is present and numeric
4. Validates py_sim configurations and types
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
  py_sim_type: WindSimLongTerm
  floris_input_file: inputs/floris_input.yaml
  wind_input_filename: inputs/wind_input.csv
  turbine_file_name: inputs/turbine_filter_model.yaml
  log_file_name: outputs/log_wind_sim.log

solar_farm:
  py_sim_type: SolarPySAM
  pysam_model: pvwatts
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

controller:
  # Controller configuration here

output_file: outputs/hercules_output.csv
``` 