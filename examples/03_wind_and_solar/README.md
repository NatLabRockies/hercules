# Example 03: Wind and solar hybrid plant

## Description

In this setup, wind and solar are combined in a hybrid plant.  For demonstration, the plant has a fixed interconnect limit of 3000 kW, which is much below the combined capacity of the wind and solar farms.  A simple controller limits the solar power to keep the total power below the interconnect limit.

## Pre setup

1. Copy `wind_input.p` from the `example_case_folders/02_wind_farm_realistic_inflow/inputs/` folder to `inputs/`


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