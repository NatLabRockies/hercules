"""Example 07: Thermal power plant simulation.

This example demonstrates simple thermal units that follow a reference power setpoint. 
The power setpoint schedule is defined in the hercules_input_[unit].yaml file and the 
controller follows that schedule. The outputs of the simulation are plotted in the 
plot_outputs.py script.
The following thermal power plants are currently available for simulation:
- Hard Coal Steam Turbine (HCST)
- Open Cycle Gas Turbine (OCGT)
- Steam Turbine (ST)
- Combined Cycle Gas Turbine modeled as individual gas and steam turbines with a coupling constraint (MU-CCGT)
- Multi-unit thermal plant with 2 OCGTs (MUTP)
"""

from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import prepare_output_directory

prepare_output_directory()

# Initialize the Hercules model
# Select which thermal plant you want to simulate by changing the yaml file
# Currenctly available:
# - hercules_input_hcst.yaml: Hard coal steam turbine (HCST)
# - hercules_input_ocgt.yaml: Open Cycle Gas Turbine (OCGT)
# - hercules_input_st.yaml: Steam Turbine (ST)
# - hercules_input_mu-ccgt.yaml: Combined Cycle Gas Turbine (CCGT) modeled as 
#       individual gas and steam turbines with a coupling constraint
# - hercules_inputs_mutp.yaml: Multi-unit thermal plants with 2 OCGTs
hmodel = HerculesModel("input_files/hercules_input_hcst.yaml")

class ControllerOCGT:
    """Controller implementing the OCGT schedule described in the module docstring."""

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
        time_index = sum(current_time >= t for t in h_dict["plant"]["power_setpoint_schedule"]["time"]) - 1
        power_setpoint = h_dict["plant"]["power_setpoint_schedule"]["power_setpoint_fraction"][time_index] * self.rated_capacity

        h_dict[self.component_name]["power_setpoint"] = power_setpoint

        return h_dict


# Instantiate the controller and assign to the Hercules model
hmodel.assign_controller(ControllerOCGT(hmodel.h_dict))

# Run the simulation
hmodel.run()

hmodel.logger.info("Process completed successfully")
