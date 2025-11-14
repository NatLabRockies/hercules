import numpy as np
from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import ensure_example_inputs_exist, prepare_output_directory
from whoc.controllers import (
    HydrogenPlantController,
    WindFarmPowerTrackingController,
)
from whoc.interfaces import HerculesV2Interface

prepare_output_directory()

# Ensure example inputs exist
ensure_example_inputs_exist()

# Initialize the Hercules model
hmodel = HerculesModel("hercules_input.yaml")


# Define a simple controller that sets all deratings to full rating
# and then sets the derating of turbine 000 to 500, toggling every other 100 seconds.
class ControllerLimitSolar:
    """Limits the solar power to keep the total power below the interconnect limit."""

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.
        """
        self.interconnect_limit = h_dict["plant"]["interconnect_limit"]
        pass

    def step(self, h_dict):
        """Execute one control step.

        Args:
            h_dict (dict): The hercules input dictionary.

        Returns:
            dict: The updated hercules input dictionary.
        """
        # Set wind turbine power setpoints to full rating
        h_dict["wind_farm"]["turbine_power_setpoints"] = 5000 * np.ones(
            h_dict["wind_farm"]["n_turbines"]
        )

        # Get the total wind farm power
        wind_farm_power = h_dict["wind_farm"]["power"]

        # Charge or discharge the battery, reversing every other hour
        # With hybrid plant sign convention: Positive = discharge, Negative = charge
        if h_dict["time"] % 3600 < 1800:
            h_dict["battery"]["power_setpoint"] = 10000  # Discharge the battery
        else:
            h_dict["battery"]["power_setpoint"] = -10000  # Charge the battery

        # Get the limit for battery power
        # Battery power + wind power must be less than the interconnect limit
        battery_power_upper_limit = self.interconnect_limit - wind_farm_power
        battery_power_lower_limit = -1 * self.interconnect_limit - wind_farm_power

        # Set the solar power limit
        h_dict["battery"]["power_setpoint"] = np.clip(
            h_dict["battery"]["power_setpoint"],
            battery_power_lower_limit,
            battery_power_upper_limit,
        )

        return h_dict

# Establish controllers based on options
interface = HerculesV2Interface(hmodel.h_dict)

print("Setting up controller.")
wind_controller = WindFarmPowerTrackingController(interface, hmodel.h_dict)
# solar_controller = (
#     SolarPassthroughController(interface, hmodel.h_dict) if include_solar
#     else None
# )
# battery_controller = (
#     BatteryPassthroughController(interface, hmodel.h_dict) if include_battery
#     else None
# )
controller = HydrogenPlantController(
    interface,
    hmodel.h_dict,
    generator_controller=wind_controller
)

# Assign the controller to the Hercules model
hmodel.assign_controller(controller)
print("Controller assigned.")

# Run the simulation
hmodel.run()

hmodel.logger.info("Process completed successfully")
