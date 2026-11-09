# Battery

There are three battery models currently implemented in Hercules: `BatterySimple`, `BatteryReservoir` and `BatteryLithiumIon`.

## Sign Conventions

It is important to note that within the battery modules, the convention that positive power is charging the
battery is followed for consistency with battery standards.  However, at the level of the `HybridPlant`
this is inverted, such that positive power implies power delivery (and thus the battery is discharging)
for consistency with other components.  This inversion applies to power_setpoint and also occurs within
`HybridPlant`.

### Parameters

Battery parameters are defined in the hercules input yaml file used to initialize `HerculesModel`. The YAML section key is a user-chosen `component_name` (e.g. `battery`, `battery_unit_1`); the examples below use `battery` as a conventional choice. See [Component Names, Types, and Categories](component_types.md) for details.

#### Required Parameters
- `component_type`: `"BatterySimple"`, `"BatteryReservoir"` or `"BatteryLithiumIon"`
- `energy_capacity`: Deliverable energy capacity in kWh. This is the energy the battery can deliver at rated discharge power — i.e., a 4 MWh / 1 MW battery will discharge for exactly 4 hours regardless of roundtrip efficiency.
- `charge_rate`: Maximum charge rate in kW
- `discharge_rate`: Maximum discharge rate in kW
- `initial_conditions`
  - `SOC`: Initial state of charge (between `min_SOC` and `max_SOC`)

#### Optional Parameters
- `max_SOC`: Maximum state of charge (0-1, default 1.0). Values below 1.0 indicate a deviation from nameplate performance (e.g., degradation) and reduce the usable energy window.
- `min_SOC`: Minimum state of charge (0-1, default 0.0). Values above 0.0 indicate a deviation from nameplate performance (e.g., degradation) and reduce the usable energy window.
- `allow_grid_power_consumption`: True or False (defaults to False)
- `roundtrip_efficiency`: Roundtrip efficiency (0-1, default 1.0), applied on charging (BatterySimple and BatteryReservoir)
- `self_discharge_time_constant`: Self-discharge time constant in seconds (default inf, BatterySimple and BatteryReservoir)
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
- `soc`: Battery state of charge (0-1)
- `power_setpoint`: Requested power setpoint in kW
- `reject`: Rejected power due to constraints in kW (BatterySimple and BatteryLithiumIon; positive when power cannot be absorbed, negative when required power unavailable)

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
  energy_capacity: 10000  # kWh (deliverable energy at rated power)
  charge_rate: 2500  # kW, represents a 2.5 MW, 4-hour battery
  discharge_rate: 2500  # kW
  # max_SOC and min_SOC default to 1.0 and 0.0 respectively.
  # Set them only to model degradation or other nameplate deviations:
  # max_SOC: 0.9
  # min_SOC: 0.1
  log_channels:
    - power
    - soc
    - power_setpoint
  initial_conditions:
    SOC: 0.5
```

If `log_channels` is not specified, only `power` will be logged.


## Roundtrip Efficiency Convention

`BatterySimple` and `BatteryReservoir` apply all roundtrip efficiency ($\eta_{RT}$) losses on charging, so the stored energy equals the energy deliverable at the terminals. This matches the convention used in NLR's ReEDS model. As a result:

- Full discharge time at `discharge_rate` $P_d$: $E_{cap} / P_d$
- Full charge time at `charge_rate` $P_c$: $E_{cap} / (\eta_{RT} P_c)$

Splitting the losses between charge and discharge (e.g., $\sqrt{\eta_{RT}}$ each, with a correspondingly larger internal capacity) produces identical power and SOC trajectories, but the internal SOC of a real battery management system may differ.


## `BatterySimple`

`BatterySimple` is a basic energy storage model with the following features:

- **State-Space Form**: The stored energy (kJ internally) is advanced with Euler integration of $\dot{E} = -E/\tau + P_{in}$, where $P_{in} = \eta_{RT} P$ when charging and $P_{in} = P$ when discharging
- **Self-Discharge**: Exponential energy loss with configurable time constant $\tau$
- **Constraints**: Energy and power are constrained by upper and lower limits, and the setpoint is clipped to the most restrictive limit. The clipped amount is reported as `reject`.

$\underline{E} \leq E \leq \overline{E}$

$\underline{P} \leq P \leq \overline{P}$


## `BatteryReservoir`

`BatteryReservoir` is an energy-reservoir model with the same inputs and power/SOC behavior as `BatterySimple`, written in a minimal form. It tracks energy in kWh, applies self-discharge as an exact exponential decay, and outputs only `power` and `soc`.

**State update.** With charging power $P > 0$ (battery sign convention), time step $\Delta t$ in hours and self-discharge time constant $\tau$, each step:

$$
E_d = E_t\, e^{-\Delta t / \tau}, \qquad
E_{t+1} = E_d + \begin{cases} \eta_{RT} P \Delta t & P > 0 \\ P \Delta t & P \le 0 \end{cases}, \qquad
\mathrm{SOC} = E / E_{cap}
$$

**Constraints.** $P$ is the setpoint clipped to the most restrictive of the power limits ($-P_d \le P \le P_c$), the available power for charging (unless `allow_grid_power_consumption` is True), and the energy limits $\mathrm{SOC}_{min} E_{cap} \le E_{t+1} \le \mathrm{SOC}_{max} E_{cap}$.

Without self-discharge, `BatteryReservoir` and `BatterySimple` produce identical power and SOC. With finite $\tau$ they differ slightly because `BatterySimple` uses Euler integration.


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
