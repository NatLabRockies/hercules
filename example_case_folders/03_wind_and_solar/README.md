# Example 03: Wind and solar hybrid plant

## Description

...

## Pre setup

1. Manually add `wind_resource_rex` folder to `example_case_folders/02_wind_farm_realistic_inflow/inputs/` folder
2. Generate the wind resource input file (`wind_input.p`) by running `example_case_folders/02_wind_farm_realistic_inflow/00_prepare_simulation.ipynb`
3. Generate the solar resource input file (`solar_input.p`) by running `example_case_folders/03_wind_and_solar/resample_solar_history.ipynb`

Note: If you will be running PySAM's Detailed PV Model instead of the PVWatts model, you will also need a `.json` file defining the system info.

## Running

To run the example, execute the following command in the terminal:

```bash
python hercules_runscript.py
```
## Outputs

To plot the outputs run the following command in the terminal:

```bash
python plot_outputs.py
```