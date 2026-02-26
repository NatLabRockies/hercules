# Battery

There are two battery models currently implemented in Hercules: `BatterySimple` and `BatteryLithiumIon`. 

## Sign Conventions

It is important to note that within the battery modules, the convention that positive power is charging the  
battery is followed for consistency with battery standards.  However, at the level of the `HybridPlant`
this is inverted, such that positive power implies power delivery (and thus the battery is discharging)
for consistency with other components.  This inversion applies to power_setpoint and also occurs within
`HybridPlant`.

### Parameters

Battery parameters are defined in the hercules input yaml file used to initialize `HerculesModel`. The YAML section key is a user-chosen `component_name` (e.g. `battery`, `battery_unit_1`); the examples below use `battery` as a conventional choice. See [Component Names, Types, and Categories](component_types.md) for details.

#### Required Parameters
- `component_type`: `"BatterySimple"` or `"BatteryLithiumIon"`
- `energy_capacity`: Energy capacity in kWh
- `charge_rate`: Maximum charge rate in kW
- `discharge_rate`: Maximum discharge rate in kW
- `max_SOC`: Maximum state of charge (between 0 and 1)
- `min_SOC`: Minimum state of charge (between 0 and 1)
- `initial_conditions`
  - `SOC`: Initial state of charge (between `min_SOC` and `max_SOC`)

#### Optional Parameters
- `allow_grid_power_consumption`: True or False (defaults to False)
- `roundtrip_efficiency`: Roundtrip efficiency (0-1, applies to BatterySimple only)
- `self_discharge_time_constant`: Self-discharge time constant in seconds (BatterySimple only)
- `track_usage`: Enable usage tracking for degradation modeling (BatterySimple only)
- `usage_calc_interval`: Interval for usage calculations in seconds (BatterySimple only)
- `usage_lifetime`: Battery lifetime in years for time-based degradation (BatterySimple only)
- `usage_cycles`: Number of cycles until replacement for cycle-based degradation (BatterySimple only)
- `log_channels`: List of output channels to log (see [Logging Configuration](battery-logging-configuration) below)


Once initialized, the battery is only interacted with using the `step` method.

### Inputs
Inputs are passed to `step()` as a dict named `h_dict`, which must have the following fields:

```python
h_dict = {
    "battery": {
        "power_setpoint": 1000  # Requested battery power in kW (positive=discharge, negative=charge)
    },
    "plant": {
        "locally_generated_power": 5000  # Available power for charging in kW
    }
}
```

### Outputs
Outputs are returned as a dict containing the following values:
- `power`: Actual battery power in kW 
- `reject`: Rejected power due to constraints in kW (positive when power cannot be absorbed, negative when required power unavailable)
- `soc`: Battery state of charge (0-1)
- `power_setpoint`: Requested power setpoint in kW

#### Additional Outputs (BatterySimple only when track_usage=True)
- `usage_in_time`: Time-based usage percentage
- `usage_in_cycles`: Cycle-based usage percentage  
- `total_cycles`: Total equivalent cycles completed

(battery-logging-configuration)=
### Logging Configuration

The `log_channels` parameter controls which outputs are written to the HDF5 output file. This is a list of channel names. The `power` channel is always logged, even if not explicitly specified.

**Available Channels:**
- `power`: Actual battery power output in kW (always logged)
- `soc`: State of charge (0-1)
- `power_setpoint`: Requested power setpoint in kW

**Example:**
```yaml
battery:
  component_type: BatterySimple
  energy_capacity: 100.0  # kWh
  charge_rate: 50.0  # kW
  discharge_rate: 50.0  # kW
  max_SOC: 0.9
  min_SOC: 0.1
  log_channels:
    - power
    - soc
    - power_setpoint
  initial_conditions:
    SOC: 0.5
```

If `log_channels` is not specified, only `power` will be logged.


## `BatterySimple`

`BatterySimple` is a basic energy storage model with the following features:

- **Energy Integration**: $E_t = \sum_{k=0}^t P_k \Delta t$, where $E_t$ is the energy stored and $P_t$ is the charging/discharging power at time $t$
- **Efficiency Losses**: Separate charge and discharge efficiencies (from roundtrip efficiency)
- **Self-Discharge**: Exponential energy loss with configurable time constant
- **Usage Tracking**: Optional rainflow cycle counting for degradation modeling
- **Constraints**: Both energy and power are constrained by upper and lower limits:

$\underline{E} \leq E \leq \overline{E}$

$\underline{P} \leq P \leq \overline{P}$

The model uses a state-space representation to handle self-discharge and efficiency losses in a unified framework.


## `BatteryLithiumIon`

`BatteryLithiumIon` models a detailed lithium-ion battery using an equivalent circuit model based on [1]. Key features include:

- **Equivalent Circuit Model**: RC branch representing diffusion transients
- **State-Dependent Parameters**: Open circuit voltage, resistance, and capacitance vary with SOC, SOH, and temperature
- **Cell-Level Modeling**: Individual cell behavior scaled to battery pack
- **Voltage-Current Relationship**: Iterative power control accounting for voltage variations
- **Physical Constraints**: Energy, power, and current limits at cell and pack level

**Battery Specifications:**
- Cathode Material: LiFePO4
- Anode Material: Graphite
- Nominal Cell Voltage: 3.3V
- Cell Capacity: 15.756 Ah

The main difference from `BatterySimple` is the inclusion of voltage dynamics, diffusion transients, and state-dependent equivalent circuit parameters that provide higher fidelity modeling of lithium-ion battery behavior.



### References

1. M.-K. Tran et al., “A comprehensive equivalent circuit model for lithium-ion batteries, incorporating the effects of state of health, state of charge, and temperature on model parameters,” Journal of Energy Storage, vol. 43, p. 103252, Nov. 2021, doi: 10.1016/j.est.2021.103252.
