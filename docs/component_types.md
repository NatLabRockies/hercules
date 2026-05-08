# Component Names, Types, and Categories

Three related but distinct concepts govern how plant components are identified in Hercules: `component_name`, `component_type`, and `component_category`. Understanding the distinction is important for writing YAML input files and for programmatically working with `h_dict`.

## The Three Concepts

### `component_name`

The **component name** is the top-level YAML key for the component section. It is user-chosen and becomes the key used to access the component's state in `h_dict` throughout the simulation.

- **Source**: YAML input file (the key you choose)
- **Can be**: Any valid YAML string — `"battery"`, `"battery_unit_1"`, `"my_wind_farm"`, etc.
- **Available as**: `self.component_name` on the component object; `h_dict[component_name]` at runtime

The name does not need to match the category. Using the category name (e.g. `battery:`) is a common convention for single-instance plants and is used throughout most examples in these docs.

### `component_type`

The **component type** is the string value of the `component_type` field inside the component's YAML section. It determines which Python class gets instantiated.

- **Source**: `component_type:` field in the component's YAML block
- **Must be**: Exactly one of the registered class name strings (see [reference table](#complete-component-type-reference) below)
- **Available as**: `self.component_type` on the component object (set automatically from the class name — never needs to be hardcoded in component code)

### `component_category`

The **component category** is a class-level attribute defined in each component class. It is not read from YAML — it is part of the class definition itself.

- **Source**: `component_category = "..."` class variable in the Python class
- **Valid values**: `"generator"`, `"load"`, or `"storage"`
- **Used by**: `HybridPlant` to classify components as generators vs. load/storage, and to apply the storage sign convention
- **Available as**: `self.component_category` on the component object (and `ComponentBase.component_category` as a class attribute)

Every `ComponentBase` subclass **must** define `component_category`; a `TypeError` is raised at class-definition time if it is missing.

### Summary

| Concept | Set by | Example value | Used for |
|---|---|---|---|
| `component_name` | User (YAML key) | `"battery_unit_1"` | Accessing `h_dict[name]`; unique instance ID |
| `component_type` | User (`component_type:` field) | `"BatterySimple"` | Registry lookup to select the Python class |
| `component_category` | Developer (class variable) | `"storage"` | Generator classification; sign convention |

---

## Complete Component Type Reference

| `component_type` | `component_category` | Documentation |
|---|---|---|
| `WindFarm` | `generator` | [Wind](wind.md) |
| `WindFarmSCADAPower` | `generator` | [Wind](wind.md) |
| `PowerPlayback` | `generator` | [Power Playback](power_playback.md) |
| `SolarPySAMPVWatts` | `generator` | [Solar PV](solar_pv.md) |
| `BatterySimple` | `storage` | [Battery](battery.md) |
| `BatteryLithiumIon` | `storage` | [Battery](battery.md) |
| `ElectrolyzerPlant` | `load` | [Electrolyzer](electrolyzer.md) |
| `OpenCycleGasTurbine` | `generator` | [Open Cycle Gas Turbine](open_cycle_gas_turbine.md) |
| `HardCoalSteamTurbine` | `generator` | [Hard Coal Steam Turbine](hard_coal_steam_turbine.md) |
| `ThermalPlant` | `generator` | [Thermal Plant](thermal_plant.md) |

Components with `component_category == "generator"` contribute to `h_dict["plant"]["locally_generated_power"]`.

For a guide on implementing new component types, see [Adding Components](adding_components.md).

---

## Multi-Instance Plants

Because `component_name` is user-chosen, you can include multiple instances of the same `component_type` in one plant. Give each instance a unique YAML key:

```yaml
battery_unit_1:
  component_type: BatterySimple
  energy_capacity: 100.0  # kWh
  charge_rate: 50.0       # kW
  discharge_rate: 50.0    # kW
  max_SOC: 0.9
  min_SOC: 0.1
  initial_conditions:
    SOC: 0.5

battery_unit_2:
  component_type: BatterySimple
  energy_capacity: 200.0  # kWh
  charge_rate: 100.0      # kW
  discharge_rate: 100.0   # kW
  max_SOC: 0.95
  min_SOC: 0.05
  initial_conditions:
    SOC: 0.8
```

In a controller, access each instance by its name:

```python
class MyController:
    def step(self, h_dict):
        power_1 = h_dict["battery_unit_1"]["power"]
        power_2 = h_dict["battery_unit_2"]["power"]

        h_dict["battery_unit_1"]["power_setpoint"] = 25.0
        h_dict["battery_unit_2"]["power_setpoint"] = -50.0
        return h_dict
```

`h_dict["component_names"]` contains the list of all discovered component names, e.g. `["battery_unit_1", "battery_unit_2"]`.

---

## Conventions

For single-instance plants, it is conventional to use the `component_category` as the YAML key — e.g. `battery:`, `wind_farm:`, `solar_farm:`. This matches most examples in these docs and makes the input file easy to read. It is not required; the key is always user-chosen.
