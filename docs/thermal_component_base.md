# Thermal Component Base

The `ThermalComponentBase` class provides common functionality for thermal power plant components in Hercules. It serves as a base class for multiple thermal plant types including:

- Open-cycle gas turbines (OCGT)
- Combined-cycle gas turbines (CCGT) 
- Coal-fired power plants

The parameterized model is based primarily on [1], with additional parameters and naming conventions from [2] and [3]. Table 1 on page 48 of [1] provides many of the default values used in subclasses.

## State Machine

The thermal component operates as a state machine with five states:

```{mermaid}
stateDiagram-v2
    direction TB
    
    state "OFF (0)" as Off
    state "HOT STARTING (1)" as Hot
    state "COLD STARTING (2)" as Cold
    state "ON (3)" as On
    state "STOPPING (4)" as Stop

    [*] --> Off
    
    Off --> Hot: start (hot)
    Off --> Cold: start (cold)
    
    Hot --> Off: abort
    Hot --> On: P >= P_min
    
    Cold --> Off: abort
    Cold --> On: P >= P_min
    
    On --> Stop: shutdown
    
    Stop --> Off: P = 0
```

### State Transitions

| From State | To State | Diagram Label | Condition |
|------------|----------|---------------|-----------|
| OFF (0) | HOT STARTING (1) | start (hot) | `power_setpoint > 0` AND `time_in_state >= min_down_time` AND `time_in_state < hot_cold_cutoff_time` |
| OFF (0) | COLD STARTING (2) | start (cold) | `power_setpoint > 0` AND `time_in_state >= min_down_time` AND `time_in_state >= hot_cold_cutoff_time` |
| HOT STARTING (1) | OFF (0) | abort | `power_setpoint <= 0` |
| HOT STARTING (1) | ON (3) | P >= P_min | `power_output >= P_min` (after `hot_startup_time`) |
| COLD STARTING (2) | OFF (0) | abort | `power_setpoint <= 0` |
| COLD STARTING (2) | ON (3) | P >= P_min | `power_output >= P_min` (after `cold_startup_time`) |
| ON (3) | STOPPING (4) | shutdown | `power_setpoint <= 0` AND `time_in_state >= min_up_time` |
| STOPPING (4) | OFF (0) | P = 0 | `power_output <= 0` |

## Parameters

All parameters below are defined in the Hercules input YAML file. The base class does **not** provide default values—subclasses (such as `OpenCycleGasTurbine`) supply defaults based on References [1-3].

### Required Parameters

| Parameter | Units | Description |
|-----------|-------|-------------|
| `rated_capacity` | kW | Maximum power output (P_max) |
| `min_stable_load_fraction` | fraction (0-1) | Minimum operating point as fraction of rated capacity |
| `ramp_rate_fraction` | fraction/min | Maximum rate of power change during normal operation, as fraction of rated capacity per minute |
| `run_up_rate_fraction` | fraction/min | Maximum rate of power increase during startup ramp, as fraction of rated capacity per minute |
| `hot_startup_time` | s | Time to reach P_min from off (hot start). Includes both readying time and ramping time |
| `cold_startup_time` | s | Time to reach P_min from off (cold start). Includes both readying time and ramping time |
| `hot_cold_cutoff_time` | s | Time in off state after which a cold start is required instead of hot start |
| `min_up_time` | s | Minimum time unit must remain on before shutdown is allowed |
| `min_down_time` | s | Minimum time unit must remain off before restart is allowed |
| `initial_conditions.power` | kW | Initial power output |
| `initial_conditions.state_num` | integer | Initial state (0=off, 1=hot starting, 2=cold starting, 3=on, 4=stopping) |

### Derived Parameters

The following parameters are computed from the input parameters:

| Parameter | Formula | Description |
|-----------|---------|-------------|
| `P_max` | `rated_capacity` | Maximum power output |
| `P_min` | `min_stable_load_fraction × rated_capacity` | Minimum stable power output |
| `ramp_rate` | `ramp_rate_fraction × rated_capacity / 60` | Ramp rate in kW/s |
| `run_up_rate` | `run_up_rate_fraction × rated_capacity / 60` | Run-up rate in kW/s |
| `ramp_time` | `P_min / run_up_rate` | Time to ramp from 0 to P_min |
| `hot_readying_time` | `hot_startup_time - ramp_time` | Preparation time before hot start ramp begins |
| `cold_readying_time` | `cold_startup_time - ramp_time` | Preparation time before cold start ramp begins |

## Startup and Ramp Behavior

The following diagram illustrates the startup sequence and ramp behavior, showing how the input and derived parameters relate to each other:

```{image} _static/thermal_startup_ramp.svg
:alt: Thermal component startup and ramp behavior
:width: 700px
:align: center
```

During startup:
1. The unit receives a positive `power_setpoint` while in the OFF state
2. If `min_down_time` is satisfied, the unit transitions to HOT STARTING or COLD STARTING (depending on how long it has been off)
3. The unit remains at zero power during the readying time (`hot_readying_time` or `cold_readying_time`)
4. After readying, the unit ramps up to P_min using `run_up_rate`
5. Once P_min is reached, the unit transitions to ON state

During normal operation (ON state):
- Power changes are constrained by `ramp_rate`
- Power output is constrained between P_min and P_max
- The unit must remain on for at least `min_up_time` before shutdown is allowed

During shutdown:
- The unit ramps down to zero using `ramp_rate`
- Once power reaches zero, the unit transitions to OFF

## Outputs

The base class outputs are returned in `h_dict`:

| Output | Units | Description |
|--------|-------|-------------|
| `power` | kW | Actual power output |
| `state_num` | integer | Current operating state (0-4) |

Subclasses may add additional outputs (e.g., fuel consumption for gas turbines).

## References

1. Agora Energiewende (2017): "Flexibility in thermal power plants - With a focus on existing coal-fired power plants."

2. "Impact of Detailed Parameter Modeling of Open-Cycle Gas Turbines on Production Cost Simulation", NREL/CP-6A40-87554, National Renewable Energy Laboratory, 2024.

3. Deane, J.P., G. Drayton, and B.P. Ó Gallachóir. "The Impact of Sub-Hourly Modelling in Power Systems with Significant Levels of Renewable Generation." Applied Energy 113 (January 2014): 152–58. https://doi.org/10.1016/j.apenergy.2013.07.027.
