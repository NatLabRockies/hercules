"""Example 09: Linear Generator Simulation.

This example demonstrates a Mainspring linear generator that:
- Starts ON at rated capacity (250 kW)
- At 10 minutes, receives a shutdown command and quickly ramps to off
  (fast ramp rate: 120%/min, effectively instantaneous at 1-min time steps)
- At 20 minutes, receives an ON command — rejected because min_down_time
  (60 min) is not yet satisfied
- At 71 minutes, min_down_time is satisfied; hot start sequence begins
- At ~78 minutes, hot start completes and generator ramps to full power
- At 90 minutes, reduces to 50% of rated capacity (125 kW)
- At 120 minutes, reduces to 20% of rated capacity (50 kW) — note this is
  below the minimum stable load of an OCGT, but the linear generator has
  no minimum stable load constraint
- At 180 minutes, shuts down
- Simulation runs for 4 hours total with 1-minute time steps

Key behaviors demonstrated:
- Fast ramp rate: power changes are nearly instantaneous
- No minimum stable load: can operate at any fraction of rated capacity
- Relatively flat efficiency: ~41% HHV net efficiency across most of the load range
- Minimum down time: ON command at 20 min is deferred until 60-min
  down time is satisfied
"""

from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import prepare_output_directory

prepare_output_directory()

# Initialize the Hercules model
hmodel = HerculesModel("hercules_input.yaml")


class ControllerLinearGenerator:
    """Controller implementing the linear generator schedule described in the module docstring."""

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.
        """
        self.rated_capacity = h_dict["linear_generator"]["rated_capacity"]

    def step(self, h_dict):
        """Execute one control step.

        Args:
            h_dict (dict): The hercules input dictionary.

        Returns:
            dict: The updated hercules input dictionary.
        """
        current_time = h_dict["time"]

        if current_time < 10 * 60:  # 0–10 minutes: run at full capacity
            power_setpoint = self.rated_capacity
        elif current_time < 90 * 60:  # 10–90 minutes: command ON at full capacity
            # From t=10 min the generator shuts down; the ON command issued here
            # (after t=10 min) will be deferred by min_down_time until ~71 min
            power_setpoint = self.rated_capacity
        elif current_time < 120 * 60:  # 90–120 minutes: reduce to 50%
            power_setpoint = 0.5 * self.rated_capacity
        elif current_time < 180 * 60:  # 120–180 minutes: reduce to 20%
            power_setpoint = 0.2 * self.rated_capacity
        else:  # After 180 minutes: shut down
            power_setpoint = 0.0

        # Issue a shutdown at t=10 min by setting setpoint to 0 for that window
        if 10 * 60 <= current_time < 20 * 60:
            power_setpoint = 0.0

        h_dict["linear_generator"]["power_setpoint"] = power_setpoint

        return h_dict


# Instantiate the controller and assign to the Hercules model
hmodel.assign_controller(ControllerLinearGenerator(hmodel.h_dict))

# Run the simulation
hmodel.run()

hmodel.logger.info("Process completed successfully")
