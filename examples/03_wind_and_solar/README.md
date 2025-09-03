# Example 03: Wind and solar hybrid plant

## Description

In this setup, wind and solar are combined in a hybrid plant.  For demonstration, the plant has a fixed interconnect limit of 3000 kW, which is much below the combined capacity of the wind and solar farms.  A simple controller limits the solar power to keep the total power below the interconnect limit.

## Setup

No manual setup is required. The example automatically generates the necessary input files (wind data, solar data, FLORIS configuration, and turbine model) in the centralized `examples/inputs/` folder when first run.

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