"""Example 08: Hard Coal Steam Turbine (HCST) simulation.

This example demonstrates a simple hard coal steam turbine (HCST) that:
- Starts on at rated capacity
- Receives a shutdown command and begins ramping down
- Transitions to off
- Receives a turn-on command with a setpoint of 100% of rated capacity
- Minimum down-time requirement is reached and the turbine begins ramping up
- Ramps up to 100% of rated capacity
- Receives a command to reduce power to 50% of rated capacity
- Receives a command to reduce power to 10% of rated capacity
        (note this is below the minimum stable load)
- Receives a command to increase power to 100% of rated capacity
- Receives a shutdown command
- Simulation runs for 10 days total with 1 minute time steps
"""

from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import prepare_output_directory

prepare_output_directory()

# Initialize the Hercules model
hmodel = HerculesModel("hercules_input.yaml")


class ControllerHCST:
    """Controller implementing the HCST schedule described in the module docstring."""

    def __init__(self, h_dict, component_name="hard_coal_steam_turbine"):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.

        """
        self.component_name = component_name
        self.rated_capacity = h_dict[self.component_name]["rated_capacity"]

        simulation_length = h_dict["endtime_utc"] - h_dict["starttime_utc"]
        self.total_simulation_time = simulation_length.total_seconds()

    def step(self, h_dict):
        """Execute one control step.
        This controller is scaled by the total simulation time, pulled from the h_dict
        This preserves the relative distance between control actions, but changes the
            simulation times that they are applied.

        Args:
            h_dict (dict): The hercules input dictionary.

        Returns:
            dict: The updated hercules input dictionary.

        """
        current_time = h_dict["time"]

        # Determine power setpoint based on time
        if current_time < 0.05 * self.total_simulation_time:
            # First 5% of simulation time, run at full capacity
            power_setpoint = self.rated_capacity
        elif current_time < 0.15 * self.total_simulation_time:
            # Between 5% and 15% of simulation time: shut down
            power_setpoint = 0.0
        elif current_time < 0.45 * self.total_simulation_time:
            # Between 15% and 45% of simulation time: signal to run at full capacity
            power_setpoint = self.rated_capacity
        elif current_time < 0.65 * self.total_simulation_time:
            # Between 45% and 65% of simulation time: reduce power to 50% of rated capacity
            power_setpoint = 0.5 * self.rated_capacity
        elif current_time < 0.75 * self.total_simulation_time:
            # Between 65% and 75% of simulation time: reduce power to 10% of rated capacity
            power_setpoint = 0.1 * self.rated_capacity
        elif current_time < 0.9 * self.total_simulation_time:  #
            # Between 75% and 90% of simulation time: increase power to 100% of rated capacity
            power_setpoint = self.rated_capacity
        else:
            # After 90% of simulation time: shut down
            power_setpoint = 0.0

        h_dict[self.component_name]["power_setpoint"] = power_setpoint

        return h_dict


# Instantiate the controller and assign to the Hercules model
hmodel.assign_controller(ControllerHCST(hmodel.h_dict))

# Run the simulation
hmodel.run()

hmodel.logger.info("Process completed successfully")
