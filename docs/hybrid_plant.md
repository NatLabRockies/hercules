# Hybrid Plant Components

The `HybridPlant` class manages all plant components in Hercules. It handles initialization, execution, and coordination of individual components while computing plant-level outputs.

## Overview

`HybridPlant` auto-discovers components from the [h_dict](h_dict.md) at initialization time. Any top-level `h_dict` entry whose value is a dict containing a `component_type` key is treated as a plant component. The YAML key becomes the component's `component_name` (a user-chosen instance identifier), and the `component_type` value determines which Python class is instantiated.

See [Component Names, Types, and Categories](component_types.md) for a full explanation of how `component_name`, `component_type`, and `component_category` relate to each other.

## Available Components

| `component_type` | `component_category` | Generator? | Documentation |
|---|---|---|---|
| `WindFarm` | `generator` | Yes | [Wind](wind.md) |
| `WindFarmSCADAPower` | `generator` | Yes | [Wind](wind.md) |
| `SolarPySAMPVWatts` | `generator` | Yes | [Solar PV](solar_pv.md) |
| `BatteryDynamic` | `storage` | No | [Battery](battery.md) |
| `BatteryReservoir` | `storage` | No | [Battery](battery.md) |
| `BatteryLithiumIon` | `storage` | No | [Battery](battery.md) |
| `ElectrolyzerPlant` | `load` | No | [Electrolyzer](electrolyzer.md) |
| `OpenCycleGasTurbine` | `generator` | Yes | [Open Cycle Gas Turbine](open_cycle_gas_turbine.md) |
| `LinearGenerator` | `generator` | Yes | [Linear Generator](linear_generator.md) |
| `SteamTurbine` | `generator` | [Steam Turbine](steam_turbine.md) |
| `ThermalPlant` | `generator` | [Thermal Plant](thermal_plant.md) |

The YAML key for each section is a user-chosen `component_name` and is not required to match the category name. For example, a `BatteryDynamic` component could be named `battery`, `battery_unit_1`, or anything else.

## Generator Classification

`HybridPlant` classifies components into generators and non-generators based on `component_category`. Components with `component_category == "generator"` have their power outputs summed into `h_dict["plant"]["locally_generated_power"]` each time step. Storage and load components are excluded from this sum.

## Plant-Level Outputs

Each step `HybridPlant` computes (see [Nomenclature](nomenclature.md)):

- `plant.power_bus`: sum of all component `power` on the LV bus.
- `plant.power_export`: power at the POI after the bus-to-POI losses, $\eta P_{bus}$ when exporting and $P_{bus} / \eta$ when importing, with $\eta$ = `plant.eta_bus_to_poi` (optional input, default 1.0).
- `plant.locally_generated_power`: sum of generator `power`.

## Sign Convention

Outside components, power delivered to the bus is positive. Storage and load components use the opposite (consumer) convention internally; `HybridPlant` passes them a negated copy of `power_setpoint` and negates the outputs listed in their `consumer_sign_outputs`. The controller-owned setpoint in `h_dict` is not modified.

## Component Registry

All available component types are defined in `COMPONENT_REGISTRY` in `hercules/component_registry.py`. This dictionary maps `component_type` strings to their Python classes:

```python
COMPONENT_REGISTRY = {
    "WindFarm": WindFarm,
    "WindFarmSCADAPower": WindFarmSCADAPower,
    "SolarPySAMPVWatts": SolarPySAMPVWatts,
    "BatteryDynamic": BatteryDynamic,
    "BatteryReservoir": BatteryReservoir,
    "BatteryLithiumIon": BatteryLithiumIon,
    "ElectrolyzerPlant": ElectrolyzerPlant,
    "OpenCycleGasTurbine": OpenCycleGasTurbine,
}
```

When adding a new component type, it must be registered here. See [Adding Components](adding_components.md) for a complete guide.
