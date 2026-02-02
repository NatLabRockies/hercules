# Combustion Turbine

The `CombustionTurbineSimple` model represents a natural gas combustion turbine (peaker plant) with state management, ramp rate constraints, minimum stable load, and fuel consumption tracking.

## State Machine

The combustion turbine operates as a state machine with four states:

| State Number | State Name | Description |
|--------------|------------|-------------|
| 0 | `off` | Turbine is off, no power output |
| 1 | `starting` | Turbine is ramping up to minimum stable load |
| 2 | `on` | Turbine is operating normally |
| 3 | `stopping` | Turbine is ramping down to shutdown |

### State Transitions

- **OFF → STARTING**: When `power_setpoint > 0` and `min_down_time` is satisfied
- **STARTING → ON**: When startup power reaches minimum stable load (`P_min`)
- **STARTING → OFF**: If `power_setpoint <= 0` during startup (abort)
- **ON → STOPPING**: When `power_setpoint <= 0` and `min_up_time` is satisfied
- **STOPPING → OFF**: When shutdown power reaches 0

## Parameters

Combustion turbine parameters are defined in the Hercules input YAML file.

### Required Parameters

- `component_type`: Must be `"CombustionTurbineSimple"`
- `rated_capacity`: Maximum power output in kW
- `min_stable_load_fraction`: Minimum operating point as fraction (0-1)
- `heat_rate`: Fuel consumption rate at rated load in kJ/kWh
- `ramp_rate_up`: Maximum rate of power increase in kW/s
- `ramp_rate_down`: Maximum rate of power decrease in kW/s
- `initial_conditions`:
  - `power`: Initial power output in kW
  - `state_num`: Initial state (0=off, 1=starting, 2=on, 3=stopping)

### Optional Parameters

- `startup_time`: Time to reach minimum stable load from off in seconds (default: 3600.0)
- `shutdown_time`: Time to shut down in seconds (default: 3600.0)
- `min_up_time`: Minimum time unit must remain on in seconds (default: 3600.0)
- `min_down_time`: Minimum time unit must remain off in seconds (default: 3600.0)
- `part_load_factor`: Heat rate penalty at minimum load (default: 1.0, range: 1.0-2.0)
- `log_channels`: List of output channels to log (see [Logging Configuration](#logging-configuration) below)

## Outputs

Outputs are returned in `h_dict` with the following values:

- `power`: Actual power output in kW
- `state_num`: Current operating state (0=off, 1=starting, 2=on, 3=stopping)
- `fuel_consumption`: Fuel consumed this timestep in kJ
- `heat_rate`: Current heat rate in kJ/kWh (varies with part-load efficiency)

## Logging Configuration

The `log_channels` parameter controls which outputs are written to the HDF5 output file.

**Available Channels:**
- `power`: Actual power output in kW (always logged)
- `state_num`: Operating state number
- `fuel_consumption`: Fuel consumed per timestep in kJ
- `heat_rate`: Current heat rate in kJ/kWh
- `power_setpoint`: Requested power setpoint in kW

**Example:**
```yaml
combustion_turbine:
  component_type: CombustionTurbineSimple
  rated_capacity: 100000  # kW (100 MW)
  min_stable_load_fraction: 0.2  # 20% minimum operating point
  heat_rate: 10000  # kJ/kWh at rated load
  ramp_rate_up: 500  # kW/s
  ramp_rate_down: 500  # kW/s
  log_channels:
    - power
    - fuel_consumption
    - state_num
    - heat_rate
    - power_setpoint
  initial_conditions:
    power: 0
    state_num: 0  # 0 = off
```

## Operational Constraints

The model enforces several operational constraints:

1. **Power Limits**: Output is constrained between `P_min` (minimum stable load) and `P_max` (rated capacity) when on
2. **Ramp Rate Limits**: Power changes are limited by `ramp_rate_up` and `ramp_rate_down`
3. **Minimum Up/Down Times**: The turbine must remain in on/off states for specified minimum durations
4. **Startup/Shutdown Ramps**: Linear ramps during state transitions

## References

1. "Impact of Detailed Parameter Modeling of Open-Cycle Gas Turbines on Production Cost Simulation", NREL/CP-6A40-87554, National Renewable Energy Laboratory, 2024.
