# Example 03: Wind and solar hybrid plant

## Description

In this setup, wind and solar are simulated together in a hybrid plant. A simple controller can be used to curtail the solar power to keep the total power below the interconnect limit.

## Setup

No manual setup is required. The example automatically generates the necessary input files (wind data, solar data, FLORIS configuration, and turbine model) in the centralized `examples/inputs/` folder when first run.

## Running

To run the example, execute the following command in the terminal:

```bash
python hercules_runscript.py
```

## Outputs

To plot the outputs, run the following command in the terminal:

```bash
python plot_outputs.py
```