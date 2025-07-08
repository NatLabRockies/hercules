import numpy as np

from hercules.python_simulators.electrolyzer_plant import ElectrolyzerPlant
from hercules.python_simulators.lib import LIB
from hercules.python_simulators.simple_battery import SimpleBattery
from hercules.python_simulators.simple_solar import SimpleSolar
from hercules.python_simulators.solar_pysam import SolarPySAM
from hercules.python_simulators.wind_sim_long_term import WindSimLongTerm
from hercules.utilities import get_available_generator_names, get_available_py_sim_names


class PySims:
    """Manages Python-based simulation components for the Hercules emulator.

    This class handles the initialization, execution, and coordination of various
    Python simulation components including wind farms, solar panels, batteries,
    and electrolyzers. It also computes plant-level outputs by aggregating
    individual component results.
    """

    def __init__(self, h_dict):
        """Initialize the Python simulators manager.

        Args:
            h_dict (dict): Dictionary containing simulation parameters and
                configuration for all Python simulators.

        Raises:
            Exception: If no Python simulators are found in the input dictionary.
        """
        # get a list of possible py_sim
        all_py_sim_names = get_available_py_sim_names()

        # get a list of possible generator names
        all_generator_names = get_available_generator_names()

        # Make a list of py_sim names that are in the h_dict
        h_dict["py_sim_names"] = [
            py_sim_name for py_sim_name in all_py_sim_names if py_sim_name in h_dict
        ]

        # Make a list of generator names that are in the h_dict
        h_dict["generator_names"] = [
            generator_name for generator_name in all_generator_names if generator_name in h_dict
        ]

        # Add in the number of py_sims
        h_dict["n_py_sim"] = len(h_dict["py_sim_names"])

        # If there are no py_sims, raise an error
        if h_dict["n_py_sim"] == 0:
            raise Exception("No py_sims found in input file")

        # Save the py_sim names and number of py_sims
        self.py_sim_names = h_dict["py_sim_names"]
        self.n_py_sim = h_dict["n_py_sim"]

        # Save the generator names
        self.generator_names = h_dict["generator_names"]

        # Collect the py_sim objects
        self.py_sim_objects = {}
        for py_sim_name in self.py_sim_names:
            self.py_sim_objects[py_sim_name] = self.get_py_sim(py_sim_name, h_dict)

    def get_py_sim(self, py_sim_name, h_dict):
        """Create and return a Python simulator object based on the specified type.

        Args:
            py_sim_name (str): Name of the Python simulator to create.
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            object: An instance of the appropriate Python simulator class.

        Raises:
            Exception: If the py_sim_type is not recognized.
        """
        if h_dict[py_sim_name]["py_sim_type"] == "WindSimLongTerm":
            return WindSimLongTerm(h_dict)
        if h_dict[py_sim_name]["py_sim_type"] == "SimpleSolar":
            return SimpleSolar(h_dict)

        if h_dict[py_sim_name]["py_sim_type"] == "SolarPySAM":
            return SolarPySAM(h_dict)

        if h_dict[py_sim_name]["py_sim_type"] == "LIB":
            return LIB(h_dict)

        if h_dict[py_sim_name]["py_sim_type"] == "SimpleBattery":
            return SimpleBattery(h_dict)

        if h_dict[py_sim_name]["py_sim_type"] == "ElectrolyzerPlant":
            return ElectrolyzerPlant(h_dict)

        raise Exception("Unknown py_sim_type: ", h_dict[py_sim_name]["py_sim_type"])

    def step(self, h_dict):
        """Execute one simulation step for all Python simulators.

        Updates each Python simulator by calling their step method and then
        computes plant-level outputs by aggregating individual component results.

        Args:
            h_dict (dict): Dictionary containing current simulation state.

        Returns:
            dict: Updated simulation dictionary with new component states and
                plant-level outputs.
        """
        # Collect the py_sim objects
        for py_sim_name in self.py_sim_names:
            # Update h_dict by calling the step method of each py_sim object
            h_dict = self.py_sim_objects[py_sim_name].step(h_dict)

        # Update the plant level outputs
        self.compute_plant_level_outputs(h_dict)

        # Return the updated h_dict
        return h_dict

    def compute_plant_level_outputs(self, h_dict):
        """Compute plant-level outputs by aggregating individual component results.

        Calculates total plant power as the sum of all Python simulator outputs
        and locally generated power as the sum of generator outputs (excluding
        batteries and electrolyzers).

        Args:
            h_dict (dict): Dictionary containing simulation state with component
                power outputs.
        """
        # The plant power is the sum of all the py_sim outputs
        h_dict["plant"]["power"] = np.sum(
            [h_dict[py_sim_name]["power"] for py_sim_name in self.py_sim_names]
        )

        # The locally generated power is the sum of all the generator outputs
        # (Excludes battery and electrolyzer outputs)
        h_dict["plant"]["locally_generated_power"] = np.sum(
            [h_dict[generator_name]["power"] for generator_name in self.generator_names]
        )

    def close_logging(self):
        """Close all loggers for all Python simulator objects.

        Iterates through all Python simulator objects and calls their close_logging
        method if it exists, ensuring proper cleanup of logging resources.
        """
        for py_sim in self.py_sim_objects.values():
            if hasattr(py_sim, 'close_logging'):
                py_sim.close_logging()
