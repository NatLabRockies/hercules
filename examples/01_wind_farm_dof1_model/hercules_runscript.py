from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import prepare_output_directory

prepare_output_directory()

# Initialize the Hercules model
hmodel = HerculesModel("hercules_input.yaml")


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
        self.h_dict = h_dict

    def step(self, h_dict):
        """Execute one control step.

        Args:
            h_dict (dict): The hercules input dictionary.

        Returns:
            dict: The updated hercules input dictionary.
        """
        # Set deratings to full rating
        for t_idx in range(h_dict["wind_farm"]["n_turbines"]):
            h_dict["wind_farm"][f"derating_{t_idx:03d}"] = 5000

        # Lower t0 derating every other 100 seconds
        if h_dict["time"] % 200 < 100:
            h_dict["wind_farm"]["derating_000"] = 500
        return h_dict


# Instantiate the controller and assign to the Hercules model
hmodel.assign_controller(ControllerToggleTurbine000(hmodel.h_dict))

# Run the simulation
hmodel.run()

hmodel.logger.info("Process completed successfully")
