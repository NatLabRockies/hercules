import numpy as np
from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import ensure_example_inputs_exist, prepare_output_directory

prepare_output_directory()

# Ensure example inputs exist
ensure_example_inputs_exist()

# Initialize the Hercules model
hmodel = HerculesModel("hercules_input.yaml")


# Define a simple controller that sets all power setpoints to full rating
class ControllerFullRating:
    """A simple controller that sets all turbines to full rating.

    This controller is appropriate for the direct wake model where
    wake effects are already included in the input wind data.
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
        # Set all turbines to full rating
        h_dict["wind_farm"]["turbine_power_setpoints"] = 5000 * np.ones(
            h_dict["wind_farm"]["n_turbines"]
        )

        return h_dict


# Assign the controller to the Hercules model
hmodel.assign_controller(ControllerFullRating(hmodel.h_dict))

# Run the simulation
hmodel.run()

hmodel.logger.info("Process completed successfully")
