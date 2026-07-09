# Linear Generator

The `LinearGenerator` class models a Mainspring linear generator — a free-piston linear engine that burns fuel to produce electricity directly, without a rotating shaft. It is a subclass of {doc}`ThermalComponentBase <thermal_component_base>` and inherits all state machine behavior, ramp constraints, and operational logic from the base class.

Set `component_type: LinearGenerator` in the component's YAML section. The section key is a user-chosen `component_name` (e.g. `linear_generator`); see [Component Names, Types, and Categories](component_types.md) for details.

For details on the state machine, startup/shutdown behavior, and base parameters, see {doc}`thermal_component_base`.


## Default Linear Generator-Specific Parameter Values

The `LinearGenerator` class provides default values for all base class parameters. Only `rated_capacity` and `initial_conditions` are required in the YAML configuration. All defaults are defined in the class-level `DEFAULTS` dict.

| Parameter | Default Value | Source | Notes |
|-----------|---------------|--------|------|
| `min_stable_load_fraction` | 0.0 (0%) | — | Minimum stable load fraction of the generator |
| `ramp_rate_fraction` | 1.2 (120%/min) | [2] | Ramp rate fraction of the generator |
| `run_up_rate_fraction` | Same as `ramp_rate_fraction` | — | Run-up rate fraction of the generator |
| `hot_startup_time` | 90 s (1.5 minutes) | — | Time required for a hot start |
| `warm_startup_time` | 450 s (7.5 minutes) | — | Time required for a warm start |
| `cold_startup_time` | 900 s (15 minutes) | — | Time required for a cold start |
| `min_up_time` | 300 s (5 minutes) | — | Note below |
| `min_down_time` | 300 s (5 minutes) | — | Minimum down time of the generator |
| `hot_to_warm_time` | 2700 s (45 minutes) | — | Assumptions documented below |
| `hot_to_cold_time` | 10800 s (3 hours) | — | Assumptions documented below |
| `hhv` | 39050000 J/m³ (39.05 MJ/m³) | [3] | Higher heating value of the fuel |
| `fuel_density` | 0.768 kg/m³ | [3] | Density of the fuel |
| `efficiency_table` | 41.44% HHV peak, with roll-off at extremes (see below) | [1] | Efficiency of the generator, converted from LHV |

Notes:
- `min_up_time` is often determined by thermal and mechanical stress management considerations, as the generator may need to remain on for a minimum duration to avoid excessive wear from frequent cycling.
- `hot_to_warm_time` and `hot_to_cold_time` are estimated based on catalyst cooling characteristics; see the section below for details on how these values were derived.


### Estimating `hot_to_warm_time` and `hot_to_cold_time`

These two parameters can be interpreted as catalyst cooling thresholds, similar to the `\tau_{hot}` and `\tau_{warm}` transition times used in conventional unit commitment startup models:

- `hot_to_warm_time`: time offline after which a hot start can no longer be assumed
- `hot_to_cold_time`: time offline after which a cold start must be assumed

For the linear generator, a reasonable first estimate is based on how long the catalyst takes to cool below its light-off temperature, typically about 200-300 °C. A simple lumped thermal model treats the catalyst assembly as cooling approximately exponentially after shutdown:

$$
T(t) = T_{amb} + (T_{op} - T_{amb}) e^{-t/\tau}
$$

where `T_amb` is ambient temperature, `T_op` is the catalyst operating temperature, and `\tau` is the thermal time constant of the catalyst assembly, approximately equal to thermal mass divided by heat loss conductance.

Using rough screening values:

- catalyst operating temperature: 400-600 °C
- ambient temperature: about 20 °C
- catalyst light-off temperature: about 250 °C
- catalyst thermal time constant: about 30-60 minutes for a relatively small, modestly insulated substrate

For example, if the catalyst is at 500 °C when the unit shuts down and the hot-to-warm threshold is taken as 250 °C, then:

$$
250 = 20 + (500 - 20)e^{-t/\tau}
$$

which gives:

$$
\frac{230}{480} = e^{-t/\tau}, \qquad
t = \tau \ln\left(\frac{480}{230}\right) \approx 0.74\tau
$$

If `\tau = 45` minutes, this yields a hot-to-warm transition time of about 33 minutes after shutdown. The warm-to-cold transition, defined more conservatively as the catalyst approaching near-ambient conditions such as within 50 °C of ambient, would usually occur after several time constants, on the order of 2-4 hours.

This supports a reasonable first-guess range of:

| Transition | Estimated threshold |
|-----------|---------------------|
| Hot -> Warm | 30-60 minutes offline |
| Warm -> Cold | 2-4 hours offline |

These thresholds are much shorter than those of many conventional thermal generators because the catalyst assembly has much lower thermal mass. More accurate values would require vendor-specific information about catalyst substrate mass, heat capacity, insulation, and enclosure heat loss.

## Linear Generator Fuel Parameters

The `LinearGenerator` class currently uses default values for natural gas properties from [3]:

| Parameter | Units | Default | Description |
|-----------|-------|---------|-------------|
| `hhv` | J/m³ | 39050000 | Higher heating value of natural gas (39.05 MJ/m³) [3] |
| `fuel_density` | kg/m³ | 0.768 | Fuel density for mass calculations [3] |

Linear generators are also capable of mixed-fuel operation. To model a different fuel, simply override the `hhv` and `fuel_density` parameters in the YAML configuration; in this case the `efficiency_table` should also be updated to reflect the new fuel's combustion characteristics.
The `efficiency_table` parameter is **optional**. If not provided, the default HHV net plant efficiency from the Mainspring Energy Linear Generator datasheet [1] is used. All efficiency values are **HHV (Higher Heating Value) net plant efficiencies**. See {doc}`thermal_component_base` for details on the efficiency table format.

### Default Efficiency Table

The default HHV net plant efficiency table is sourced from the Mainspring Energy Linear Generator datasheet [1]:

| Power Fraction | HHV Net Efficiency |
|---------------|-------------------|
| 1.00 | 0.40 (40%) |
| 0.90 | 0.4144 (41.44%) |
| 0.30 | 0.4144 (41.44%) |
| 0.20 | 0.35 (35%) |

Mainspring reports a single peak efficiency value of 41.44% HHV, which is representative of most of the operating range. The table adds a modest drop-off at the extremes: a small reduction at high load (above ~90% of rated) reflecting thermal losses, and a larger reduction at low load (below ~30% of rated) reflecting fixed auxiliary and parasitic losses. The boundary values at 0.90 and 0.30 are chosen conservatively to preserve the reported peak efficiency across the broad mid-load range; the actual roll-off shape is uncertain without part-load test data, so users with site-specific measurements should override the `efficiency_table` accordingly.

## Linear Generator Outputs

The linear generator model provides the following outputs (inherited from base class):

| Output | Units | Description |
|--------|-------|-------------|
| `power` | kW | Actual power output |
| `state` | integer | Operating state number (0-7), corresponding to the `STATES` enum |
| `efficiency` | fraction (0-1) | Current HHV net plant efficiency |
| `fuel_volume_rate` | m³/s | Fuel volume flow rate |
| `fuel_mass_rate` | kg/s | Fuel mass flow rate (computed using `fuel_density` [3]) |


## YAML Configuration

### Minimal Configuration

Required parameters only (uses all defaults):

```yaml
linear_generator:
  component_type: LinearGenerator
  rated_capacity: 250  # kW
  initial_conditions:
    power: 0  # 0 kW means OFF; power > 0 means ON
```

### Full Configuration

All parameters explicitly specified:

```yaml
linear_generator:
  component_type: LinearGenerator
  rated_capacity: 250  # kW
  min_stable_load_fraction: 0.0
  ramp_rate_fraction: 1.2  # 120%/min
  run_up_rate_fraction: 1.2  # 120%/min
  hot_startup_time: 90.0  # 1.5 minutes
  warm_startup_time: 450.0  # 7.5 minutes
  cold_startup_time: 900.0  # 15 minutes
  min_up_time: 300  # 5 minutes
  min_down_time: 300  # 5 minutes
  hot_to_warm_time: 2700.0  # 45 minutes
  hot_to_cold_time: 10800.0  # 3 hours
  hhv: 39050000  # J/m³ for natural gas (39.05 MJ/m³) [3]
  fuel_density: 0.768  # kg/m³ for natural gas [3]
  efficiency_table:
    power_fraction:
      - 1.00
      - 0.90
      - 0.30
      - 0.20
    efficiency:  # HHV net plant efficiency from [1]; peak ±roll-off at extremes
      - 0.40
      - 0.4144
      - 0.4144
      - 0.35
  log_channels:
    - power
    - fuel_volume_rate
    - fuel_mass_rate
    - state
    - efficiency
    - power_setpoint
  initial_conditions:
    power: 250  # kW; power > 0 means ON
```

### Multi-Unit Configuration (via ThermalPlant)

Multiple linear generators can be combined using the `ThermalPlant` component:

```yaml
thermal_power_plant:
  component_type: ThermalPlant
  units: ["linear_generator_ms", "linear_generator_ms", "linear_generator_ms", "linear_generator_ms"]
  unit_names: ["lg_1", "lg_2", "lg_3", "lg_4"]

  linear_generator_ms:
    component_type: LinearGenerator
    rated_capacity: 250  # kW
    initial_conditions:
      power: 250  # Start ON at rated capacity
```

## Logging Configuration

The `log_channels` parameter controls which outputs are written to the HDF5 output file.

**Available Channels:**
- `power`: Actual power output in kW (always logged)
- `state`: Operating state number (0-7), corresponding to the `STATES` enum
- `fuel_volume_rate`: Fuel volume flow rate in m³/s
- `fuel_mass_rate`: Fuel mass flow rate in kg/s (computed using `fuel_density` [3])
- `efficiency`: Current HHV net plant efficiency (0-1)
- `power_setpoint`: Requested power setpoint in kW

## References

1. Mainspring Energy, "Linear Generator Datasheet," Rev. R30313.3, March 16, 2026.
   https://linear-power.files.svdcdn.com/production/Mainspring-Linear-Generator-Datasheet-R30313.3_2026-03-16-205457_psod.pdf

2. https://www.energy.ca.gov/sites/default/files/2024-05/CEC-500-2024-037.pdf

3. I. Staffell, "The Energy and Fuel Data Sheet," University of Birmingham, March 2011.
   https://claverton-energy.com/cms4/wp-content/uploads/2012/08/the_energy_and_fuel_data_sheet.pdf
