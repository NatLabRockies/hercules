"""Example 09: Multiunit Thermal Plant

This example demonstrates a thermal power plant constructed from two 50 MW OCGT units.
The power setpoints are split unequally between the two units to demonstrate the ability of the
model to specify setpoints of individual units.
"""

from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import prepare_output_directory

prepare_output_directory()


# Declare the open loop control setpoint sequence used for demonstration.
class OpenLoopController:
    """Controller implementing the unit power setpoints in open loop."""

    def __init__(self, h_dict):
        # Access total rated capacity from h_dict, as well as capacities of individual units
        self.rated_capacity = h_dict["thermal_power_plant"]["rated_capacity"]
        self.unit_1_capacity = h_dict["thermal_power_plant"]["OCGT1"]["rated_capacity"]
        self.unit_2_capacity = h_dict["thermal_power_plant"]["OCGT2"]["rated_capacity"]
        self.unit_3_capacity = h_dict["thermal_power_plant"]["OCGT3"]["rated_capacity"]

    def step(self, h_dict):
        current_time = h_dict["time"]

        # Determine power setpoint based on time
        if current_time < 10 * 60:  # 10 minutes in seconds
            # Before 10 minutes: run all three units at full capacity
            self.power_setpoint_1 = self.unit_1_capacity
            self.power_setpoint_2 = self.unit_2_capacity
            self.power_setpoint_3 = self.unit_3_capacity
        elif current_time < 20 * 60:  # 20 minutes in seconds
            # Between 10 and 20 minutes: shut down unit 1, leave units 2 & 3
            self.power_setpoint_1 = 0.0
        elif current_time < 40 * 60:  # 40 minutes in seconds
            # Shut down units 2 & 3
            self.power_setpoint_2 = 0.0
            self.power_setpoint_3 = 0.0
        elif current_time < 120 * 60:  # 120 minutes in seconds
            # Between 40 and 120 minutes: signal to run at full capacity
            self.power_setpoint_1 = self.unit_1_capacity
            self.power_setpoint_2 = self.unit_2_capacity
            self.power_setpoint_3 = self.unit_3_capacity
        elif current_time < 180 * 60:  # 180 minutes in seconds
            # Between 120 and 180 minutes: reduce power of unit 1 to 50% of rated capacity
            self.power_setpoint_1 = 0.5 * self.unit_1_capacity
        elif current_time < 210 * 60:  # 210 minutes in seconds
            # Between 180 and 210 minutes: reduce power of unit 1 to 10% of rated capacity
            self.power_setpoint_1 = 0.1 * self.unit_1_capacity
        elif current_time < 240 * 60:  # 240 minutes in seconds
            # Between 210 and 240 minutes: move both units to 50% of rated capacity
            self.power_setpoint_1 = 0.5 * self.unit_1_capacity
            self.power_setpoint_2 = 0.5 * self.unit_2_capacity
            self.power_setpoint_3 = 0.5 * self.unit_3_capacity
        else:
            # After 240 minutes: shut down
            self.power_setpoint_1 = 0.0
            self.power_setpoint_2 = 0.0
            self.power_setpoint_3 = 0.0

        # Update the h_dict with the power setpoints for each unit and return
        h_dict["thermal_power_plant"]["power_setpoints"] = [
            self.power_setpoint_1,
            self.power_setpoint_2,
            self.power_setpoint_3,
        ]

        return h_dict


# Runscript
if __name__ == "__main__":
    # Initialize the Hercules model
    hmodel = HerculesModel("hercules_input.yaml")

    # Instantiate the controller and assign to the Hercules model
    hmodel.assign_controller(OpenLoopController(hmodel.h_dict))

    # Run the simulation
    hmodel.run()

    hmodel.logger.info("Process completed successfully")
