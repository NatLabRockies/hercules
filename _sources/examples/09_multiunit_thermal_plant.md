# Example 09: Multi-unit Thermal Plant

## Description

Demonstrates a multi-unit thermal plant with three Open Cycle Gas Turbine (OCGT) units. Each unit has its own state machine and ramp behavior, but they share a common controller that issues power setpoints for all units simultaneously. The example illustrates how the plant responds to changes in setpoints while respecting constraints such as minimum up/down times, ramp rates, and minimum stable load of the individual units. The first two individual units are identical, but their commands and responses are tracked separately in the outputs. The third unit is also an Open Cycle Gas Turbine, but it has half the ramp rate of the first two units. It is given the same power set points as the second unit, demonstrating the effect of the ramp rate parameter. This example demonstrates how to both use the same unit definition for two units (OCGT1 & OCGT2), and how to define a unit with its own definition (OCGT3).

## Running

To run the example, execute the following command in the terminal:

```bash
python hercules_runscript.py
```

## Outputs

To plot the outputs, run:

```bash
python plot_outputs.py
```

The plot shows (for the all units separately):
- Power output over time (demonstrating ramp constraints and minimum stable load in response to setpoint changes for the individual units), as well as total plant power output
- Operating state transitions
- Fuel consumption tracking
- Heat rate variation with load
