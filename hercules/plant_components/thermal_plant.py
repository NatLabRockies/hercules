"""
Multiunit thermal power plant.
"""
import copy

from hercules.plant_components.component_base import ComponentBase
from hercules.plant_components.open_cycle_gas_turbine import OpenCycleGasTurbine


class ThermalPlant(ComponentBase):
    """ """

    component_category = "generator"

    def __init__(self, h_dict, component_name):
        # Instantiate individual units from the h_dict.

        self.unit_names = h_dict[component_name]["unit_names"]
        generic_units = h_dict[component_name]["units"]

        for unit, unit_name in zip(generic_units, self.unit_names):
            if unit_name not in h_dict[component_name]:
                h_dict[component_name][unit_name] = copy.deepcopy(h_dict[component_name][unit])

        # Remove the template from the component dict since it's now copied into each unit dict
        for unit in generic_units:
            if unit in h_dict[component_name]:
                del h_dict[component_name][unit]

        self.units = []
        for unit, unit_name in zip(h_dict[component_name]["units"], self.unit_names):
            h_dict_thermal = h_dict[component_name]
            h_dict_thermal["dt"] = h_dict["dt"]
            h_dict_thermal["starttime"] = h_dict["starttime"]
            h_dict_thermal["endtime"] = h_dict["endtime"]
            h_dict_thermal["verbose"] = h_dict["verbose"]
            self.units.append(OpenCycleGasTurbine(h_dict_thermal, unit_name))

        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)

    def step(self, h_dict):
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
        for unit in self.units:
            h_dict_thermal = h_dict[self.component_name]
            h_dict_thermal = unit.get_initial_conditions_and_meta_data(h_dict_thermal)

        h_dict[self.component_name]["power"] = sum(
            h_dict_thermal[unit.component_name]["power"] for unit in self.units
        )

        # TODO: we likely want to save off data for the individual units to the
        # h_dict as well. Will need to figure out how to do that.

        return h_dict
