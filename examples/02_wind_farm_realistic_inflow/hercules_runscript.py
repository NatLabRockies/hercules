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
class ControllerToggleTurbine000:
    """A simple controller that toggles the derating of turbine 000 every other 100 seconds.

    This controller sets all turbines to full rating (5000) and then lowers
    the derating of turbine 000 to 500 every other 100 seconds.
    """

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.
        """
        pass

    def step(self, h_dict):
        """Execute one control step.

        Args:
            h_dict (dict): The hercules input dictionary.

        Returns:
            dict: The updated hercules input dictionary.
        """
        # Set deratings to full rating
        h_dict["wind_farm"]["turbine_power_setpoints"] = 5000 * np.ones(
            h_dict["wind_farm"]["n_turbines"]
        )

        # Lower t0 derating to 500 every other 100 seconds
        if h_dict["time"] % 200 < 100:
            h_dict["wind_farm"]["turbine_power_setpoints"][0] = 500

        return h_dict


# Initialize and run the Hercules model
hmodel = HerculesModel(input_file, ControllerToggleTurbine000)

# Run the simulation
hmodel.enter_execution()

hmodel.logger.info("Process completed successfully")
