# Nomenclature

This page defines how quantities are named in Hercules. It applies to `h_dict` keys,
input YAML keys, logged output channels, HDF5 datasets and Python attributes and
locals. **All new code must follow it.** If you add a name that is not covered here,
add it to the tables below in the same pull request.

The convention was agreed in
[issue #279](https://github.com/NatLabRockies/hercules/issues/279) and is shared
with Hycon and ENPAX.


## Power flow

```{mermaid}
flowchart LR
    HYCON["Hycon (controller)"]

    subgraph COMPONENTS["Components (AC at inverter / PCS output)"]
        WIND["wind_farm<br/>power, power_hypothetical<br/>turbine_powers, turbine_powers_hypothetical"]
        SOLAR["solar_farm<br/>power, power_hypothetical<br/>DC_power_hypothetical"]
        BATT["battery<br/>power, DC_power<br/>SOC"]
        THERM["thermal units<br/>power"]
        ELEC["electrolyzer<br/>power (negative)<br/>power_allocated"]
    end

    BUS["LV bus<br/>plant.power_bus<br/>plant.locally_generated_power"]
    LOSS["η = plant.efficiency_bus_to_poi<br/>(applied in both directions)"]
    POI["POI<br/>plant.power_export"]
    GRID["Grid"]

    HYCON -- "turbine_power_setpoints" --> WIND
    HYCON -- "power_setpoint" --> SOLAR
    HYCON -- "power_setpoint" --> BATT
    HYCON -- "power_setpoint(s)" --> THERM
    HYCON -- "power_setpoint" --> ELEC

    WIND --> BUS
    SOLAR --> BUS
    BATT <--> BUS
    THERM --> BUS
    ELEC <--> BUS
    BUS <--> LOSS
    LOSS <--> POI
    POI <--> GRID

    BUS -. "read back" .-> HYCON
    POI -. "read back" .-> HYCON
```

Hycon writes setpoints (solid arrows from Hycon). Hercules computes everything else
and Hycon reads it back (dashed arrows).

## Name grammar

```
[<subobject>_][DC_]<quantity>[_<qualifier>...][_<unit>]
```

The full logged name is `<component>.<name>`, e.g. `solar_farm.power_hypothetical`.

- **`<subobject>`**: an optional part of the component the quantity belongs to, e.g.
  `turbine_`, `rotor_`, `generator_`, `floris_`, `fuel_`.
- **`DC_`**: marks a DC quantity (see the AC/DC rule below).
- **`<quantity>`**: what is measured, e.g. `power`, `energy`, `capacity`, `SOC`,
  `efficiency`, `startup_time`, `wind_speed`.
- **`<qualifier>`**: refines the quantity and always comes after it, e.g. `_hypothetical`,
  `_setpoint`, `_max`, `_min`, `_rated`, `_bus`, `_export`, `_hot`.
- **`<unit>`**: only for non-default units (see below).

Examples: `power_charge_max`, `SOC_min`, `capacity_rated`, `DC_capacity_rated`,
`turbine_power_rated`, `startup_time_hot`, `up_time_min`, `rotor_speed_initial_rpm`.

## General rules

1. **AC by default.** Every power quantity is AC unless its name contains `DC`.
   - Solar: `power` is AC at the inverter output; `DC_power_hypothetical` is DC at the array.
   - Battery: `power` is AC at the PCS output; `DC_power` is DC at the battery
     terminals.
2. **`<component>.power` is the actual power** the component delivers to (or draws
   from) the LV bus, after curtailment and setpoint limits.
3. **`_hypothetical` marks uncurtailed power.** It is what the resource
   would produce with no curtailment, so `power <= power_hypothetical`. Currently only wind and
   solar report `_hypothetical` quantities; other components may add them later.
4. **`_setpoint` quantities belong to the controller.** Hercules reads them but never
   writes them. Setpoints are AC and use the same sign convention as `power`.
   Multi-unit components (`ThermalPlant`, `CombinedCyclePlant`) derive per-unit setpoints
   for their internal units; the controller-facing setpoint is left unchanged.
5. **DC is related to AC through the inverter/PCS efficiency.** For batteries,
   `DC_power` is the rate of change of stored energy and is what drives SOC.
6. **Sign convention** (see below): generator sign outside components.
7. **Plant level.** Hercules computes these each step; none are setpoints.
   - `plant.power_bus`: sum of all `component.power` on the LV bus, before losses.
   - `plant.locally_generated_power`: sum of `power` over `generator` components only.
     Storage and load components use it to avoid drawing from the grid.
   - `plant.efficiency_bus_to_poi` (η): constant electrical efficiency of a single pass
     between the LV bus and the point of interconnection (POI), applied in whichever
     direction power flows (not a round-trip efficiency). It lumps LV AC ohmic losses, the
     MV transformer, MV line losses, the HV transformer and the gen-tie. Optional
     input, default 1.0, must satisfy 0 < η ≤ 1.
   - `plant.power_export`: power at the POI, positive when exporting:

     $$
     P_{export} =
     \begin{cases}
     \eta \, P_{bus} & P_{bus} \ge 0 \\
     P_{bus} / \eta & P_{bus} < 0
     \end{cases}
     $$
8. **Controller-internal quantities are out of scope**, e.g. how much battery charging
   comes from solar versus the grid is tracked inside Hycon.

## Sign convention

Outside a component (`h_dict`, logged outputs, plant quantities and setpoints) Hercules
uses the **generator convention**: power delivered to the bus is positive, power drawn
from the bus is negative. A discharging battery is positive, a charging battery is
negative, and an electrolyzer is always negative or zero. This matches the
interconnection, SCADA and EMS standards used to describe grid assets, and lets all
`power` signals be summed directly.

Inside storage and load components the **consumer convention** is used: charging or
consumption is positive. This matches battery-cell standards and many simulation tools.
`HybridPlant` converts between the two:

- Before stepping a component, it passes the component a copy of its section with
  `power_setpoint` negated. The controller-owned value in `h_dict` is never modified.
- After the step, it negates the outputs listed in the component's
  `consumer_sign_outputs` class attribute.

Internal variables that use the consumer convention carry a `_charge` or `_consumed`
qualifier (e.g. `power_charge`, `power_consumed`) so the sign is visible in the name.
Unit tests that call a storage or load component's `step()` directly use the consumer
convention.

## Units in names

Default units carry no suffix: power in kW, energy in kWh, time in s, and SI units
for everything else (m/s, rad/s, kg, m³, J/m³). Any other unit must be explicit:
`_MW`, `_MWh`, `_kJ`, `_rpm`, `_years`, `_percent`, `_per_min`. Dimensionless
fractions in [0, 1] of another quantity end in `_fraction`. See [Units](units.md).

## Other conventions

- **Acronyms are uppercase**: `AC`, `DC`, `SOC`, `SOH`, `DNI`, `POA`, `AOI`, `GHI`,
  `DHI`, `HHV`, `H2`, `MFR`, `POI`.
- **Spell out `efficiency`** in names (`efficiency_bus_to_poi`, `efficiency_charge`);
  do not use `eta`. The symbol η may still be used in equations.
- **Arrays are plural**: `turbine_powers`, `turbine_power_setpoints`,
  `wind_speeds_background`, `power_setpoints`.
- **Counts** are `<thing>_count[_<qualifier>]`: `turbine_count`, `stack_count`,
  `start_count_hot`, `component_count`.
- **File paths** end in `_filename`: `floris_input_filename`, `turbine_filename`,
  `wind_input_filename`, `log_filename`, `output_filename`.

## Quantities by component

### Plant

| Name | Kind | Description |
|---|---|---|
| `plant.interconnect_limit` | input | POI limit in kW (not enforced by Hercules) |
| `plant.efficiency_bus_to_poi` | input | Bus-to-POI efficiency, default 1.0 |
| `plant.power_bus` | output | Sum of component `power` |
| `plant.locally_generated_power` | output | Sum of generator `power` |
| `plant.power_export` | output | Power at the POI |
| `component_count` | metadata | Number of components |

### Wind (`WindFarm`, `WindFarmSCADAPower`)

| Name | Kind | Description |
|---|---|---|
| `turbine_power_setpoints` | setpoint | Per-turbine power limits (`WindFarm` only) |
| `power`, `turbine_powers` | output | Actual farm and turbine power |
| `power_hypothetical`, `turbine_powers_hypothetical` | output | Uncurtailed farm and turbine power |
| `capacity_rated`, `turbine_power_rated`, `turbine_count` | metadata | Ratings |
| `wind_speed_mean_background`, `wind_speed_mean_withwakes`, `wind_direction_mean` | output | Mean inflow |
| `wind_speeds_background`, `wind_speeds_withwakes` | output | Per-turbine wind speeds |
| `floris_input_filename`, `wind_input_filename`, `turbine_filename`, `scada_filename` | input | Files |
| `floris_update_time` | input | FLORIS update period |

Turbine model file (`dof1_model` section): `rotor_inertia`, `rotor_speed_rated`,
`torque_rated`, `cq_table_filename`, `rotor_speed_filter_frequency`, `gearbox_ratio`,
`generator_efficiency`, `torque_rate_max`, `pitch_rate_max`, `rotor_speed_initial_rpm`.

`power_hypothetical` uses the same waked wind speeds as `power`, so wake changes caused by
derating are not reflected. For `WindFarmSCADAPower`, `power_hypothetical` equals `power`.

### Solar (`SolarPySAMPVWatts`)

| Name | Kind | Description |
|---|---|---|
| `power_setpoint` | setpoint | AC power limit |
| `power` | output | AC power after curtailment |
| `power_hypothetical` | output | AC power before curtailment (after inverter clipping) |
| `DC_power_hypothetical` | output | DC array power before the inverter |
| `capacity_rated`, `DC_capacity_rated` | metadata | AC rating (`system_capacity / dc_ac_ratio`) and DC rating |
| `DNI`, `POA`, `AOI` | output | Irradiance and angle of incidence |

### Battery (`BatteryDynamic`, `BatteryReservoir`, `BatteryLithiumIon`)

| Name | Kind | Description |
|---|---|---|
| `energy_capacity` | input | Deliverable energy |
| `power_charge_max`, `power_discharge_max` | input | Power limits (positive magnitudes) |
| `SOC_max`, `SOC_min` | input | SOC limits |
| `roundtrip_efficiency` | input | Roundtrip efficiency (`BatteryDynamic`, `BatteryReservoir`) |
| `time_constant_self_discharge` | input | Self-discharge time constant (`BatteryDynamic`, `BatteryReservoir`) |
| `power_setpoint` | setpoint | Discharge positive |
| `power` | output | AC power, discharge positive |
| `DC_power` | output | DC power at the terminals, discharge positive |
| `power_reject` | output | `power_setpoint - power` (`BatteryDynamic`, `BatteryLithiumIon`) |
| `SOC` | output | State of charge |

`BatteryReservoir` intentionally omits `power_reject`. `BatteryLithiumIon` has no PCS
model, so its `DC_power` equals `power`.

### Electrolyzer (`ElectrolyzerPlant`)

| Name | Kind | Description |
|---|---|---|
| `power_setpoint` | setpoint | Optional, negative (consumption); if absent all local power is used |
| `power` | output | Power drawn, negative |
| `power_allocated` | output | Power allocated before stack curtailment, negative |
| `H2_output`, `H2_MFR` | output | Hydrogen per step (kg) and mass flow rate (kg/s) |
| `stack_count_on`, `stacks_waiting` | output | Stack status |

### Thermal (`ThermalComponentBase` subclasses, `ThermalPlant`, `CombinedCyclePlant`)

| Name | Kind | Description |
|---|---|---|
| `capacity_rated` | input | Rated power |
| `load_stable_min_fraction` | input | Minimum stable load, fraction of `capacity_rated` |
| `ramp_rate_fraction_per_min`, `run_up_rate_fraction_per_min` | input | Ramp rates, fraction of `capacity_rated` per minute |
| `startup_time_hot`, `startup_time_warm`, `startup_time_cold` | input | Startup durations |
| `up_time_min`, `down_time_min` | input | Minimum on and off durations |
| `cooldown_time_warm`, `cooldown_time_cold` | input | Off time before a unit becomes warm or cold |
| `fuel_startup_fraction`, `fuel_shutdown_fraction` | input | Startup and shutdown fuel use |
| `HHV`, `fuel_density`, `efficiency_table` | input | Fuel and efficiency data |
| `power_setpoint` (`power_setpoints` for `ThermalPlant`) | setpoint | Requested power |
| `power`, `state`, `efficiency`, `fuel_volume_rate`, `fuel_mass_rate` | output | Operating outputs |
| `start_count`, `start_count_hot`, `start_count_warm`, `start_count_cold` | output | Start counts |

### Power playback (`PowerPlayback`)

`power` only. It has no setpoint and does not yet report a `_hypothetical` quantity.

## Exceptions

- **Keys passed to external packages** keep the package's naming: PySAM
  (`system_capacity`, `losses`, `tilt`, `lat`, `lon`, `elev`, `pysam_options`), FLORIS
  input files and the electrolyzer package configuration (e.g. `initial_power_kW`).
- **Input data file columns** keep their formats (`time_utc`, `ws_000`, `wd_mean`,
  `pow_000`, `power`).
- **Established names** kept for continuity: `plant.locally_generated_power`,
  `plant.interconnect_limit`, `energy_capacity`, `roundtrip_efficiency` (standard
  industry term), `initial_conditions.time_in_shutdown`,
  `allow_grid_power_consumption`, `time_utc` and `starttime_utc`/`endtime_utc`.
- **Physics symbols** in internal code (`V`, `I`, `R`, `C`, `OCV`, `SOH`, `Cp`, `Cq`,
  `rho`, `omega`) and wind `ws`/`wd` internals that mirror input file columns.

## Renamed names

Hercules v3 renamed the following. Using an old input key or log channel raises an
error that names the replacement.

| Old | New |
|---|---|
| `plant.power` (HDF5 `plant_power`) | `plant.power_bus` (HDF5 `plant_power_bus`) |
| `eta_bus_to_poi` (name used in issue #279) | `efficiency_bus_to_poi` |
| `power_hyp`, `DC_power_hyp`, `turbine_powers_hyp` (names used in issue #279) | `power_hypothetical`, `DC_power_hypothetical`, `turbine_powers_hypothetical` |
| `n_components` | `component_count` |
| `output_file` | `output_filename` |
| `logging.log_file`, `log_file_name` | `log_filename` |
| `external_data.external_data_file` | `external_data.external_data_filename` |
| `floris_input_file`, `turbine_file_name`, `cq_table_file` | `floris_input_filename`, `turbine_filename`, `cq_table_filename` |
| `floris_update_time_s` | `floris_update_time` |
| `capacity`, `rated_capacity` | `capacity_rated` (solar: old `capacity` is now `DC_capacity_rated`) |
| `rated_turbine_power`, `n_turbines` | `turbine_power_rated`, `turbine_count` |
| `rated_rotor_speed`, `rated_torque`, `initial_rpm` | `rotor_speed_rated`, `torque_rated`, `rotor_speed_initial_rpm` |
| `filterfreq_rotor_speed`, `gen_efficiency` | `rotor_speed_filter_frequency`, `generator_efficiency` |
| `max_pitch_rate`, `max_torque_rate` | `pitch_rate_max`, `torque_rate_max` |
| `ac_power_available`, `dc_power_available` | `power_hypothetical`, `DC_power_hypothetical` |
| `dni`, `poa`, `aoi` | `DNI`, `POA`, `AOI` |
| `charge_rate`, `discharge_rate` | `power_charge_max`, `power_discharge_max` |
| `max_SOC`, `min_SOC`, `soc` | `SOC_max`, `SOC_min`, `SOC` |
| `self_discharge_time_constant` | `time_constant_self_discharge` |
| `reject` | `power_reject` |
| `electrolyzer_signal` (positive) | `power_setpoint` (negative) |
| `power_input_kw` | `power_allocated` (negative) |
| `H2_mfr`, `stacks_on` | `H2_MFR`, `stack_count_on` |
| electrolyzer `initial_conditions.power_available_kw` | removed (unused) |
| `min_stable_load_fraction` | `load_stable_min_fraction` |
| `ramp_rate_fraction`, `run_up_rate_fraction` | `ramp_rate_fraction_per_min`, `run_up_rate_fraction_per_min` |
| `hot_startup_time`, `warm_startup_time`, `cold_startup_time` | `startup_time_hot`, `startup_time_warm`, `startup_time_cold` |
| `min_up_time`, `min_down_time` | `up_time_min`, `down_time_min` |
| `hot_to_warm_time`, `hot_to_cold_time` | `cooldown_time_warm`, `cooldown_time_cold` |
| `startup_fuel_fraction`, `shutdown_fuel_fraction` | `fuel_startup_fraction`, `fuel_shutdown_fraction` |
| `hhv` | `HHV` |
| `n_total_starts`, `n_hot_starts`, `n_warm_starts`, `n_cold_starts` | `start_count`, `start_count_hot`, `start_count_warm`, `start_count_cold` |
