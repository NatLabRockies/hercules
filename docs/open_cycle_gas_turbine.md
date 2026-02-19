# Open Cycle Gas Turbine

The `OpenCycleGasTurbine` class models an open-cycle gas turbine (OCGT), also known as a peaker plant or simple-cycle gas turbine. Since this class is focused on peaker plant behavior, this class was developed based on aeroderivative engines. It is a subclass of {doc}`ThermalComponentBase <thermal_component_base>` and inherits all state machine behavior, ramp constraints, and operational logic from the base class.

For details on the state machine, startup/shutdown behavior, and base parameters, see {doc}`thermal_component_base`.

## OCGT-Specific Parameters

The OCGT class provides default values for natural gas properties from [6]:

| Parameter | Units | Default | Description |
|-----------|-------|---------|-------------|
| `hhv` | J/m³ | 39050000 | Higher heating value of natural gas (39.05 MJ/m³) [6] |
| `fuel_density` | kg/m³ | 0.768 | Fuel density for mass calculations [6] |

The `efficiency_table` parameter is **optional**. If not provided, default values based on approximate readings from the SC1A curve in Exhibit ES-4 of [5] are used. All efficiency values are **HHV (Higher Heating Value) net plant efficiencies**. See {doc}`thermal_component_base` for details on the efficiency table format.

## Default Parameter Values

The `OpenCycleGasTurbine` class provides default values for base class parameters based on References [1-5]. Only `rated_capacity` and `initial_conditions` are required in the YAML configuration.

| Parameter | Default Value | Source |
|-----------|---------------|--------|
| `min_stable_load_fraction` | 0.40 (40%) | [4] |
| `ramp_rate_fraction` | 0.10 (10%/min) | [1] |
| `run_up_rate_fraction` | Same as `ramp_rate_fraction` | — |
| `hot_startup_time` | 420 s (7 minutes) | [1], [5] |
| `warm_startup_time` | 480 s (8 minutes) | [1], [5] |
| `cold_startup_time` | 480 s (8 minutes) | [1], [5] |
| `min_up_time` | 1800 s (30 minutes) | [4] |
| `min_down_time` | 3600 s (1 hour) | [4] |
| `hhv` | 39050000 J/m³ (39.05 MJ/m³) | [6] |
| `fuel_density` | 0.768 kg/m³ | [6] |
| `efficiency_table` | SC1A HHV net efficiency (see below) | Exhibit ES-4 of [5] |

### Default Efficiency Table

The default HHV net plant efficiency table is based on approximate readings from the SC1A (simple cycle) curve in Exhibit ES-4 of [5]:

| Power Fraction | HHV Net Efficiency |
|---------------|-------------------|
| 1.00 | 0.39 (39%) |
| 0.75 | 0.37 (37%) |
| 0.50 | 0.325 (32.5%) |
| 0.25 | 0.245 (24.5%) |

## OCGT Outputs

The OCGT model provides the following outputs (inherited from base class):

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
open_cycle_gas_turbine:
  component_type: OpenCycleGasTurbine
  rated_capacity: 100000  # kW (100 MW)
  initial_conditions:
    power: 0  # 0 kW means OFF; power > 0 means ON
```

### Full Configuration

All parameters explicitly specified:

```yaml
open_cycle_gas_turbine:
  component_type: OpenCycleGasTurbine
  rated_capacity: 100000  # kW (100 MW)
  min_stable_load_fraction: 0.4  # 40% minimum operating point
  ramp_rate_fraction: 0.1  # 10%/min ramp rate
  run_up_rate_fraction: 0.05  # 5%/min run up rate
  hot_startup_time: 420.0  # 7 minutes
  warm_startup_time: 480.0  # 8 minutes
  cold_startup_time: 480.0  # 8 minutes
  min_up_time: 1800  # 30 minutes
  min_down_time: 3600  # 1 hour
  hhv: 39050000  # J/m³ for natural gas (39.05 MJ/m³) [6]
  fuel_density: 0.768  # kg/m³ for natural gas [6]
  efficiency_table:
    power_fraction:
      - 1.0
      - 0.75
      - 0.50
      - 0.25
    efficiency:  # HHV net plant efficiency from SC1A in Exhibit ES-4 of [5]
      - 0.39
      - 0.37
      - 0.325
      - 0.245
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
