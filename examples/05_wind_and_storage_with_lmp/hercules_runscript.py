from pathlib import Path

import numpy as np
import pandas as pd
from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import ensure_example_inputs_exist, prepare_output_directory

prepare_output_directory()

# Ensure example inputs exist
ensure_example_inputs_exist()

# Generate LMP data file if it doesn't exist
lmp_data_path = Path("external_data_lmp.csv")

print("Generating LMP data file...")
# Create 4 hours of data at 5-minute intervals
# Start time matching the example: 2024-06-24T16:59:08Z
start_time = pd.Timestamp("2024-06-24T16:59:08Z")
# 4 hours = 240 minutes, 5-minute intervals = 49 time points (0, 5, 10, ..., 240)
time_points = pd.date_range(start=start_time, periods=49, freq="5min")

# Create the dataframe
df = pd.DataFrame(
    {
        "time_utc": time_points,
        "lmp_da": np.full(49, 10.0),  # Constant $10
        "lmp_rt": np.linspace(0, 50, 49),  # Ramp from $0 to $50
    }
)

# Save to CSV
df.to_csv(lmp_data_path, index=False)
print(f"Created {lmp_data_path}")

# Initialize the Hercules model
hmodel = HerculesModel("hercules_input.yaml")


# Define an LMP-based battery controller
class ControllerLMPBased:
    """Battery controller that charges/discharges based on real-time LMP prices."""

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.
        """
        self.interconnect_limit = h_dict["plant"]["interconnect_limit"]
        self.charge_threshold = 15.0  # Charge when lmp_rt < $15
        self.discharge_threshold = 35.0  # Discharge when lmp_rt > $35

    def step(self, h_dict):
        """Execute one control step based on LMP prices.

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

        # Get the real-time LMP from external signals
        lmp_rt = h_dict["external_signals"]["lmp_rt"]

        # Battery control based on LMP
        # With hybrid plant sign convention: Positive = discharge, Negative = charge
        if lmp_rt < self.charge_threshold:
            # Low price: charge the battery
            h_dict["battery"]["power_setpoint"] = -10000
        elif lmp_rt > self.discharge_threshold:
            # High price: discharge the battery
            h_dict["battery"]["power_setpoint"] = 10000
        else:
            # Medium price: idle
            h_dict["battery"]["power_setpoint"] = 0

        # Get the limit for battery power
        # Battery power + wind power must be less than the interconnect limit
        battery_power_upper_limit = self.interconnect_limit - wind_farm_power
        battery_power_lower_limit = -1 * self.interconnect_limit - wind_farm_power

        # Clip to respect interconnect limits
        h_dict["battery"]["power_setpoint"] = np.clip(
            h_dict["battery"]["power_setpoint"],
            battery_power_lower_limit,
            battery_power_upper_limit,
        )

        return h_dict


# Assign the controller to the Hercules model
hmodel.assign_controller(ControllerLMPBased(hmodel.h_dict))

# Run the simulation
hmodel.run()

hmodel.logger.info("Process completed successfully")
