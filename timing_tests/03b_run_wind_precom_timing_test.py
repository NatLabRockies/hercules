"""Run wind timing test with power curtailment controller.

This script runs a wind farm simulation using the generated wind input data
and measures the execution time. It includes a simple controller that curtails
power to 20 MW halfway through the simulation (at 500 minutes).

Unlike 03_run_wind_timing_test.py, this script uses the precomputed FLORIS model.
"""

import os
import shutil
import time

import matplotlib.pyplot as plt
import numpy as np
from hercules.emulator import Emulator
from hercules.hybrid_plant import HybridPlant
from hercules.utilities import load_hercules_input, setup_logging

from utilities import record_timing_result

PLOT_OUTPUT = True


class PowerCurtailmentController:
    """A simple controller that curtails power to 20 MW halfway through simulation.

    This controller sets all turbines to full rating initially, then curtails
    power to 20 MW at 500 minutes (halfway through the 1000-minute simulation).
    """

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.
        """
        self.n_turbines = h_dict["wind_farm"]["n_turbines"]
        self.curtailment_time = 10 * 60 * 60  # seconds
        self.turbine_curtail_power = 1000  # kW

    def step(self, h_dict):
        """Execute one control step.

        Args:
            h_dict (dict): The hercules input dictionary.

        Returns:
            dict: The updated hercules input dictionary.
        """
        current_time = h_dict["time"]

        # Set all turbines to full rating initially
        h_dict["wind_farm"]["turbine_power_setpoints"] = 5000 * np.ones(
            h_dict["wind_farm"]["n_turbines"]
        )

        # Apply curtailment after 500 minutes
        if current_time >= self.curtailment_time:
            # Simple proportional curtailment to reduce power output
            for t_idx in range(self.n_turbines):
                # Reduce power
                h_dict["wind_farm"]["turbine_power_setpoints"][t_idx] = self.turbine_curtail_power

        return h_dict


def main():
    """Run the wind timing test with power curtailment."""
    print("Starting wind timing test with power curtailment...")

    # Clean up output directory
    if os.path.exists("outputs"):
        shutil.rmtree("outputs")
    os.makedirs("outputs")

    # Setup logging
    logger = setup_logging()
    logger.info("Starting wind timing test with power curtailment")

    # Load the input file
    input_file = "hercules_input_wind_precom.yaml"
    logger.info(f"Loading input file: {input_file}")
    h_dict = load_hercules_input(input_file)

    # Record start time
    start_time = time.time()

    # Initialize the hybrid plant
    hybrid_plant = HybridPlant(h_dict)

    # Add meta data
    h_dict = hybrid_plant.add_plant_metadata_to_h_dict(h_dict)

    # Initialize the controller
    controller = PowerCurtailmentController(h_dict)

    # Initialize the emulator
    emulator = Emulator(controller, hybrid_plant, h_dict, logger)

    # Run the emulator
    logger.info("Starting emulator execution...")
    emulator.enter_execution(function_targets=[], function_arguments=[[]])

    # Record end time
    end_time = time.time()
    execution_time = end_time - start_time

    logger.info(f"Emulator execution completed in {execution_time:.2f} seconds")

    # Record timing result
    result_file = "timing_results.csv"
    record_timing_result(
        result_file=result_file,
        test_name="wind_precom",
        test_result_seconds=execution_time,
        notes=None,
    )
    print(f"Timing result recorded in {result_file}")
    print(f"Total execution time: {execution_time:.2f} seconds")

    # Plot the outputs
    if PLOT_OUTPUT:
        # Read the Hercules output file
        from hercules.utilities import read_hercules_hdf5

        df_p = read_hercules_hdf5("outputs/hercules_output.h5")

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df_p["time"], df_p["wind_farm.power"])
        ax.axvline(
            x=controller.curtailment_time, color="red", linestyle="--", label="Curtailment Start"
        )
        ax.legend()
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Power Output (kW)")
        ax.set_title("Wind Farm Power Output")
        plt.show()


if __name__ == "__main__":
    main()
