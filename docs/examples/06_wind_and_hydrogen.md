# Example 06: Wind and Hydrogen

## Description

This example demonstrates a wind and hydrogen hybrid plant where power that the wind farm produces goes directly to hydrogen electrolysis. This configuration is useful for understanding how renewable energy can be directly converted to hydrogen for energy storage or industrial applications.

## Key Features

- Wind farm power generation
- Electrolyzer plant for hydrogen production
- Direct power flow from wind to electrolyzer
- Hydrogen production tracking

## Setup

No manual setup is required. The example automatically generates the necessary input files (wind data, FLORIS configuration, and turbine model) in the centralized `examples/inputs/` folder when first run.

## Running the Example

To run the example, execute the following command in the terminal:

```bash
cd examples/06_wind_and_hydrogen/
python hercules_runscript.py
```

## Visualizing Outputs

To plot the outputs, run the following command:

```bash
python plot_outputs.py
```

## Expected Results

The simulation will produce outputs showing:
- Wind farm power generation over time
- Hydrogen production rates
- Electrolyzer stack status
- Power consumption by the electrolyzer

## Configuration

The example uses:
- Wind farm with FLORIS wake modeling
- Electrolyzer plant with multiple stacks
- Hydrogen reference signal for electrolyzer control (from `inputs/hydrogen_ref_signal.csv`)

