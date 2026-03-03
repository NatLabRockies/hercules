# Example 08: Combined Cycle Gas Turbine (CCGT)

## Description

This example demonstrates a standalone combined-cycle gas turbine (CCGT) simulation. The example showcases the turbine's state machine behavior including startup sequences, power ramping, minimum stable load constraints, and shutdown sequences.

For details on CCGT parameters and configuration, see {doc}`../combined_cycle_gas_turbine`. For details on the underlying state machine and ramp behavior, see {doc}`../thermal_component_base`.

## Scenario

The simulation runs for 10 hours with 1-minute time steps. A controller commands the turbine through several operating phases. The table below shows both **control commands** (setpoint changes) and **state transitions** (responses to commands based on constraints).

### Timeline

| Time (min) | Event Type | Setpoint | State | Description |
|------------|------------|----------|-------|-------------|
| 0 | Initial | 100 MW | ON (4) | Turbine starts on at rated power, `time_in_state` begins counting |
| 10 | Command + State | → 0 | → STOPPING (5) | Shutdown command; `min_up_time` satisfied (initialized to be dispatchable), begins stopping sequence |
| ~45 | State | 0 | → OFF (0) | Power reaches 0 (ramped down at 3 MW/min), turbine off |
| 60 | Command | → 100 MW | OFF (0) | Setpoint changes to full power, but `min_down_time` (120 min) not yet satisfied—turbine remains off |
| ~160 | State | 100 MW | → HOT STARTING (1) | `min_down_time` satisfied, turbine begins hot starting sequence |
| ~225 | State | 100 MW | HOT STARTING (1) | `hot_readying_time` (~65 min) complete, run-up ramp begins |
| ~235 | State | 100 MW | → ON (4) | Power reaches P_min (40 MW) after `hot_startup_time` (~75 min), turbine now operational |
| ~260 | Ramp | 100 MW | ON (4) | Power reaches 100 MW (ramped at 3 MW/min from P_min) |
| 260 | Command | → 50 MW | ON (4) | Setpoint reduced to 50% capacity |
| ~276 | Ramp | 50 MW | ON (4) | Power reaches 50 MW (ramped down at 3 MW/min) |
| 360 | Command | → 10 MW | ON (4) | Setpoint reduced to 10% (below P_min), power clamped to P_min (40 MW) |
| ~365 | Ramp | 10 MW | ON (4) | Power reaches P_min (40 MW), cannot go lower |
| 480 | Command | → 100 MW | ON (4) | Setpoint increased to full power |
| ~500 | Ramp | 100 MW | ON (4) | Power reaches 100 MW |
| 540 | Command + State | → 0 | → STOPPING (5) | Shutdown command; `min_up_time` satisfied (~305 min on), begins stopping sequence |
| ~570 | State | 0 | → OFF (0) | Power reaches 0 (ramped down at 3 MW/min), turbine off |
| 600 | End | 0 | OFF (0) | Simulation ends |

### Key Behaviors Demonstrated

- **Minimum down time**: The turbine cannot start until `min_down_time` (120 min) is satisfied, even though the command is issued at 60 min
- **Hot startup sequence**: After `min_down_time`, the turbine enters HOT STARTING, waits through `hot_readying_time`, then ramps to P_min using `run_up_rate`
- **Ramp rate constraints**: All power changes in ON state are limited by `ramp_rate` (3 MW/min)
- **Minimum stable load**: When commanded to 10 MW (below P_min = 40 MW), power is clamped to P_min
- **Minimum up time**: Shutdown is allowed immediately at 570 min because `min_up_time` (240 min) was satisfied long ago
- **Stopping sequence**: The turbine ramps down to zero at `ramp_rate` before transitioning to OFF

## Setup

No manual setup is required. The example uses only the CCGT component which requires no external data files.

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
