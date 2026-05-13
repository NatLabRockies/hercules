"""Example 07: Thermal power plant simulation.

This example demonstrates simple thermal units that follow a reference power setpoint.
The power setpoint schedule is defined in the hercules_input_[unit].yaml file and the
controller follows that schedule. The outputs of the simulation are plotted in the
plot_outputs.py script.
The following thermal power plants are currently available for simulation:
- Open Cycle Gas Turbine (OCGT)
- Steam Turbine (ST)
"""

from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import prepare_output_directory

prepare_output_directory()

# Initialize the Hercules model
# Select which thermal plant you want to simulate by changing the yaml file
# Currenctly available:
# - hercules_input_hcst.yaml: Steam turbine (ST) using hard coal as fuel
# - hercules_input_ocgt.yaml: Open Cycle Gas Turbine (OCGT)
hmodel = HerculesModel("input_files/hercules_input_ocgt.yaml")


class ControllerPassthrough:
    """Controller implementing the turbine schedule described in the module docstring."""

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.

        """
        self.component_name = h_dict["component_names"][0]
        self.rated_capacity = h_dict[self.component_name]["rated_capacity"]

    def step(self, h_dict):
        """Execute one control step.

        Args:
            h_dict (dict): The hercules input dictionary.

        Returns:
            dict: The updated hercules input dictionary.

        """
        current_time = h_dict["time"]

        # Determine power setpoint based on schedule provided in yaml file
        time_index = (
            sum(current_time >= t for t in h_dict["plant"]["power_setpoint_schedule"]["time"]) - 1
        )
        power_setpoint = (
            h_dict["plant"]["power_setpoint_schedule"]["power_setpoint_fraction"][time_index]
            * self.rated_capacity
        )

        h_dict[self.component_name]["power_setpoint"] = power_setpoint

        return h_dict


# Instantiate the controller and assign to the Hercules model
hmodel.assign_controller(ControllerPassthrough(hmodel.h_dict))

# Run the simulation
hmodel.run()

hmodel.logger.info("Process completed successfully")
