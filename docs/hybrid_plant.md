# Hybrid Plant Components

The `HybridPlant` class manages all plant components in Hercules. It handles initialization, execution, and coordination of individual components while computing plant-level outputs.

## Overview

`HybridPlant` auto-discovers components from the [h_dict](h_dict.md) at initialization time. Any top-level `h_dict` entry whose value is a dict containing a `component_type` key is treated as a plant component. The YAML key becomes the component's `component_name` (a user-chosen instance identifier), and the `component_type` value determines which Python class is instantiated.

See [Component Names, Types, and Categories](component_types.md) for a full explanation of how `component_name`, `component_type`, and `component_category` relate to each other.

## Available Components

| `component_type` | `component_category` | Generator? | Documentation |
|---|---|---|---|
| `WindFarm` | `wind_farm` | Yes | [Wind](wind.md) |
| `WindFarmSCADAPower` | `wind_farm` | Yes | [Wind](wind.md) |
| `SolarPySAMPVWatts` | `solar_farm` | Yes | [Solar PV](solar_pv.md) |
| `BatterySimple` | `battery` | No | [Battery](battery.md) |
| `BatteryLithiumIon` | `battery` | No | [Battery](battery.md) |
| `ElectrolyzerPlant` | `electrolyzer` | No | [Electrolyzer](electrolyzer.md) |
| `OpenCycleGasTurbine` | `thermal` | Yes | [Open Cycle Gas Turbine](open_cycle_gas_turbine.md) |

The YAML key for each section is a user-chosen `component_name` and is not required to match the category name. For example, a `BatterySimple` component could be named `battery`, `battery_unit_1`, or anything else.

## Generator Classification

`HybridPlant` classifies components into generators and non-generators based on `component_category`. Components in the `wind_farm`, `solar_farm`, and `thermal` categories are generators; their power outputs are summed into `h_dict["plant"]["locally_generated_power"]` each time step. Batteries and electrolyzers are excluded from this sum.
