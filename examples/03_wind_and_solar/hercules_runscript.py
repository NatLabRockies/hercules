import os
import shutil
import sys

import numpy as np
from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import ensure_example_inputs_exist

# If the output folder exists, delete it
if os.path.exists("outputs"):
    shutil.rmtree("outputs")
os.makedirs("outputs")

# Ensure example inputs exist
ensure_example_inputs_exist()

# If more than one argument is provided raise and error
if len(sys.argv) > 2:
    raise Exception(
        "Usage: python hercules_runscript.py [hercules_input_file] or python hercules_runscript.py"
    )

# If one argument is provided, use it as the input file
if len(sys.argv) == 2:
    input_file = sys.argv[1]
# If no arguments are provided, use the default input file
else:
    input_file = "hercules_input.yaml"


# Define a simple controller that sets all deratings to full rating
# and then sets the derating of turbine 000 to 500, toggling every other 100 seconds.
class ControllerLimitSolar:
    """Limits the solar power to keep the total power below the interconnect limit."""

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.
        """
        self.interconnect_limit = h_dict["plant"]["interconnect_limit"]
        pass

    def step(self, h_dict):
        """Execute one control step.

        Args:
            h_dict (dict): The hercules input dictionary.

        Returns:
            dict: The updated hercules input dictionary.
        """
        # Set wind turbine power setpoints to full rating
        h_dict["wind_farm"]["turbine_power_setpoints"] = 5000 * np.ones(
            h_dict["wind_farm"]["n_turbines"]
        )

        # Get the total wind farm power
        wind_farm_power = h_dict["wind_farm"]["power"]

        # Get the limit for solar power
        solar_power_limit = max(0, self.interconnect_limit - wind_farm_power)

        # Set the solar power limit
        h_dict["solar_farm"]["power_setpoint"] = solar_power_limit

        return h_dict


# Initialize and run the Hercules model
hmodel = HerculesModel(input_file, ControllerLimitSolar)

# Run the simulation
hmodel.enter_execution()

hmodel.logger.info("Process completed successfully")
