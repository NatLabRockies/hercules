# Example 07: Open Cycle Gas Turbine (OCGT)

## Description

This example demonstrates a standalone open-cycle gas turbine (OCGT) simulation. The example showcases the turbine's state machine behavior including startup sequences, power ramping, minimum stable load constraints, and shutdown sequences.

For details on OCGT parameters and configuration, see {doc}`../open_cycle_gas_turbine`. For details on the underlying state machine and ramp behavior, see {doc}`../thermal_component_base`.

## Scenario

The simulation runs for 6 hours with 1-minute time steps. A controller commands the turbine through several operating phases. The table below shows both **control commands** (setpoint changes) and **state transitions** (responses to commands based on constraints).

### Timeline

| Time (min) | Event Type | Setpoint | State | Description |
|------------|------------|----------|-------|-------------|
| 0 | Initial | 0 | OFF (0) | Turbine starts off, `time_in_state` begins counting |
| 40 | Command | → 100 MW | OFF (0) | Setpoint changes to full power, but `min_down_time` (60 min) not yet satisfied—turbine remains off |
| 60 | State | 100 MW | → HOT STARTING (1) | `min_down_time` satisfied, turbine begins hot starting sequence |
| ~64 | State | 100 MW | HOT STARTING (1) | `hot_readying_time` (~4.2 min) complete, run-up ramp begins |
| ~68 | State | 100 MW | → ON (4) | Power reaches P_min (20 MW) after `hot_startup_time` (~8.2 min), turbine now operational |
| ~76 | Ramp | 100 MW | ON (4) | Power reaches 100 MW (ramped at 10 MW/min from P_min) |
| 120 | Command | → 50 MW | ON (4) | Setpoint reduced to 50% capacity |
| ~125 | Ramp | 50 MW | ON (4) | Power reaches 50 MW (ramped down at 10 MW/min) |
| 180 | Command | → 10 MW | ON (4) | Setpoint reduced to 10% (below P_min), power clamped to P_min |
| ~183 | Ramp | 10 MW | ON (4) | Power reaches P_min (20 MW), cannot go lower |
| 210 | Command | → 100 MW | ON (4) | Setpoint increased to full power |
| ~218 | Ramp | 100 MW | ON (4) | Power reaches 100 MW |
| 240 | Command + State | → 0 | → STOPPING (5) | Shutdown command; `min_up_time` satisfied (~172 min on), begins stopping sequence |
| ~250 | State | 0 | → OFF (0) | Power reaches 0 (ramped down at 10 MW/min), turbine off |
| 360 | End | 0 | OFF (0) | Simulation ends |

### Key Behaviors Demonstrated

- **Minimum down time**: The turbine cannot start until `min_down_time` (60 min) is satisfied, even though the command is issued at 40 min
- **Hot startup sequence**: After `min_down_time`, the turbine enters HOT STARTING, waits through `hot_readying_time`, then ramps to P_min using `run_up_rate`
- **Ramp rate constraints**: All power changes in ON state are limited by `ramp_rate` (10 MW/min)
- **Minimum stable load**: When commanded to 10 MW (below P_min = 20 MW), power is clamped to P_min
- **Minimum up time**: Shutdown is allowed immediately at 240 min because `min_up_time` (60 min) was satisfied long ago
- **Stopping sequence**: The turbine ramps down to zero at `ramp_rate` before transitioning to OFF

## Setup

No manual setup is required. The example uses only the OCGT component which requires no external data files.

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

The plot shows:
- Power output over time (demonstrating ramp constraints and minimum stable load)
- Operating state transitions
- Fuel consumption tracking
- Heat rate variation with load
