import numpy as np

from hercules.plant_components.battery_lithium_ion import BatteryLithiumIon
from hercules.plant_components.battery_simple import BatterySimple
from hercules.plant_components.electrolyzer_plant import ElectrolyzerPlant
from hercules.plant_components.open_cycle_gas_turbine import OpenCycleGasTurbine
from hercules.plant_components.solar_pysam_pvwatts import SolarPySAMPVWatts
from hercules.plant_components.wind_farm import WindFarm
from hercules.plant_components.wind_farm_scada_power import WindFarmSCADAPower

# Registry mapping component_type strings to their classes.
# Add new component types here to make them discoverable by HybridPlant.
COMPONENT_REGISTRY = {
    "WindFarm": WindFarm,
    "WindFarmSCADAPower": WindFarmSCADAPower,
    "SolarPySAMPVWatts": SolarPySAMPVWatts,
    "BatterySimple": BatterySimple,
    "BatteryLithiumIon": BatteryLithiumIon,
    "ElectrolyzerPlant": ElectrolyzerPlant,
    "OpenCycleGasTurbine": OpenCycleGasTurbine,
}

# Derived from registry keys for validation in utilities.py
VALID_COMPONENT_TYPES = tuple(COMPONENT_REGISTRY.keys())


class HybridPlant:
    """Manages hybrid plant components for Hercules.

    This class handles the initialization, execution, and coordination of various
    plant components including wind farms, solar panels, batteries,
    and electrolyzers. It also computes plant-level outputs by aggregating
    individual component results.
    """

    def __init__(self, h_dict):
        """Initialize the hybrid plant manager.

        Args:
            h_dict (dict): Dictionary containing simulation parameters and
                configuration for all plant components.

        Raises:
            Exception: If no plant components are found in the input dictionary.
        """
        # Discover components: any top-level h_dict entry whose value is a dict
        # containing a "component_type" key is treated as a plant component.
        # This allows user-chosen instance names (e.g. "battery_unit_1") while
        # remaining backward compatible with conventional names (e.g. "battery").
        self.component_names = [
            key for key, val in h_dict.items() if isinstance(val, dict) and "component_type" in val
        ]

        # Add in the number of components
        self.n_components = len(self.component_names)

        # If there are no components, raise an error
        if self.n_components == 0:
            raise Exception("No plant components found in input file")

        # Collect the component objects
        self.component_objects = {}
        for component_name in self.component_names:
            self.component_objects[component_name] = self.get_plant_component(
                component_name, h_dict
            )

        # Determine generator names from component_category after instantiation
        self.generator_names = [
            name
            for name, obj in self.component_objects.items()
            if obj.component_category == "generator"
        ]

    def add_plant_metadata_to_h_dict(self, h_dict):
        """Add plant component metadata to the h_dict.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Updated dictionary with plant component metadata.
        """
        # Add component metadata to h_dict
        h_dict["component_names"] = self.component_names
        h_dict["generator_names"] = self.generator_names
        h_dict["n_components"] = self.n_components

        for component_name in self.component_names:
            h_dict = self.component_objects[component_name].get_initial_conditions_and_meta_data(
                h_dict
            )

        # Add the plant level outputs to the h_dict
        h_dict = self.compute_plant_level_outputs(h_dict)

        return h_dict

    def get_plant_component(self, component_name, h_dict):
        """Create and return a plant component object based on the specified type.

        Args:
            component_name (str): Name of the plant component to create.
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            object: An instance of the appropriate plant component class.

        Raises:
            Exception: If the component_type is not recognized.
        """
        component_type = h_dict[component_name]["component_type"]

        cls = COMPONENT_REGISTRY.get(component_type)
        if cls is None:
            raise ValueError(
                f"Unknown component_type '{component_type}' for component '{component_name}'. "
                f"Available types: {sorted(COMPONENT_REGISTRY)}"
            )
        return cls(h_dict, component_name)

    def step(self, h_dict):
        """Execute one simulation step for all plant components.

        Args:
            h_dict (dict): Dictionary containing current simulation state.

        Returns:
            dict: Updated simulation dictionary with new component states and plant-level outputs.
        """
        # Collect the component objects
        for component_name in self.component_names:
            is_storage = self.component_objects[component_name].component_category == "storage"

            # Storage sign convention: negate setpoint before step, restore after
            if is_storage:
                h_dict[component_name]["power_setpoint"] = -h_dict[component_name]["power_setpoint"]

            # Update h_dict by calling the step method of each component object
            h_dict = self.component_objects[component_name].step(h_dict)

            if is_storage:
                h_dict[component_name]["power_setpoint"] = -h_dict[component_name]["power_setpoint"]
                h_dict[component_name]["power"] = -h_dict[component_name]["power"]

        # Update the plant level outputs
        self.compute_plant_level_outputs(h_dict)

        # Return the updated h_dict
        return h_dict

    def compute_plant_level_outputs(self, h_dict):
        """Compute plant-level outputs by aggregating individual component results.

        Args:
            h_dict (dict): Dictionary containing simulation state with component power outputs.
        """
        # The plant power is the sum of all the component outputs
        h_dict["plant"]["power"] = np.sum(
            [h_dict[component_name]["power"] for component_name in self.component_names]
        )

        # The locally generated power is the sum of all the generator outputs
        # (Excludes battery and electrolyzer outputs)
        h_dict["plant"]["locally_generated_power"] = np.sum(
            [h_dict[generator_name]["power"] for generator_name in self.generator_names]
        )

        return h_dict

    def close_logging(self):
        """Close all loggers for all plant component objects.

        Iterates through all plant component objects and calls their close_logging method
        if it exists, ensuring proper cleanup of logging resources.
        """
        for component in self.component_objects.values():
            if hasattr(component, "close_logging"):
                component.close_logging()
