import numpy as np

from hercules.component_registry import COMPONENT_REGISTRY

# from hercules.plant_components.battery_lithium_ion import BatteryLithiumIon
# from hercules.plant_components.combined_cycle_plant import CombinedCyclePlant
# from hercules.plant_components.electrolyzer_plant import ElectrolyzerPlant
# from hercules.plant_components.open_cycle_gas_turbine import OpenCycleGasTurbine
# from hercules.plant_components.power_playback import PowerPlayback
# from hercules.plant_components.solar_pysam_pvwatts import SolarPySAMPVWatts
# from hercules.plant_components.steam_turbine import SteamTurbine
# from hercules.plant_components.thermal_plant import ThermalPlant
# from hercules.plant_components.wind_farm import WindFarm
# from hercules.plant_components.wind_farm_scada_power import WindFarmSCADAPower

# # Registry mapping component_type strings to their classes.
# # Add new component types here to make them discoverable by HybridPlant.
# COMPONENT_REGISTRY = {
#     "WindFarm": WindFarm,
#     "WindFarmSCADAPower": WindFarmSCADAPower,
#     "SolarPySAMPVWatts": SolarPySAMPVWatts,
#     "BatteryLithiumIon": BatteryLithiumIon,
#     "ElectrolyzerPlant": ElectrolyzerPlant,
#     "OpenCycleGasTurbine": OpenCycleGasTurbine,
#     "ThermalPlant": ThermalPlant,
#     "PowerPlayback": PowerPlayback,
#     "SteamTurbine": SteamTurbine,
#     "CombinedCyclePlant": CombinedCyclePlant,
# }

# # Derived from registry keys for validation in utilities.py
# VALID_COMPONENT_TYPES = tuple(COMPONENT_REGISTRY.keys())


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
        self.component_count = len(self.component_names)

        # If there are no components, raise an error
        if self.component_count == 0:
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

        self.eta_bus_to_poi = h_dict["plant"].get("eta_bus_to_poi", 1.0)

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
        h_dict["component_count"] = self.component_count
        h_dict["plant"]["eta_bus_to_poi"] = self.eta_bus_to_poi

        for component_name in self.component_names:
            component = self.component_objects[component_name]
            h_dict = component.get_initial_conditions_and_meta_data(h_dict)
            for key in component.consumer_sign_outputs:
                if key in h_dict[component_name]:
                    h_dict[component_name][key] = -h_dict[component_name][key]

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
        for component_name in self.component_names:
            component = self.component_objects[component_name]
            if component.consumer_sign_outputs:
                h_dict = self._step_consumer_sign(component, h_dict)
            else:
                h_dict = component.step(h_dict)

        # Update the plant level outputs
        self.compute_plant_level_outputs(h_dict)

        # Return the updated h_dict
        return h_dict

    def _step_consumer_sign(self, component, h_dict):
        """Step a storage or load component that uses the consumer sign convention internally.

        The component sees a copy of its h_dict section with ``power_setpoint`` negated, so
        the controller-owned setpoint is never modified. Outputs listed in
        ``component.consumer_sign_outputs`` are negated back to the generator convention.

        Args:
            component (ComponentBase): Component to step.
            h_dict (dict): Dictionary containing current simulation state.

        Returns:
            dict: Updated simulation dictionary.
        """
        name = component.component_name
        external = h_dict[name]
        internal = dict(external)
        if "power_setpoint" in external:
            internal["power_setpoint"] = -external["power_setpoint"]
        h_dict[name] = internal

        h_dict = component.step(h_dict)

        internal = h_dict[name]
        for key in component.consumer_sign_outputs:
            internal[key] = -internal[key]
        internal.pop("power_setpoint", None)
        external.update(internal)
        h_dict[name] = external
        return h_dict

    def compute_plant_level_outputs(self, h_dict):
        """Compute plant-level outputs by aggregating individual component results.

        Args:
            h_dict (dict): Dictionary containing simulation state with component power outputs.
        """
        power_bus = np.sum(
            [h_dict[component_name]["power"] for component_name in self.component_names]
        )
        h_dict["plant"]["power_bus"] = power_bus

        # Bus-to-POI losses always reduce what arrives at the far end
        if power_bus >= 0:
            h_dict["plant"]["power_export"] = self.eta_bus_to_poi * power_bus
        else:
            h_dict["plant"]["power_export"] = power_bus / self.eta_bus_to_poi

        # Excludes storage and load components
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
