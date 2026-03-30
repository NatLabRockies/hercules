# Thermal Plant

The `ThermalPlant` class models generic single or multiunit thermal power plants. It expects to be assigned one or more thermal units, for example [`OpenCycleGasTurbine`s](open_cycle_gas_turbine.md). The individual units are established in the YAML configuration file, and may be repeats of the same type of units or heterogeneous units.

In order to use the thermal plant model, set `component_type: ThermalPlant` in the component's YAML section. The section key is a user-chosen `component_name` (e.g. `my_thermal_plant`); see [Component Names, Types, and Categories](component_types.md) for details.

For details on the state machine, startup/shutdown behavior, and base parameters, see {doc}`thermal_component_base`.

## Parameters

The `ThermalPlant` class does not have any default parameters. However, key attributes that must be provided in the YAML configuration file are `units`, which is a list that is used to instantiate the individual thermal units that make up the plant, and `unit_names`, which is a list of unique names for each unit. The number of entries in `units` and `unit_names` must match.

See the [YAML Configuration](#yaml-configuration) section below for examples of how to specify these parameters in the input file.

## YAML configuration

The YAML configuration for the thermal plant includes lists `units` and `unit_names`, that define the configuration for each unit. The `component_type` of each unit must be a valid thermal component type, e.g. `OpenCycleGasTurbine`. See [Component Types](component_types.md) for the full list of available component types.

The units listed under the `units` field are used to index the subdictionaries for each unit, which specify the parameters and initial conditions for each unit. For example, if `units: ["open_cycle_gas_turbine", "open_cycle_gas_turbine"]`, then the YAML file must include a subdictionary with the key `open_cycle_gas_turbine:` that specify the parameters and initial conditions that will be used for both of the two gas turbines. Different subdictionaries can be defined for each, or a subset, of units by adding a subdictionary defining the desired parameters and initial conditions, and adding it to the appropriate place in the `units` list. This is illustrated in the below example, where the first two units use the `large_ocgt` subdictionary and the last unit uses the `small_ocgt` subdictionary. The `unit_names` field is a list of unique names for each unit, which are used to identify the units in the HDF5 output file and in the `h_dict` passed to controllers. For example, if `unit_names: ["OCGT1", "OCGT2"]`, then the two gas turbines will be identified as `OCGT1` and `OCGT2` in the output file and in the `h_dict`.

```yaml
my_thermal_plant:
  component_type: ThermalPlant
  units: ["large_ocgt", "large_ocgt", "small_ocgt"]
  unit_names: ["OCGT1", "OCGT2", "OCGT3"]

  large_ocgt:
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
    hhv: 39050000  # J/m³ for natural gas (39.05 MJ/m³)
    fuel_density: 0.768  # kg/m³ for natural gas
    efficiency_table:
      power_fraction:
        - 1.0
        - 0.75
        - 0.50
        - 0.25
      efficiency:
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
      power: 0

  small_ocgt:
    component_type: OpenCycleGasTurbine
    rated_capacity: 50000  # kW (50 MW)
    min_stable_load_fraction: 0.4  # 40% minimum operating point
    ramp_rate_fraction: 0.15  # 15%/min ramp rate
    run_up_rate_fraction: 0.1  # 10%/min run up rate
    hot_startup_time: 300.0  # 5 minutes
    warm_startup_time: 360.0  # 6 minutes
    cold_startup_time: 420.0  # 7 minutes
    min_up_time: 1200  # 20 minutes
    min_down_time: 2400  # 40 minutes
    hhv: 39050000  # J/m³ for natural gas (39.05 MJ/m³) [6]
    fuel_density: 0.768  # kg/m
    efficiency_table:
      power_fraction:
        - 1.0
        - 0.75
        - 0.50
        - 0.25
      efficiency:
        - 0.38
        - 0.36
        - 0.32
        - 0.22
    log_channels:
      - power
    initial_conditions:
      power: 0
```

## Logging configuration

The `log_channels` parameter controls which outputs are written to the HDF5 output file. Logging is configured separately for each unit, so the `log_channels` field is specified within each unit's subdictionary. For example, if `unit_names: ["OCGT1", "OCGT1"]`, then the log will have columns `my_thermal_plant.OCGT1.power`, `my_thermal_plant.OCGT1.fuel_volume_rate`, etc. for the first unit, and `my_thermal_plant.OCGT2.power`, `my_thermal_plant.OCGT2.fuel_volume_rate`, etc. for the second unit, assuming those channels are included in the `log_channels` list for each unit. The total power for the thermal plant is always logged to `my_thermal_plant.power`, which is the sum of the power outputs of each unit.
