# Examples Overview

Hercules includes several example cases that demonstrate different simulation configurations and capabilities. Each example is self-contained with its own input files, run scripts, and output plotting.

## Available Examples

### [00: Wind Farm Only](example_case_folders/00_wind_farm_only/)


### [01: Wind Farm DOF1 Model](example_case_folders/01_wind_farm_dof1_model/)


### [02: Wind Farm Realistic Inflow](example_case_folders/02_wind_farm_realistic_inflow/)


### [03: Wind and Solar](example_case_folders/03_wind_and_solar/)


### [04: Wind, Solar, and Storage](example_case_folders/04_wind_solar_storage/)


## Running Examples

Each example includes:
- `hercules_input.yaml`: Configuration file
- `hercules_runscript.py`: Main execution script
- `run_script.sh`: Convenient shell script wrapper
- `plot_outputs.py`: Output visualization script

To run any example:
```bash
cd example_case_folders/XX_example_name/
bash run_script.sh
```
