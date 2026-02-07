# Thermal Component Base

The `ThermalComponentBase` class provides common functionality for thermal power plant components in Hercules. It serves as a base class for multiple thermal plant types including:

- Reciprocating internal combustion engines (RICE)
- Open-cycle gas turbines (OCGT)
- Combined-cycle gas turbines (CCGT) 
- Coal-fired power plants

The parameterized model is based primarily on [1], with additional parameters and naming conventions from [2] and [3]. Table 1 on page 48 of [1] provides many of the default values used in subclasses.

## State Machine

The thermal component operates as a state machine with six states:

```{mermaid}
stateDiagram-v2
    direction TB
    
    state "OFF (0)" as Off
    state "HOT STARTING (1)" as Hot
    state "WARM STARTING (2)" as Warm
    state "COLD STARTING (3)" as Cold
    state "ON (4)" as On
    state "STOPPING (5)" as Stop

    [*] --> Off
    
    Off --> Hot: start (hot)
    Off --> Warm: start (warm)
    Off --> Cold: start (cold)
    
    Hot --> Off: abort
    Hot --> On: P >= P_min
    
    Warm --> Off: abort
    Warm --> On: P >= P_min
    
    Cold --> Off: abort
    Cold --> On: P >= P_min
    
    On --> Stop: shutdown
    
    Stop --> Off: P = 0
```

### State Transitions

The decision between hot, warm, and cold starting is based on how long the unit has been off. The cutoff times are hardcoded based on reference [5]: less than 8 hours triggers a hot start, 8-48 hours triggers a warm start, and 48+ hours triggers a cold start.

| From State | To State | Diagram Label | Condition |
|------------|----------|---------------|-----------|
| OFF (0) | HOT STARTING (1) | start (hot) | `power_setpoint > 0` AND `time_in_state >= min_down_time` AND `time_in_state < 8 hours` |
| OFF (0) | WARM STARTING (2) | start (warm) | `power_setpoint > 0` AND `time_in_state >= min_down_time` AND `time_in_state >= 8 hours` AND `time_in_state < 48 hours` |
| OFF (0) | COLD STARTING (3) | start (cold) | `power_setpoint > 0` AND `time_in_state >= min_down_time` AND `time_in_state >= 48 hours` |
| HOT STARTING (1) | OFF (0) | abort | `power_setpoint <= 0` |
| HOT STARTING (1) | ON (4) | P >= P_min | `power_output >= P_min` (after `hot_startup_time`) |
| WARM STARTING (2) | OFF (0) | abort | `power_setpoint <= 0` |
| WARM STARTING (2) | ON (4) | P >= P_min | `power_output >= P_min` (after `warm_startup_time`) |
| COLD STARTING (3) | OFF (0) | abort | `power_setpoint <= 0` |
| COLD STARTING (3) | ON (4) | P >= P_min | `power_output >= P_min` (after `cold_startup_time`) |
| ON (4) | STOPPING (5) | shutdown | `power_setpoint <= 0` AND `time_in_state >= min_up_time` |
| STOPPING (5) | OFF (0) | P = 0 | `power_output <= 0` |

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
| `warm_startup_time` | s | Time to reach P_min from off (warm start). Includes both readying time and ramping time |
| `cold_startup_time` | s | Time to reach P_min from off (cold start). Includes both readying time and ramping time |
| `min_up_time` | s | Minimum time unit must remain on before shutdown is allowed |
| `min_down_time` | s | Minimum time unit must remain off before restart is allowed |
| `initial_conditions.power` | kW | Initial power output |
| `initial_conditions.state_num` | integer | Initial state (0=off, 1=hot starting, 2=warm starting, 3=cold starting, 4=on, 5=stopping) |
| `hhv` | J/m³ | Higher heating value of fuel |
| `fuel_density` | kg/m³ | Fuel density for mass calculations |
| `efficiency_table` | dict | Dictionary containing `power_fraction` and `efficiency` arrays (see below) |

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
| `warm_readying_time` | `warm_startup_time - ramp_time` | Preparation time before warm start ramp begins |
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
2. If `min_down_time` is satisfied, the unit transitions to HOT STARTING, WARM STARTING, or COLD STARTING (depending on how long it has been off: <8h = hot, 8-48h = warm, >48h = cold)
3. The unit remains at zero power during the readying time (`hot_readying_time`, `warm_readying_time`, or `cold_readying_time`)
4. After readying, the unit ramps up to P_min using `run_up_rate`
5. Once P_min is reached, the unit transitions to ON state

During normal operation (ON state):
- Power changes are constrained by `ramp_rate`
- Power output is constrained between P_min and P_max
- The unit must remain on for at least `min_up_time` before shutdown is allowed

During shutdown:
- The unit ramps down to zero using `ramp_rate`
- Once power reaches zero, the unit transitions to OFF

## Efficiency and Fuel Consumption

The base class calculates thermal efficiency and fuel consumption based on the `efficiency_table` and `hhv` parameters.

### Efficiency Table Format

The `efficiency_table` parameter specifies how efficiency varies with load:

```yaml
efficiency_table:
  power_fraction:  # fraction of rated_capacity (0-1)
    - 1.0
    - 0.75
    - 0.50
    - 0.25
  efficiency:  # fraction (0-1), e.g., 0.425 = 42.5%
    - 0.425
    - 0.40
    - 0.35
    - 0.275
```

Both arrays must have the same length and values must be in the range [0, 1]. The arrays are sorted by `power_fraction` internally.

### Efficiency Interpolation

Efficiency is calculated by linear interpolation from the table based on current power fraction (`power_output / rated_capacity`). Values outside the table range are clamped to the nearest endpoint.

### Fuel Consumption Calculation

Fuel consumption is calculated as:

$$
\text{fuel\_volume} = \frac{\text{power} \times \Delta t}{\text{efficiency} \times \text{hhv}}
$$

Where:
- `power` is in W (converted from kW internally)
- `Δt` is the timestep in seconds
- `efficiency` is the interpolated efficiency (0-1)
- `hhv` is the higher heating value in J/m³
- Result is fuel volume in m³/timestep

The fuel mass is then computed from the volume using the fuel density:

$$
\text{fuel\_mass} = \text{fuel\_volume} \times \text{fuel\_density}
$$

Where:
- `fuel_volume` is in m³
- `fuel_density` is in kg/m³
- Result is fuel mass in kg/timestep

## Outputs

The base class outputs are returned in `h_dict`:

| Output | Units | Description |
|--------|-------|-------------|
| `power` | kW | Actual power output |
| `state_num` | integer | Current operating state (0-5) |
| `efficiency` | fraction (0-1) | Current thermal efficiency |
| `fuel_consumption` | m³ | Fuel consumed this timestep |
| `fuel_consumption_kg` | kg | Fuel consumed this timestep (computed from volume using `fuel_density`) |

## References

1. Agora Energiewende (2017): "Flexibility in thermal power plants - With a focus on existing coal-fired power plants."

2. "Impact of Detailed Parameter Modeling of Open-Cycle Gas Turbines on Production Cost Simulation", NREL/CP-6A40-87554, National Renewable Energy Laboratory, 2024.

3. Deane, J.P., G. Drayton, and B.P. Ó Gallachóir. "The Impact of Sub-Hourly Modelling in Power Systems with Significant Levels of Renewable Generation." Applied Energy 113 (January 2014): 152–58. https://doi.org/10.1016/j.apenergy.2013.07.027.

4. IRENA (2019), Innovation landscape brief: Flexibility in conventional power plants, International Renewable Energy Agency, Abu Dhabi.

5. M. Oakes, M. Turner, "Cost and Performance Baseline for Fossil Energy Plants, Volume 5: Natural Gas Electricity Generating Units for Flexible Operation," National Energy Technology Laboratory, Pittsburgh, May 5, 2023.

6. I. Staffell, "The Energy and Fuel Data Sheet," University of Birmingham, March 2011. https://claverton-energy.com/cms4/wp-content/uploads/2012/08/the_energy_and_fuel_data_sheet.pdf
