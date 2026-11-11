# Example 09: Linear Generator

## Description

This example demonstrates a standalone Mainspring linear generator simulation. It highlights three key characteristics that distinguish the linear generator from other thermal components:

1. **Fast ramp rate** (120%/min) — power changes are effectively instantaneous at 1-minute time steps
2. **No minimum stable load** — the generator can operate at any fraction of rated capacity, including very low loads, without shutting down
3. **Flat efficiency** — HHV net efficiency is constant at 41.44% regardless of load level

For details on linear generator parameters and configuration, see {doc}`../linear_generator`. For details on the underlying state machine and ramp behavior, see {doc}`../thermal_component_base`.

## Scenario

The simulation runs for 7 hours with 1-minute time steps on a 250 kW unit.

### Timeline

| Time (min) | Event Type | Setpoint | State | Description |
|------------|------------|----------|-------|-------------|
| 0 | Initial | 250 kW | ON (6) | Generator starts on at rated capacity; `time_in_state` pre-set to `up_time_min` |
| 10 | Command | → 0 | → STOPPING (7) | Shutdown command; `up_time_min` pre-satisfied, stopping begins immediately |
| ~10 | State | 0 | → OFF_HOT (4) | Power reaches 0 within one time step (ramp rate of 120%/min exceeds rated capacity), `down_time_min` begins counting |
| ~15 | State | 0 | OFF_HOT (4) | `down_time_min` (5 min) satisfied |
| 20 | Command | → 250 kW | → HOT_STARTING (5) | ON command issued; `down_time_min` already satisfied, hot start begins immediately |
| ~21–22 | State | — | HOT_STARTING (5) | Hot start in progress; `startup_time_hot` is 90 s, which spans 2 time steps at dt=60 s |
| ~22 | State | 250 kW | → ON (6) | `startup_time_hot` complete; power ramps to 250 kW within one time step |
| 90 | Command | → 125 kW | ON (6) | Setpoint reduced to 50%; power reaches 125 kW within one time step |
| 120 | Command | → 50 kW | ON (6) | Setpoint reduced to 20%; power reaches 50 kW — note no minimum stable load constraint |
| 180 | Command | → 0 | → STOPPING (7) | Shutdown command; `up_time_min` satisfied (~153 min on), stopping begins |
| ~180 | State | 0 | → OFF_HOT (4) | Power reaches 0 within one time step |
| ~225 | State | 0 | → OFF_WARM (2) | `cooldown_time_warm` (45 min) elapsed since shutdown; unit transitions from hot to warm |
| ~360 | State | 0 | → OFF_COLD (0) | `cooldown_time_cold` (3 hours) elapsed since shutdown; unit transitions from warm to cold |
| 420 | End | 0 | OFF_COLD (0) | Simulation ends |

### Key Behaviors Demonstrated

- **Fast ramp**: Load changes while ON complete within a single 1-minute time step — the ramp rate (120%/min) exceeds rated capacity, so any setpoint change is met immediately
- **Hot startup duration**: `startup_time_hot` is 90 s, which spans 2 timesteps at dt=60 s; power is not available until the startup sequence completes
- **No minimum stable load**: The generator operates at 20% (50 kW) without clamping or shutdown, unlike a gas turbine which typically has a 30–40% minimum
- **Flat efficiency**: Efficiency remains 41.44% at 100%, 50%, and 20% load — fuel consumption scales linearly with power output
- **Minimum down time**: After shutdown at t=10 min, `down_time_min` (5 min) is satisfied by t=15 min, so the ON command at t=20 min starts the hot start sequence immediately
- **Cooldown state transitions**: After the final shutdown at t=180 min, the unit progresses through OFF_HOT → OFF_WARM (at t≈225 min, after `cooldown_time_warm` of 45 min) → OFF_COLD (at t≈360 min, after `cooldown_time_cold` of 3 hours)

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
