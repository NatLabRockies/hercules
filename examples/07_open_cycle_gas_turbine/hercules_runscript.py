"""
Example 07: Open Cycle Gas Turbine (OCGT) simulation.

This example demonstrates a simple open cycle gas turbine (OCGT) and a combined
    cycle turbine (CCGT) in a simulation that compares their performance using the
    following schedule of commands:
- Starts on at rated capacity (100 MW)
- At 10 minutes, receives a shutdown command and begins ramping down
- At 60 minutes, receives a turn-on command with a setpoint of 100% of rated capacity
- At 260 minutes, receives a command to reduce power to 50% of rated capacity
- At 360 minutes, receives a command to reduce power to 10% of rated capacity
        (note this is below the minimum stable load)
- At 480 minutes, receives a command to increase power to 100% of rated capacity
- At 540 minutes (9 hours), receives a shutdown command
- Simulation runs for 10 hours total with 1 minute time steps
"""

from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import prepare_output_directory

prepare_output_directory()

# Initialize the Hercules model
hmodel = HerculesModel("hercules_input_ocgt.yaml")


class OpenLoopController:
    """Controller implementing the OCGT schedule described in the module docstring."""

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.

        """
        # TODO: Improve this once component-type reconfigured
        if "open_cycle_gas_turbine" in h_dict:
            self.rated_capacity = h_dict["open_cycle_gas_turbine"]["rated_capacity"]
        elif "combined_cycle_gas_turbine" in h_dict:
            self.rated_capacity = h_dict["combined_cycle_gas_turbine"]["rated_capacity"]
        else:
            raise ValueError("No gas turbine component found in input dictionary.")

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

        # TODO: Improve this once component-type reconfigured
        if "open_cycle_gas_turbine" in h_dict:
            h_dict["open_cycle_gas_turbine"]["power_setpoint"] = power_setpoint
        elif "combined_cycle_gas_turbine" in h_dict:
            h_dict["combined_cycle_gas_turbine"]["power_setpoint"] = power_setpoint

        return h_dict


# Instantiate the controller and assign to the Hercules model
hmodel.assign_controller(OpenLoopController(hmodel.h_dict))

# Run the simulation
print("Running OCGT simulation...")
hmodel.run()

hmodel.logger.info("Process completed successfully")

# Initialize the Hercules model
hmodel = HerculesModel("hercules_input_ccgt.yaml")


# Instantiate the controller and assign to the Hercules model
hmodel.assign_controller(OpenLoopController(hmodel.h_dict))

# Run the simulation
print("Running CCGT simulation...")
hmodel.run()

hmodel.logger.info("Process completed successfully")
