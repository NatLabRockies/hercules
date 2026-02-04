# Example 06: Wind and hydrogen hybrid plant

## Description

Example of a wind and hydrogen hybrid plant where power that the wind farm produces goes directly to hydrogen electrolysis. The hydrogen output is then controlled by controlling the wind farm power to follow a hydrogen production reference signal.

## Setup

No manual setup is required. The example automatically generates the necessary input files (wind data, FLORIS configuration, and turbine model) in the centralized `examples/inputs/` folder when first run.

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
