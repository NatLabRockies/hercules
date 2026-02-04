# Open Cycle Gas Turbine

The `OpenCycleGasTurbine` class models an open-cycle gas turbine (OCGT), also known as a peaker plant or simple-cycle gas turbine. It is a subclass of {doc}`ThermalComponentBase <thermal_component_base>` and inherits all state machine behavior, ramp constraints, and operational logic from the base class.

For details on the state machine, startup/shutdown behavior, and base parameters, see {doc}`thermal_component_base`.

## OCGT-Specific Parameters

In addition to the base class parameters, the OCGT model includes parameters for fuel consumption tracking:

| Parameter | Units | Default | Description |
|-----------|-------|---------|-------------|
| `part_load_factor` | dimensionless | 1.0 | Heat rate penalty at minimum load. Range: 1.0-2.0. A value of 1.0 means no penalty; higher values indicate decreased efficiency at part load |
| `heat_rate_at_rated_load` | kJ/kWh | 10000 | Fuel consumption rate at rated load |

## Default Parameter Values

The `OpenCycleGasTurbine` class provides default values for base class parameters based on References [1-3]. Only `rated_capacity` and `initial_conditions` are required in the YAML configuration.

| Parameter | Default Value | Source |
|-----------|---------------|--------|
| `min_stable_load_fraction` | 0.20 (20%) | [1], [2], [3] |
| `ramp_rate_fraction` | 0.10 (10%/min) | [1] |
| `run_up_rate_fraction` | Same as `ramp_rate_fraction` | — |
| `hot_startup_time` | 420 s (7 minutes) | [1] |
| `cold_startup_time` | 480 s (8 minutes) | [1] |
| `hot_cold_cutoff_time` | 28800 s (8 hours) | [1], [2], [3] |
| `min_up_time` | 7200 s (2 hours) |  [2], [3] |
| `min_down_time` | 7200 s (2 hours) | [2], [3] |

## OCGT-Specific Outputs

In addition to the base class outputs (`power`, `state_num`), the OCGT model provides:

| Output | Units | Description |
|--------|-------|-------------|
| `fuel_consumption` | kJ | Fuel consumed during the timestep |
| `heat_rate` | kJ/kWh | Current heat rate (varies with load) |

### Heat Rate Calculation

The heat rate varies with load fraction to model part-load efficiency degradation:

- At rated load: `heat_rate = heat_rate_at_rated_load`
- At minimum load: `heat_rate = heat_rate_at_rated_load × part_load_factor`
- Between: Linear interpolation

Fuel consumption is calculated as:

$$
\text{fuel\_consumption} = \text{power} \times \text{heat\_rate} \times \frac{\Delta t}{3600}
$$

Where $\Delta t$ is the timestep in seconds.

## YAML Configuration

### Minimal Configuration

Only required parameters (uses all defaults):

```yaml
open_cycle_gas_turbine:
  component_type: OpenCycleGasTurbine
  rated_capacity: 100000  # kW (100 MW)
  initial_conditions:
    power: 0
    state_num: 0  # 0 = off
```

### Full Configuration

All parameters explicitly specified:

```yaml
open_cycle_gas_turbine:
  component_type: OpenCycleGasTurbine
  rated_capacity: 100000  # kW (100 MW)
  min_stable_load_fraction: 0.2  # 20% minimum operating point
  ramp_rate_fraction: 0.1  # 10%/min ramp rate
  run_up_rate_fraction: 0.05  # 5%/min run up rate
  hot_startup_time: 490.0  # ~8 minutes
  cold_startup_time: 580.0  # ~10 minutes
  hot_cold_cutoff_time: 28800  # 8 hours
  min_up_time: 3600  # 1 hour
  min_down_time: 3600  # 1 hour
  part_load_factor: 1.25  # 25% heat rate penalty at min load
  heat_rate_at_rated_load: 10000  # kJ/kWh at rated load
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

## Logging Configuration

The `log_channels` parameter controls which outputs are written to the HDF5 output file.

**Available Channels:**
- `power`: Actual power output in kW (always logged)
- `state_num`: Operating state number (0-4)
- `fuel_consumption`: Fuel consumed per timestep in kJ
- `heat_rate`: Current heat rate in kJ/kWh
- `power_setpoint`: Requested power setpoint in kW

## References

1. Agora Energiewende (2017): "Flexibility in thermal power plants - With a focus on existing coal-fired power plants."

2. "Impact of Detailed Parameter Modeling of Open-Cycle Gas Turbines on Production Cost Simulation", NREL/CP-6A40-87554, National Renewable Energy Laboratory, 2024.

3. Deane, J.P., G. Drayton, and B.P. Ó Gallachóir. "The Impact of Sub-Hourly Modelling in Power Systems with Significant Levels of Renewable Generation." Applied Energy 113 (January 2014): 152–58. https://doi.org/10.1016/j.apenergy.2013.07.027.
