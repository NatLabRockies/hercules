# Combined Cycle Gas Turbine

The `CombinedCyclePlant` class models an combined-cycle gas turbine (CCGT), which pairs a gas turbine (or sometimes 2 gas turbines) with a steam turbine to increase efficiency. It therefore combines the units of the {doc}`OpenCycleGasTurbine <open_cycle_gas_turbine>` and {doc}`SteamTurbine <steam_turbine>`. It is a subclass of {doc}`ThermalPlant <thermal_plant>` and inherits most state machine behavior, ramp constraints, and operational logic from the base class. What makes this class different from the regular `ThermalPlant`, is that it includes the dependencies between the gas and steam turbine associated with a CCGT (i.e., the steam turbine can only run if the gas turbine is producing power).

To use this model, set `component_type: CombinedCyclePlant` in the component's YAML section. The section key is a user-chosen `component_name` (e.g. `combined_cycle_plant`); see [Component Names, Types, and Categories](component_types.md) for details.

For details on the state machine, startup/shutdown behavior, and base parameters of the individual units, see {doc}`thermal_component_base`.

## CCGT-Specific Parameters

Similar to the `ThermalPlant` class, the `CombinedCyclePlant` class does not have many default parameters. Key attributes that must be provided in the YAML configuration file are the `OpenCycleGasTurbine` and `SteamTurbine` `units`, which is a list that is used to instantiate the individual thermal units that make up the plant, and `unit_names`, which is a list of unique names for each unit. The number of entries in `units` and `unit_names` must match.

However, unlike the base `ThermalPlant` class, it is recommended that some parameters are defined outside the individual thermal units. Since the steam turbine does not have its own individual fuel source, instead using the rest heat from the gas turbine, it is not possible to specify the efficiency and fuel consumption of the steam turbine in the same way as done for individual components that are not linked. As a result, these outputs are instead calculated for the plant as a whole, necessitating an efficiency table for the unit as a whole. Note that this table is only used when both the gas and steam turbine are running. If only the gas turbine is running, the `OpenCycleGasTurbine` efficiency table is used instead.

The `efficiency_table` parameter is **optional**. If not provided, default values based on approximate readings from the CC1A curve in Exhibit ES-4 of [5] are used. All efficiency values are **HHV (Higher Heating Value) net plant efficiencies**. See {doc}`thermal_component_base` for details on the efficiency table format.

## Default Parameter Values

No default parameter values are currently defined, except for the aforementioned `efficiency_table`. See `examples/08_multi_unit_thermal_plants/input_files/hercules_input_mu-ccgt.yaml` for example parameter values.

### Default Efficiency Table

The default HHV net plant efficiency table is based on approximate readings from the CC1A (simple cycle) curve in Exhibit ES-4 of [5]:

| Power Fraction | HHV Net Efficiency |
|---------------|-------------------|
| 1.0           | 0.53  | 
| 0.95          | 0.515 | 
| 0.90          | 0.52  |
| 0.85          | 0.52  |
| 0.80          | 0.52  |
| 0.75          | 0.52  |
| 0.7           | 0.52  |
| 0.65          | 0.515 |
| 0.6           | 0.505 |
| 0.55          | 0.5   |
| 0.50          | 0.49  |
| 0.4           | 0.47  |

## OCGT Outputs

The CCGT plant model provides the following outputs:

| Output | Units | Description |
|--------|-------|-------------|
| `power` | kW | Actual power output |
| `efficiency` | fraction (0-1) | Current HHV net plant efficiency |
| `fuel_volume_rate` | m³/s | Fuel volume flow rate |
| `fuel_mass_rate` | kg/s | Fuel mass flow rate (computed using `fuel_density` [6]) |

Subsequently, the individual `OpenCycleGasTurbine` and `SteamTurbine` units provide the following outputs:

| Output | Units | Description |
|--------|-------|-------------|
| `power` | kW | Actual power output |
| `state` | integer | Operating state number (0-5), corresponding to the `STATES` enum |
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

## YAML configuration

The YAML configuration for the combined cycle plant includes list `units` and `unit_names`, as then as subdictionaries, list the configuration for each unit. The `component_type` of each unit must be `OpenCycleGasTurbine` or `SteamTurbine`.

The units listed under the `units` field are used to index the subdictionaries for each unit, which specify the parameters and initial conditions for each unit. For `units: ["open_cycle_gas_turbine", "steam_turbine"]`, the YAML file must include two subdictionaries with keys `open_cycle_gas_turbine:` and `steam_turbine:` that specify the parameters and initial conditions for each of the two units. The `unit_names` field is a list of unique names for each unit, which are used to identify the units in the HDF5 output file and in the `h_dict` passed to controllers. For example, if `unit_names: ["OCGT", "ST"]`, then the two gas turbines will be identified as `OCGT` and `ST` in the output file and in the `h_dict`.

```yaml
plant:
  interconnect_limit: 100000  # kW (100 MW)
  power_setpoint_schedule:
    time: # Time in seconds from start
      - 0
      - 600
      - 3600
      - 15600
      - 21600
      - 28800
      - 32400
    power_setpoint_fraction:
      - 1.0
      - 0.0
      - 1.0
      - 0.5
      - 0.1
      - 1.0
      - 0.0

combined_cycle_plant:
  component_type: CombinedCyclePlant
  units: ["open_cycle_gas_turbine", "steam_turbine"]
  unit_names: ["OCGT", "ST"]

  open_cycle_gas_turbine:
    component_type: OpenCycleGasTurbine
    rated_capacity: 70000  # kW (70 MW)
    min_stable_load_fraction: 0.4  # 40% minimum operating point
    ramp_rate_fraction: 0.1  # 10%/min ramp rate
    run_up_rate_fraction: 0.05  # 5%/min run up rate
    hot_startup_time: 1800.0  # 30 minutes
    warm_startup_time: 2700.0  # 45 minutes
    cold_startup_time: 2700.0  # 45 minutes
    min_up_time: 14400  # 4 hour
    min_down_time: 7200  # 2 hour
    # Natural gas properties from [6] Staffell, "The Energy and Fuel Data Sheet", 2011
    # HHV: 39.05 MJ/m³, Density: 0.768 kg/m³
    hhv: 39050000  # J/m³ for natural gas (39.05 MJ/m³) [6]
    fuel_density: 0.768  # kg/m³ for natural gas [6]
    efficiency_table:
      power_fraction:
        - 1.0
        - 0.75
        - 0.50
        - 0.25
      efficiency:  # HHV net plant efficiency, fractions (0-1), from SC1A in Exhibit ES-4 of [5]
        - 0.39
        - 0.37
        - 0.325
        - 0.245
    log_channels:
      - power
      - state
      - power_setpoint
    initial_conditions:
      power: 70000  # Start ON at rated capacity (70 MW)

  steam_turbine:
    component_type: SteamTurbine
    rated_capacity: 30000  # kW (30 MW)
    min_stable_load_fraction: 0.4  # 40% minimum operating point
    ramp_rate_fraction: 0.05  # 5%/min ramp rate
    run_up_rate_fraction: 0.02  # 2%/min run up rate
    hot_startup_time: 3600.0  # 1 hour
    warm_startup_time: 7200.0  # 2 hours
    cold_startup_time: 14400.0  # 4 hours
    min_up_time: 14400  # 4 hour
    min_down_time: 7200  # 2 hour
    # Natural gas properties from [6] Staffell, "The Energy and Fuel Data Sheet", 2011
    # HHV: 39.05 MJ/m³, Density: 0.768 kg/m³
    # hhv: 39050000  # J/m³ for natural gas (39.05 MJ/m³) [6]
    # fuel_density: 0.768  # kg/m³ for natural gas [6]
    efficiency_table:
      power_fraction:
        - 1.0
        - 0.75
        - 0.50
        - 0.25
      efficiency:  # HHV net plant efficiency, fractions (0-1), from SC1A in Exhibit ES-4 of [5]
        - 0.14
        - 0.15
        - 0.165
        - 0.17
    log_channels:
      - power
      - state
      - power_setpoint
    initial_conditions:
      power: 30000  # Start ON at rated capacity (30 MW)

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
    - efficiency
```

## Logging Configuration

The `log_channels` parameter controls which outputs are written to the HDF5 output file.

**Available Channels:**
- `power`: Actual power output in kW (always logged)
- `state`: Operating state number (0-5), corresponding to the `STATES` enum (only available for the individual units)
- `fuel_volume_rate`: Fuel volume flow rate in m³/s (only available for the unit as a whole)
- `fuel_mass_rate`: Fuel mass flow rate in kg/s (computed using `fuel_density` [6]) (only available for the unit as a whole)
- `efficiency`: Current HHV net plant efficiency (0-1) (only available for the unit as a whole)
- `power_setpoint`: Requested power setpoint in kW (only available for the unit as a whole)

## References

1. Agora Energiewende (2017): "Flexibility in thermal power plants - With a focus on existing coal-fired power plants."

2. "Impact of Detailed Parameter Modeling of Open-Cycle Gas Turbines on Production Cost Simulation", NREL/CP-6A40-87554, National Renewable Energy Laboratory, 2024.

3. Deane, J.P., G. Drayton, and B.P. Ó Gallachóir. "The Impact of Sub-Hourly Modelling in Power Systems with Significant Levels of Renewable Generation." Applied Energy 113 (January 2014): 152–58. https://doi.org/10.1016/j.apenergy.2013.07.027.

4. IRENA (2019), Innovation landscape brief: Flexibility in conventional power plants, International Renewable Energy Agency, Abu Dhabi.

5. M. Oakes, M. Turner, "Cost and Performance Baseline for Fossil Energy Plants, Volume 5: Natural Gas Electricity Generating Units for Flexible Operation," National Energy Technology Laboratory, Pittsburgh, May 5, 2023.

6. I. Staffell, "The Energy and Fuel Data Sheet," University of Birmingham, March 2011. https://claverton-energy.com/cms4/wp-content/uploads/2012/08/the_energy_and_fuel_data_sheet.pdf
