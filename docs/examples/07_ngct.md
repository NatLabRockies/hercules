# Example 07: Natural Gas Combustion Turbine (NGCT)

## Description

This example demonstrates a standalone natural gas combustion turbine (peaker plant) simulation. The example showcases the turbine's state machine behavior including startup sequences, power ramping, minimum stable load constraints, and shutdown sequences.

## Scenario

The simulation runs for 6 hours with 1-minute time steps. A controller commands the turbine through several operating phases:

| Time (minutes) | Command | Description |
|----------------|---------|-------------|
| 0-70 | Off | Turbine remains off |
| 70 | Start | Command to 100% rated capacity |
| 70-120 | Full power | Operating at rated capacity |
| 120-180 | Reduce to 50% | Operating at 50% rated capacity |
| 180-210 | Reduce to 10% | Command below minimum stable load (clamped to 20%) |
| 210-240 | Full power | Operating at rated capacity |
| 240 | Shutdown | Command to turn off |
| 240-360 | Off | Turbine shuts down and remains off |

This scenario demonstrates several key behaviors:
- **Startup ramp**: The turbine takes time to reach minimum stable load after being commanded on
- **Minimum stable load**: When commanded to 10% (below the 20% minimum), the turbine clamps to minimum stable load
- **Ramp rate constraints**: Power changes are limited by the configured ramp rates
- **Shutdown sequence**: The turbine ramps down to zero over the shutdown time

## Setup

No manual setup is required. The example uses only the combustion turbine component which requires no external data files.

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
