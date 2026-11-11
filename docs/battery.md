# Battery

There are three battery models currently implemented in Hercules: `BatteryDynamic`, `BatteryReservoir` and `BatteryLithiumIon`.

## Sign Conventions

Outside the battery component (`h_dict`, logged outputs and plant quantities) Hercules uses the
generator convention used by interconnection, SCADA and EMS standards: **discharging is positive and
charging is negative**. Inside the battery models the battery-cell convention is used: charging is
positive. `HybridPlant` passes each battery a negated copy of `power_setpoint` and negates the
outputs listed in the model's `consumer_sign_outputs` (`power`, `DC_power` and, where present,
`power_reject`). The controller-owned `power_setpoint` in `h_dict` is never modified. Unit tests
that call a battery's `step()` directly therefore use the charge-positive convention. See
[Nomenclature](nomenclature.md#sign-convention).

### Parameters

Battery parameters are defined in the hercules input yaml file used to initialize `HerculesModel`. The YAML section key is a user-chosen `component_name` (e.g. `battery`, `battery_unit_1`); the examples below use `battery` as a conventional choice. See [Component Names, Types, and Categories](component_types.md) for details.

#### Required Parameters
- `component_type`: `"BatteryDynamic"`, `"BatteryReservoir"` or `"BatteryLithiumIon"`
- `energy_capacity`: Deliverable energy capacity in kWh. This is the energy the battery can deliver at rated discharge power — i.e., a 4 MWh / 1 MW battery will discharge for exactly 4 hours regardless of roundtrip efficiency.
- `power_charge_max`: Maximum charge rate in kW
- `power_discharge_max`: Maximum discharge rate in kW
- `initial_conditions`
  - `SOC`: Initial state of charge (between `SOC_min` and `SOC_max`)

#### Optional Parameters
- `SOC_max`: Maximum state of charge (0-1, default 1.0). Values below 1.0 indicate a deviation from nameplate performance (e.g., degradation) and reduce the usable energy window.
- `SOC_min`: Minimum state of charge (0-1, default 0.0). Values above 0.0 indicate a deviation from nameplate performance (e.g., degradation) and reduce the usable energy window. This limits discharge only; self-discharge can take SOC below `SOC_min`.
- `allow_grid_power_consumption`: True or False (defaults to False)
- `roundtrip_efficiency`: Roundtrip efficiency (0-1, default 1.0), applied on charging (BatteryDynamic and BatteryReservoir)
- `time_constant_self_discharge`: Self-discharge time constant in seconds (default inf, BatteryDynamic and BatteryReservoir)
- `log_channels`: List of output channels to log (see [Logging Configuration](battery-logging-configuration) below)


Once initialized, the battery is only interacted with using the `step` method.

### Inputs
Inputs are read from `h_dict` in `step()`:

```python
h_dict = {
    "battery": {
        "power_setpoint": 1000  # Requested battery power in kW (positive=discharge, negative=charge)
    },
    "plant": {
        "locally_generated_power": 5000  # Available power for charging in kW
    },
}
```

### Outputs
Outputs (generator convention, discharge positive):
- `power`: AC battery power in kW
- `DC_power`: DC power at the battery terminals in kW, the rate of change of stored energy. For `BatteryDynamic` and `BatteryReservoir` it equals `power` when discharging and `roundtrip_efficiency * power` when charging. `BatteryLithiumIon` has no PCS model, so `DC_power` equals `power`.
- `SOC`: Battery state of charge (0-1)
- `power_setpoint`: Requested power setpoint in kW
- `power_reject`: `power_setpoint - power` in kW (BatteryDynamic and BatteryLithiumIon)

(battery-logging-configuration)=
### Logging Configuration

The `log_channels` parameter controls which outputs are written to the HDF5 output file. This is a list of channel names. The `power` channel is always logged, even if not explicitly specified.

**Available Channels:**
- `power`: AC battery power in kW (always logged)
- `DC_power`: DC battery power in kW
- `SOC`: State of charge (0-1)
- `power_setpoint`: Requested power setpoint in kW
- `power_reject`: Rejected power in kW (BatteryDynamic and BatteryLithiumIon)

**Example:**
```yaml
battery:
  component_type: BatteryDynamic
  energy_capacity: 10000  # kWh (deliverable energy at rated power)
  power_charge_max: 2500  # kW, represents a 2.5 MW, 4-hour battery
  power_discharge_max: 2500  # kW
  # SOC_max and SOC_min default to 1.0 and 0.0 respectively.
  # Set them only to model degradation or other nameplate deviations:
  # SOC_max: 0.9
  # SOC_min: 0.1
  log_channels:
    - power
    - SOC
    - power_setpoint
  initial_conditions:
    SOC: 0.5
```

If `log_channels` is not specified, only `power` will be logged.


## Roundtrip Efficiency Convention

`BatteryDynamic` and `BatteryReservoir` apply all roundtrip efficiency ($\eta_{RT}$) losses on charging, so the stored energy equals the energy deliverable at the terminals. This matches the convention used in NLR's ReEDS model. As a result:

- Full discharge time at `power_discharge_max` $P_d$: $E_{cap} / P_d$
- Full charge time at `power_charge_max` $P_c$: $E_{cap} / (\eta_{RT} P_c)$

Splitting the losses between charge and discharge (e.g., $\sqrt{\eta_{RT}}$ each, with a correspondingly larger internal capacity) produces identical power and SOC trajectories, but the internal SOC of a real battery management system may differ.


## `BatteryDynamic`

`BatteryDynamic` is a basic energy storage model with the following features:

- **State-Space Form**: The stored energy (kJ internally) is advanced with Euler integration of $\dot{E} = -E/\tau + P_{in}$, where $P_{in} = \eta_{RT} P$ when charging and $P_{in} = P$ when discharging
- **Self-Discharge**: Exponential energy loss with configurable time constant $\tau$
- **Constraints**: Energy and power are constrained by upper and lower limits, and the setpoint is clipped to the most restrictive limit. The clipped amount is reported as `power_reject`.

$\underline{E} \leq E \leq \overline{E}$

$\underline{P} \leq P \leq \overline{P}$

The energy limits constrain the commanded power: the battery will not discharge below $\underline{E}$ or charge above $\overline{E}$. Self-discharge can still take the energy below $\underline{E}$; the model never charges on its own to restore it.


## `BatteryReservoir`

`BatteryReservoir` is an energy-reservoir model with the same inputs and power/SOC behavior as `BatteryDynamic`, written in a minimal form. It tracks energy in kWh, applies self-discharge as an exact exponential decay, and outputs only `power`, `DC_power` and `SOC` (no `power_reject`).

**State update.** With charging power $P > 0$ in kW (battery sign convention), stored energy $E$ in kWh, and time step $\Delta t$ and self-discharge time constant $\tau$ both in seconds, each step:

$$
E_d = E_t\, e^{-\Delta t / \tau}, \qquad
E_{t+1} = E_d + \frac{\Delta t}{3600} \begin{cases} \eta_{RT} P & P > 0 \\ P & P \le 0 \end{cases}, \qquad
\mathrm{SOC} = E / E_{cap}
$$

**Constraints.** $P$ is the setpoint clipped to the most restrictive of the power limits ($-P_d \le P \le P_c$), the available power for charging (unless `allow_grid_power_consumption` is True), and the energy limits $\mathrm{SOC}_{min} E_{cap} \le E_{t+1} \le \mathrm{SOC}_{max} E_{cap}$. The energy limits only restrict the commanded power, so with $P = 0$ self-discharge can take SOC below $\mathrm{SOC}_{min}$; the model never charges on its own to restore it.

Without self-discharge, `BatteryReservoir` and `BatteryDynamic` produce identical power and SOC. With finite $\tau$ they differ slightly because `BatteryDynamic` uses Euler integration.


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

The main difference from `BatteryDynamic` is the inclusion of voltage dynamics, diffusion transients, and state-dependent equivalent circuit parameters that provide higher fidelity modeling of lithium-ion battery behavior.



### References

1. M.-K. Tran et al., “A comprehensive equivalent circuit model for lithium-ion batteries, incorporating the effects of state of health, state of charge, and temperature on model parameters,” Journal of Energy Storage, vol. 43, p. 103252, Nov. 2021, doi: 10.1016/j.est.2021.103252.
