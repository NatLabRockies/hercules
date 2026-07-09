"""Example 08: Multi-unit thermal power plant simulation.

This example demonstrates simple thermal units that follow a reference power setpoint.
The power setpoint schedule is defined in the hercules_input_[unit].yaml file and the
controller follows that schedule. The outputs of the simulation are plotted in the
plot_outputs.py script.
The following thermal power plants are currently available for simulation:
- Combined Cycle Gas Turbine modeled as individual gas and steam turbines
    with a coupling constraint (MU-CCGT)
- Multi-unit thermal plant with 3 OCGTs (MUTP)
"""

from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import prepare_output_directory

prepare_output_directory()

# Initialize the Hercules model
# Select which thermal plant you want to simulate by changing the yaml file
# Currenctly available:
# - hercules_input_mu-ccgt.yaml: Combined Cycle Gas Turbine (CCGT) modeled as
#       individual gas and steam turbines with a coupling constraint
# - hercules_inputs_mutp.yaml: Multi-unit thermal plants with 3 OCGTs

# Version 1: CCGT with coupling constraint
# hmodel = HerculesModel("input_files/hercules_input_mu-ccgt.yaml")
# Version 2: Multi-unit thermal plant with 3 OCGTs
hmodel = HerculesModel("input_files/hercules_input_mutp.yaml")


class ControllerTPP:
    """Controller implementing the thermal power plant schedule
    described in the module docstring."""

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.

        """
        self.component_name = h_dict["component_names"][0]
        self.unit_capacities = [
            h_dict[self.component_name][unit_name]["rated_capacity"]
            for unit_name in h_dict[self.component_name]["unit_names"]
        ]
        self.rated_capacity = sum(self.unit_capacities)
        h_dict[self.component_name]["rated_capacity"] = self.rated_capacity

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

        # If the power setpoint fraction is provided as a list for each unit, use it directly.
        # Otherwise, assume it's a fraction of the total rated capacity and distribute it
        # proportionally to the unit capacities.
        if isinstance(
            h_dict["plant"]["power_setpoint_schedule"]["power_setpoint_fraction"][time_index],
            (list, tuple),
        ):
            power_setpoint_fraction = h_dict["plant"]["power_setpoint_schedule"][
                "power_setpoint_fraction"
            ][time_index]
            power_setpoints = [
                power_setpoint * unit_capacity
                for power_setpoint, unit_capacity in zip(
                    power_setpoint_fraction, self.unit_capacities
                )
            ]
            h_dict[self.component_name]["power_setpoints"] = power_setpoints
        else:
            power_setpoint_fraction = h_dict["plant"]["power_setpoint_schedule"][
                "power_setpoint_fraction"
            ][time_index]
            h_dict[self.component_name]["power_setpoint"] = (
                power_setpoint_fraction * self.rated_capacity
            )

        return h_dict


# Instantiate the controller and assign to the Hercules model
hmodel.assign_controller(ControllerTPP(hmodel.h_dict))

# Run the simulation
hmodel.run()

hmodel.logger.info("Process completed successfully")
