"""
Multiunit thermal power plant.
"""

import copy

from hercules.plant_components.component_base import ComponentBase
from hercules.plant_components.thermal_component_base import ThermalComponentBase


class ThermalPlant(ComponentBase):
    """Thermal power plant comprising multiple units.

    The thermal plant component is designed to represent a collection of thermal generation units
    (e.g. gas turbines, steam turbines, RICEs) that are grouped together into a single Hercules
    component.  This allows users to model a thermal plant with multiple units with finer
    granularity than a single aggregate component. Control setpoints can be specified for each unit.

    """

    component_category = "generator"

    def __init__(self, h_dict, component_name):
        # Instantiate individual units from the h_dict.

        self.unit_names = h_dict[component_name]["unit_names"]
        generic_units = h_dict[component_name]["units"]

        # Check that unit_names are valid
        if len(self.unit_names) != len(generic_units):
            raise ValueError(
                f"Length of unit_names ({len(self.unit_names)}) must match length of units "
                f"({len(generic_units)})."
            )
        if len(set(self.unit_names)) != len(self.unit_names):
            raise ValueError(f"unit_names must be unique. Found duplicates in {self.unit_names}.")

        for unit, unit_name in zip(generic_units, self.unit_names):
            if unit_name not in h_dict[component_name]:
                h_dict[component_name][unit_name] = copy.deepcopy(h_dict[component_name][unit])

        # Remove the template from the component dict since it's now copied into each unit dict
        for unit in generic_units:
            if unit in h_dict[component_name]:
                del h_dict[component_name][unit]

        # Load component registry here to define units in thermal plant
        # NOTE: this breaks a circular dependency issue
        from hercules.component_registry import COMPONENT_REGISTRY

        self.units = []
        for unit, unit_name in zip(h_dict[component_name]["units"], self.unit_names):
            h_dict_thermal = h_dict[component_name]
            h_dict_thermal["dt"] = h_dict["dt"]
            h_dict_thermal["starttime"] = h_dict["starttime"]
            h_dict_thermal["endtime"] = h_dict["endtime"]
            h_dict_thermal["verbose"] = h_dict["verbose"]
            unit_type = h_dict["thermal_power_plant"][unit_name]["component_type"]
            unit_class = COMPONENT_REGISTRY[unit_type]
            if unit_class is None:
                raise ValueError(f"Unit type {unit_type} not found in component registry.")
            elif not issubclass(unit_class, ThermalComponentBase):
                raise ValueError(
                    f"Unit type {unit_type} must be a subclass of ThermalComponentBase."
                )
            else:
                self.units.append(unit_class(h_dict_thermal, unit_name))

        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)

    def step(self, h_dict):
        """
        Step the thermal plant by stepping each individual unit and summing their power outputs.
        """
        thermal_plant_power = 0.0

        for unit, unit_name, power_setpoint in zip(
            self.units, self.unit_names, h_dict[self.component_name]["power_setpoints"]
        ):
            h_dict_thermal = h_dict[self.component_name]
            h_dict_thermal[unit_name]["power_setpoint"] = power_setpoint
            h_dict_thermal = unit.step(h_dict_thermal)
            thermal_plant_power += h_dict_thermal[unit_name]["power"]

        h_dict[self.component_name]["power"] = thermal_plant_power

        return h_dict

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Get initial conditions and metadata for the thermal plant.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
        """
        # NOTE: h_dict is modified in place, so h_dict will be updated with the initial
        # conditions and metadata for each unit.
        for unit in self.units:
            h_dict_thermal = h_dict[self.component_name]
            unit.get_initial_conditions_and_meta_data(h_dict_thermal)

        h_dict[self.component_name]["power"] = sum(
            h_dict_thermal[unit.component_name]["power"] for unit in self.units
        )
        h_dict[self.component_name]["rated_capacity"] = sum(
            h_dict_thermal[unit.component_name]["rated_capacity"] for unit in self.units
        )

        return h_dict
