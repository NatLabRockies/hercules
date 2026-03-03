# Combined Cycle Gas Turbine

The `CombinedCycleGasTurbine` class models a combined-cycle gas turbine (CCGT). It is a subclass of {doc}`ThermalComponentBase <thermal_component_base>` and inherits all state machine behavior, ramp constraints, and operational logic from the base class. This class represents the combined gas turbine and steam turbine operation as an improvement in the fuel efficiency of the unit and does not model the individual generators.

For details on the state machine, startup/shutdown behavior, and base parameters, see {doc}`thermal_component_base`.

## CCGT-Specific Parameters

The CCGT class provides default values for natural gas properties from [6]:

| Parameter | Units | Default | Description |
|-----------|-------|---------|-------------|
| `hhv` | J/m³ | 39050000 | Higher heating value of natural gas (39.05 MJ/m³) [6] |
| `fuel_density` | kg/m³ | 0.768 | Fuel density for mass calculations [6] |

The `efficiency_table` parameter is **optional**. If not provided, default values based on approximate readings from the CC1A-F curve in Exhibit ES-4 of [5] are used. All efficiency values are **HHV (Higher Heating Value) net plant efficiencies**. See {doc}`thermal_component_base` for details on the efficiency table format.

## Default Parameter Values

The `CombinedCycleGasTurbine` class provides default values for base class parameters based on References [1-5]. Only `rated_capacity` and `initial_conditions` are required in the YAML configuration.

| Parameter | Default Value | Source |
|-----------|---------------|--------|
| `min_stable_load_fraction` | 0.40 (40%) | [4] |
| `ramp_rate_fraction` | 0.03 (3%/min) | [1] |
| `run_up_rate_fraction` | Same as `ramp_rate_fraction` | — |
| `hot_startup_time` | 4500 s (75 minutes, 1.25 hours) | [1], [5] |
| `warm_startup_time` | 7200 s (120 minutes, 2 hours) | [1], [5] |
| `cold_startup_time` | 10800 s (180 minutes, 3 hours) | [1], [5] |
| `min_up_time` | 14400 s (240 minutes, 4 hours) | [4] |
| `min_down_time` | 7200 s (120 minutes, 2 hours) | [4] |
| `hhv` | 39050000 J/m³ (39.05 MJ/m³) | [6] |
| `fuel_density` | 0.768 kg/m³ | [6] |
| `efficiency_table` | SC1A HHV net efficiency (see below) | Exhibit ES-4 of [5] |

### Default Efficiency Table

The default HHV net plant efficiency table is based on approximate readings from the CC1A-F curve in Exhibit ES-4 of [5]:

| Power Fraction | HHV Net Efficiency |
|---------------|-------------------|
| 1.00 | 0.53 (53%) |
| 0.95 | 0.515 (51.5%) |
| 0.90 | 0.52 (52%) |
| 0.85 | 0.52 (52%) |
| 0.80 | 0.52 (52%) |
| 0.75 | 0.52 (52%) |
| 0.70 | 0.52 (52%) |
| 0.65 | 0.515 (51.5%) |
| 0.60 | 0.505 (50.5%) |
| 0.55 | 0.5 (50%) |
| 0.50 | 0.49 (49%) |
| 0.4 | 0.47 (47%) |

## CCGT Outputs

The CCGT model provides the following outputs (inherited from base class):

| Output | Units | Description |
|--------|-------|-------------|
| `power` | kW | Actual power output |
| `state` | integer | Operating state number (0-5), corresponding to the `STATES` enum |
| `efficiency` | fraction (0-1) | Current HHV net plant efficiency |
| `fuel_volume_rate` | m³/s | Fuel volume flow rate |
| `fuel_mass_rate` | kg/s | Fuel mass flow rate (computed using `fuel_density` [6]) |

### Efficiency and Fuel Rate

HHV net plant efficiency varies with load based on the `efficiency_table`. The fuel volume rate is calculated as:

$$
\text{fuel\_volume\_rate} = \frac{\text{power}}{\text{efficiency} \times \text{hhv}}
$$

Where:
- `power` is in W (converted from kW internally)
- `efficiency` is the HHV net efficiency interpolated from the efficiency table
- `hhv` is the higher heating value in J/m³ (default 39.05 MJ/m³ for natural gas [6])
- Result is fuel volume rate in m³/s

The fuel mass rate is then computed from the volume rate using the fuel density [6]:

$$
\text{fuel\_mass\_rate} = \text{fuel\_volume\_rate} \times \text{fuel\_density}
$$

Where:
- `fuel_volume_rate` is in m³/s
- `fuel_density` is in kg/m³ (default 0.768 kg/m³ for natural gas [6])
- Result is fuel mass rate in kg/s

## YAML Configuration

### Minimal Configuration

Required parameters only (uses defaults for `hhv`, `efficiency_table`, and other parameters):

```yaml
combined_cycle_gas_turbine:
  component_type: CombinedCycleGasTurbine
  rated_capacity: 100000  # kW (100 MW)
  initial_conditions:
    power: 0  # 0 kW means OFF; power > 0 means ON
```

### Full Configuration

All parameters explicitly specified:

```yaml
combined_cycle_gas_turbine:
  component_type: CombinedCycleGasTurbine
  rated_capacity: 100000  # kW (100 MW)
  min_stable_load_fraction: 0.4  # 40% minimum operating point
  ramp_rate_fraction: 0.03  # 3%/min ramp rate
  run_up_rate_fraction: 0.02 # 2%/min run up rate
  hot_startup_time: 4500.0  # 75 minutes
  warm_startup_time: 7200.0  # 120 minutes
  cold_startup_time: 10800.0  # 180 minutes
  min_up_time: 14400  # 4 hours
  min_down_time: 7200  # 2 hours
  # Natural gas properties from [6] Staffell, "The Energy and Fuel Data Sheet", 2011
  # HHV: 39.05 MJ/m³, Density: 0.768 kg/m³
  hhv: 39050000  # J/m³ for natural gas (39.05 MJ/m³) [6]
  fuel_density: 0.768  # kg/m³ for natural gas [6]
  efficiency_table:
    power_fraction:
      - 1.0
      - 0.95
      - 0.90
      - 0.85
      - 0.80
      - 0.75
      - 0.7
      - 0.65
      - 0.6
      - 0.55
      - 0.50
      - 0.4
    efficiency:  # HHV net plant efficiency, fractions (0-1), from CC1A-F curve in Exhibit ES-4 of [5]
      - 0.53
      - 0.515
      - 0.52
      - 0.52
      - 0.52
      - 0.52
      - 0.52
      - 0.515
      - 0.505
      - 0.5
      - 0.49
      - 0.47
  log_channels:
    - power
    - fuel_volume_rate
    - fuel_mass_rate
    - state
    - efficiency
    - power_setpoint
  initial_conditions:
    power: 100000  # 0 kW means OFF; power > 0 means ON

```

## Logging Configuration

The `log_channels` parameter controls which outputs are written to the HDF5 output file.

**Available Channels:**
- `power`: Actual power output in kW (always logged)
- `state`: Operating state number (0-5), corresponding to the `STATES` enum
- `fuel_volume_rate`: Fuel volume flow rate in m³/s
- `fuel_mass_rate`: Fuel mass flow rate in kg/s (computed using `fuel_density` [6])
- `efficiency`: Current HHV net plant efficiency (0-1)
- `power_setpoint`: Requested power setpoint in kW

## References

1. Agora Energiewende (2017): "Flexibility in thermal power plants - With a focus on existing coal-fired power plants."

2. "Impact of Detailed Parameter Modeling of Open-Cycle Gas Turbines on Production Cost Simulation", NREL/CP-6A40-87554, National Renewable Energy Laboratory, 2024.

3. Deane, J.P., G. Drayton, and B.P. Ó Gallachóir. "The Impact of Sub-Hourly Modelling in Power Systems with Significant Levels of Renewable Generation." Applied Energy 113 (January 2014): 152–58. https://doi.org/10.1016/j.apenergy.2013.07.027.

4. IRENA (2019), Innovation landscape brief: Flexibility in conventional power plants, International Renewable Energy Agency, Abu Dhabi.

5. M. Oakes, M. Turner, "Cost and Performance Baseline for Fossil Energy Plants, Volume 5: Natural Gas Electricity Generating Units for Flexible Operation," National Energy Technology Laboratory, Pittsburgh, May 5, 2023.

6. I. Staffell, "The Energy and Fuel Data Sheet," University of Birmingham, March 2011. https://claverton-energy.com/cms4/wp-content/uploads/2012/08/the_energy_and_fuel_data_sheet.pdf
