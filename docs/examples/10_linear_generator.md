# Example 10: Linear Generator

## Description

This example demonstrates a standalone Mainspring linear generator simulation. It highlights three key characteristics that distinguish the linear generator from other thermal components:

1. **Fast ramp rate** (120%/min) — power changes are effectively instantaneous at 1-minute time steps
2. **No minimum stable load** — the generator can operate at any fraction of rated capacity, including very low loads, without shutting down
3. **Flat efficiency** — HHV net efficiency is constant at 41.44% regardless of load level

For details on linear generator parameters and configuration, see {doc}`../linear_generator`. For details on the underlying state machine and ramp behavior, see {doc}`../thermal_component_base`.

## Scenario

The simulation runs for 4 hours with 1-minute time steps on a 250 kW unit.

### Timeline

| Time (min) | Event Type | Setpoint | State | Description |
|------------|------------|----------|-------|-------------|
| 0 | Initial | 250 kW | ON (4) | Generator starts on at rated capacity; `time_in_state` pre-set to `min_up_time` |
| 10 | Command | → 0 | → STOPPING (5) | Shutdown command; `min_up_time` pre-satisfied, stopping begins immediately |
| ~10 | State | 0 | → OFF (0) | Power reaches 0 within one time step (fast ramp), `min_down_time` begins counting |
| ~15 | State | 0 | OFF (0) | `min_down_time` (5 min) satisfied |
| 20 | Command | → 250 kW | → HOT STARTING (1) | ON command issued; `min_down_time` already satisfied, hot start begins immediately |
| ~27 | State | 250 kW | → ON (4) | `hot_startup_time` (~7 min) complete; power reaches 250 kW within one time step |
| 90 | Command | → 125 kW | ON (4) | Setpoint reduced to 50%; power reaches 125 kW within one time step |
| 120 | Command | → 50 kW | ON (4) | Setpoint reduced to 20%; power reaches 50 kW — note no minimum stable load constraint |
| 180 | Command | → 0 | → STOPPING (5) | Shutdown command; `min_up_time` satisfied (~153 min on), stopping begins |
| ~180 | State | 0 | → OFF (0) | Power reaches 0 within one time step |
| 240 | End | 0 | OFF (0) | Simulation ends |

### Key Behaviors Demonstrated

- **Fast ramp**: All power transitions complete within a single 1-minute time step
- **No minimum stable load**: The generator operates at 20% (50 kW) without clamping or shutdown, unlike a gas turbine which typically has a 30–40% minimum
- **Flat efficiency**: Efficiency remains 41.44% at 100%, 50%, and 20% load — fuel consumption scales linearly with power output
- **Minimum down time**: After shutdown at t=10 min, `min_down_time` (5 min) is satisfied by t=15 min, so the ON command at t=20 min starts the hot start sequence immediately
- **Hot startup**: After `min_down_time`, the generator enters HOT STARTING and completes the startup sequence before returning to ON

## Setup

No manual setup is required. The example uses only the `LinearGenerator` component which requires no external data files.

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
- Power output and setpoint over time (demonstrating fast ramp and no minimum stable load)
- Operating state transitions
- Thermal efficiency over time (flat at 41.44% across all load levels)
- Fuel volume rate over time
