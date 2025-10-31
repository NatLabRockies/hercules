import numpy as np

from hercules.plant_components.battery_lithium_ion import BatteryLithiumIon
from hercules.plant_components.battery_simple import BatterySimple
from hercules.plant_components.electrolyzer_plant import ElectrolyzerPlant
from hercules.plant_components.solar_pysam_pvwatts import SolarPySAMPVWatts
from hercules.plant_components.wind_meso_to_power import Wind_MesoToPower
from hercules.plant_components.wind_meso_to_power_precom_floris import Wind_MesoToPowerPrecomFloris
from hercules.utilities import get_available_component_names, get_available_generator_names


class HybridPlant:
    """Manages hybrid plant components for the Hercules emulator.

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
        # get a list of possible component names
        all_component_names = get_available_component_names()

        # get a list of possible generator names
        all_generator_names = get_available_generator_names()

        # Make a list of component names that are in the h_dict
        self.component_names = [
            component_name for component_name in all_component_names if component_name in h_dict
        ]

        # Make a list of generator names that are in the h_dict
        self.generator_names = [
            generator_name for generator_name in all_generator_names if generator_name in h_dict
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
        if h_dict[component_name]["component_type"] == "Wind_MesoToPower":
            return Wind_MesoToPower(h_dict)

        if h_dict[component_name]["component_type"] == "Wind_MesoToPowerPrecomFloris":
            return Wind_MesoToPowerPrecomFloris(h_dict)

        if h_dict[component_name]["component_type"] == "SolarPySAMPVWatts":
            return SolarPySAMPVWatts(h_dict)

        if h_dict[component_name]["component_type"] == "BatteryLithiumIon":
            return BatteryLithiumIon(h_dict)

        if h_dict[component_name]["component_type"] == "BatterySimple":
            return BatterySimple(h_dict)

        if h_dict[component_name]["component_type"] == "ElectrolyzerPlant":
            return ElectrolyzerPlant(h_dict)

        raise Exception("Unknown component_type: ", h_dict[component_name]["component_type"])

    def step(self, h_dict):
        """Execute one simulation step for all plant components.

        Args:
            h_dict (dict): Dictionary containing current simulation state.

        Returns:
            dict: Updated simulation dictionary with new component states and plant-level outputs.
        """
        # Collect the component objects
        for component_name in self.component_names:
            # If component_name is battery, invert the sign of the power_setpoint
            if component_name == "battery":
                h_dict[component_name]["power_setpoint"] = -h_dict[component_name]["power_setpoint"]

            # Update h_dict by calling the step method of each component object
            h_dict = self.component_objects[component_name].step(h_dict)

            # If component_name is battery, invert the sign of the power_setpoint back
            # And invert the sign of the power output
            if component_name == "battery":
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
