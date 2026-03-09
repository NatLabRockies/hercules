"""Example 10: Combined Cycle Gas Turbine (CCGT) simulation.

This example demonstrates a simple combined cycle gas turbine (CCGT) that:
- Starts on at rated capacity (100 MW)
- At 10 minutes, receives a shutdown command and begins ramping down
- At ~20 minutes, reaches 0 MW and transitions to off
- At 40 minutes, receives a turn-on command with a setpoint of 100% of rated capacity
- At ~80 minutes, 1 hour down-time minimum is reached and the turbine begins hot starting
- At ~87 minutes, hot start completes, continues ramping up to 100% of rated capacity
- At 120 minutes, receives a command to reduce power to 50% of rated capacity
- At 180 minutes, receives a command to reduce power to 10% of rated capacity
        (note this is below the minimum stable load)
- At 210 minutes, receives a command to increase power to 100% of rated capacity
- At 240 minutes (4 hours), receives a shutdown command
- Simulation runs for 6 hours total with 1 minute time steps
"""

from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import prepare_output_directory

prepare_output_directory()

# Initialize the Hercules model
hmodel = HerculesModel("hercules_input.yaml")


class ControllerCCGT:
    """Controller implementing the CCGT schedule described in the module docstring."""

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.

        """
        self.rated_capacity = 100000  # Hardcode for now. Likely need to get from

    def step(self, h_dict):
        """Execute one control step.

        Args:
            h_dict (dict): The hercules input dictionary.

        Returns:
            dict: The updated hercules input dictionary.

        """
        current_time = h_dict["time"]

        # Determine power setpoint based on time
        if current_time < 10 * 60:  # 10 minutes in seconds
            # Before 10 minutes: run at full capacity
            power_setpoint = self.rated_capacity
        elif current_time < 60 * 60:  # 60 minutes in seconds
            # Between 10 and 60 minutes: shut down
            power_setpoint = 0.0
        elif current_time < 260 * 60:  # 260 minutes in seconds
            # Between 60 and 260 minutes: signal to run at full capacity
            power_setpoint = self.rated_capacity
        elif current_time < 360 * 60:  # 360 minutes in seconds
            # Between 260 and 360 minutes: reduce power to 50% of rated capacity
            power_setpoint = 0.5 * self.rated_capacity
        elif current_time < 480 * 60:  # 480 minutes in seconds
            # Between 360 and 480 minutes: reduce power to 10% of rated capacity
            power_setpoint = 0.1 * self.rated_capacity
        elif current_time < 540 * 60:  # 540 minutes in seconds
            # Between 480 and 540 minutes: increase power to 100% of rated capacity
            power_setpoint = self.rated_capacity
        else:
            # After 540 minutes: shut down
            power_setpoint = 0.0

        h_dict["combined_cycle_plant"]["power_setpoint"] = power_setpoint

        return h_dict

# Instantiate the controller and assign to the Hercules model
hmodel.assign_controller(ControllerCCGT(hmodel.h_dict))

# Run the simulation
hmodel.run()

hmodel.logger.info("Process completed successfully")
