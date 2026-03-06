# Hard Coal Steam Turbine

The `HardCoalSteamTurbine` (HCST) class models a hard coal power production plant using steam turbines. This class is a subclass of {doc}`ThermalComponentBase <thermal_component_base>` and inherits all state machine behavior, ramp constraints, and operational logic from the base class.

Set `component_type: HardCoalSteamTurbine` in the component's YAML section. The section key is a user-chosen `component_name` (e.g. `hard_coal_steam_turbine`); see [Component Names, Types, and Categories](component_types.md) for details.

For details on the state machine, startup/shutdown behavior, and base parameters, see {doc}`thermal_component_base`.

## HCST-Specific Parameters

The HCST class provides default values for bituminous coal properties from [4]:

| Parameter | Units | Default | Description |
|-----------|-------|---------|-------------|
| `hhv` | J/m³ | 29310000000 | Higher heating value of bituminous coal (29.31 MJ/kg) [4] |
| `fuel_density` | kg/m³ | 1000 | Fuel density for mass calculations |

The `efficiency_table` parameter is **optional**. If not provided, default values based on approximate readings from the [2] are used. All efficiency values are **HHV (Higher Heating Value) net plant efficiencies**. See {doc}`thermal_component_base` for details on the efficiency table format.

## Default Parameter Values

The `HardCoalSteamTurbine` class provides default values for base class parameters based on References [1-4]. Only `rated_capacity` and `initial_conditions` are required in the YAML configuration.

| Parameter | Default Value | Source |
|-----------|---------------|--------|
| `min_stable_load_fraction` | 0.30 (30%) | [2] |
| `ramp_rate_fraction` | 0.03 (3%/min) | [1] |
| `run_up_rate_fraction` | Same as `ramp_rate_fraction` | — |
| `hot_startup_time` | 7.5 hours | [1] |
| `warm_startup_time` | 7.5 hours | [1] |
| `cold_startup_time` | 7.5 hours | [1] |
| `min_up_time` | 48 hours | [2] |
| `min_down_time` | 48 hours | [2] |
| `efficiency_table` | Average plant efficiency | [2,3] |

### Default Efficiency Table

The default HHV net plant efficiency table is based on [2,3]:

| Power Fraction | HHV Net Efficiency |
|---------------|-------------------|
| 1.00 | 0.35 (35%) |
| 0.5o | 0.32 (32%) |
| 0.30 | 0.30 (30%) |

## HCST Outputs

The HCST model provides the following outputs (inherited from base class):

| Output | Units | Description |
|--------|-------|-------------|
| `power` | kW | Actual power output |
| `state` | integer | Operating state number (0-5), corresponding to the `STATES` enum |
| `efficiency` | fraction (0-1) | Current HHV net plant efficiency |
| `fuel_volume_rate` | m³/s | Fuel volume flow rate |
| `fuel_mass_rate` | kg/s | Fuel mass flow rate (computed using `fuel_density` |

### Efficiency and Fuel Rate

HHV net plant efficiency varies with load based on the `efficiency_table`. The fuel volume rate is calculated as:

$$
\text{fuel\_volume\_rate} = \frac{\text{power}}{\text{efficiency} \times \text{hhv}}
$$

Where:
- `power` is in W (converted from kW internally)
- `efficiency` is the HHV net efficiency interpolated from the efficiency table
- `hhv` is the higher heating value in J/m³
- Result is fuel volume rate in m³/s

The fuel mass rate is then computed from the volume rate using the fuel density:

$$
\text{fuel\_mass\_rate} = \text{fuel\_volume\_rate} \times \text{fuel\_density}
$$

Where:
- `fuel_volume_rate` is in m³/s
- `fuel_density` is in kg/m³
- Result is fuel mass rate in kg/s

## YAML Configuration

### Minimal Configuration

Required parameters only (uses defaults for `hhv`, `efficiency_table`, and other parameters):

```yaml
hard_coal_steam_turbine:
  component_type: HardCoalSteamTurbine
  rated_capacity: 100000  # kW (100 MW)
  initial_conditions:
    power: 0  # 0 kW means OFF; power > 0 means ON
```

### Full Configuration

All parameters explicitly specified:

```yaml
hard_coal_steam_turbine:
  component_type: HardCoalSteamTurbine
  rated_capacity: 500000  # kW (500 MW)
  min_stable_load_fraction: 0.3  # 30% minimum operating point
  ramp_rate_fraction: 0.03  # 3%/min ramp rate
  run_up_rate_fraction: 0.02  # 2%/min run up rate
  hot_startup_time: 27000.0  # 7.5 hours
  warm_startup_time: 27000.0  # 7.5 hours
  cold_startup_time: 27000.0  # 7.5 hours
  min_up_time: 172800  # 48 hours
  min_down_time: 172800  # 48 hour
  hhv: 29310000000  # J/m³ for bituminous coal (29.31 MJ/m³) [4]
  fuel_density: 1000  # kg/m³ for bituminous coal
  efficiency_table:
    power_fraction:
      - 1.0
      - 0.50
      - 0.30
    efficiency:  # HHV net plant efficiency, fractions (0-1)
      - 0.35
      - 0.32
      - 0.32
  log_channels:
    - power
    - fuel_volume_rate
    - fuel_mass_rate
    - state
    - efficiency
    - power_setpoint
  initial_conditions:
    power: 0  # 0 kW means OFF; power > 0 means ON
```

## Logging Configuration

The `log_channels` parameter controls which outputs are written to the HDF5 output file.

**Available Channels:**
- `power`: Actual power output in kW (always logged)
- `state`: Operating state number (0-5), corresponding to the `STATES` enum
- `fuel_volume_rate`: Fuel volume flow rate in m³/s
- `fuel_mass_rate`: Fuel mass flow rate in kg/s
- `efficiency`: Current HHV net plant efficiency (0-1)
- `power_setpoint`: Requested power setpoint in kW

## References

1. Agora Energiewende (2017): "Flexibility in thermal power plants - With a focus on existing coal-fired power plants."

2. IRENA (2019), Innovation landscape brief: Flexibility in conventional power plants, International Renewable Energy Agency, Abu Dhabi.

3. T. Schmitt, S. Leptinsky, M. Turner, A. Zoelle, C. White, S. Hughes, S. Homsy, et al. “Cost And Performance Baseline for Fossil Energy Plants Volume 1: Bituminous Coal and Natural Gas Electricity.” Pittsburgh, PA: National Energy Technology Laboratory, October 14, 2022b. https://doi.org/10.2172/1893822.

4. I. Staffell, "The Energy and Fuel Data Sheet," University of Birmingham, March 2011. https://claverton-energy.com/cms4/wp-content/uploads/2012/08/the_energy_and_fuel_data_sheet.pdf
