# Battery

There are two battery models currently implemented in Hercules: `SimpleBattery` and `LIB`. Both interact with Hercules through a simple wrapper class: `Battery`.

### Parameters

Battery parameters are defined in the hercules input yaml file used to initialize `emulator`.

- `py_sim_type`: `"SimpleBattery"` or `"LIB"`
- `energy_capacity`: [kWh]
- `charge_rate`: [kW]
- `max_SOC`: between 0 and 1
- `min_SOC`: between 0 and 1
- `allow_grid_power_consumption`: True or False (defaults to True)
- `initial_conditions`
  - `SOC`: between `min_SOC` and `max_SOC`


Once initialized, the battery is only interacted with using the `step` method.

### Inputs
Inputs are passed to `step()` as a dict named `inputs`, which must have the following fields:

```
{py_sims:{inputs:{battery_signal: ____,
                 locally_generated_power: ____
                 }}}
```

### Outputs
Outputs are returned as a dict containing the following values
- `power` The charging/discharging power of the battery
- `reject` The amount of charging/discharging requested of the battery that it could not fulfill. Can be positive or negative.
- `soc` The battery state of charge


## `SimpleBattery`

`SimpleBattery` is defined by $E_t = \sum_{k=0}^t P_k \Delta t$, where $E_t$ is the energy stored and $P_t$ is the charging/discharging power at time $t$. Both $E$ and $P$ are constrained by upper and lower limits.

$\underline{E} \leq E \leq \overline{E}$

$\underline{P} \leq P \leq \overline{P}$


## `LIB`

`LIB` models a lithium ion battery based on the lithium ion cell model presented in [1.]. The main difference between `LIB` and `SimpleBattery` is that `LIB` includes diffusion transients and losses both of which are modeled as an equivalent circuit model following the approach in [1.].



### References

1. M.-K. Tran et al., “A comprehensive equivalent circuit model for lithium-ion batteries, incorporating the effects of state of health, state of charge, and temperature on model parameters,” Journal of Energy Storage, vol. 43, p. 103252, Nov. 2021, doi: 10.1016/j.est.2021.103252.
