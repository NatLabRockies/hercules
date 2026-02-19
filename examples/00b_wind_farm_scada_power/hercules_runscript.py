from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import ensure_example_inputs_exist, prepare_output_directory

prepare_output_directory()

# Ensure example inputs exist
ensure_example_inputs_exist()

# Initialize the Hercules model
hmodel = HerculesModel("hercules_input.yaml")


# Define a controller that does nothing
class ControllerPassThrough:
    """A place holder controller that does nothing."""

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
        # Simply return the unmodified h_dict
        return h_dict


# Instantiate the controller and assign to the Hercules model
hmodel.assign_controller(ControllerPassThrough(hmodel.h_dict))

# Run the simulation
hmodel.run()

hmodel.logger.info("Process completed successfully")
