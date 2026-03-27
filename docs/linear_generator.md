# Linear Generator

The `LinearGenerator` class models a Mainspring linear generator — a free-piston linear engine that burns fuel to produce electricity directly, without a rotating shaft. It is a subclass of {doc}`ThermalComponentBase <thermal_component_base>` and inherits all state machine behavior, ramp constraints, and operational logic from the base class.

Set `component_type: LinearGenerator` in the component's YAML section. The section key is a user-chosen `component_name` (e.g. `linear_generator`); see [Component Names, Types, and Categories](component_types.md) for details.

For details on the state machine, startup/shutdown behavior, and base parameters, see {doc}`thermal_component_base`.


## Default Linear Generator-Specific Parameter Values

The `LinearGenerator` class provides default values for all base class parameters. Only `rated_capacity` and `initial_conditions` are required in the YAML configuration. All defaults are defined in the class-level `DEFAULTS` dict.

| Parameter | Default Value | Source |
|-----------|---------------|--------|
| `min_stable_load_fraction` | 0.0 (0%) | — |
| `ramp_rate_fraction` | 1.2 (120%/min) | [2] |
| `run_up_rate_fraction` | Same as `ramp_rate_fraction` | — |
| `hot_startup_time` | 420 s (7 minutes) | — |
| `warm_startup_time` | 480 s (8 minutes) | — |
| `cold_startup_time` | 480 s (8 minutes) | — |
| `min_up_time` | 300 s (5 minutes) | — |
| `min_down_time` | 300 s (5 minutes) | — |
| `hhv` | 39050000 J/m³ (39.05 MJ/m³) | [3] |
| `fuel_density` | 0.768 kg/m³ | [3] |
| `efficiency_table` | Flat 41.44% HHV efficiency (see below) | [1] |

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
| 1.00 | 0.4144 (41.44%) |
| 0.00 | 0.4144 (41.44%) |

The flat efficiency curve reflects the near-constant efficiency characteristic of the linear generator across its operating range.

## Linear Generator Outputs

The linear generator model provides the following outputs (inherited from base class):

| Output | Units | Description |
|--------|-------|-------------|
| `power` | kW | Actual power output |
| `state` | integer | Operating state number (0-5), corresponding to the `STATES` enum |
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
  hot_startup_time: 420.0  # 7 minutes
  warm_startup_time: 480.0  # 8 minutes
  cold_startup_time: 480.0  # 8 minutes
  min_up_time: 300  # 5 minutes
  min_down_time: 300  # 5 minutes
  hhv: 39050000  # J/m³ for natural gas (39.05 MJ/m³) [3]
  fuel_density: 0.768  # kg/m³ for natural gas [3]
  efficiency_table:
    power_fraction:
      - 1.0
      - 0.0
    efficiency:  # HHV net plant efficiency from [1]
      - 0.4144
      - 0.4144
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
- `state`: Operating state number (0-5), corresponding to the `STATES` enum
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
