"""Run solar timing test with power curtailment controller.

This script runs a solar farm simulation using the generated solar input data
and measures the execution time. It includes a simple controller that curtails
power to 20 MW halfway through the simulation (at 500 minutes).
"""

import time

import matplotlib.pyplot as plt
from hercules.hercules_model import HerculesModel
from hercules.utilities_examples import prepare_output_directory

from utilities import record_timing_result

PLOT_OUTPUT = True


class PowerCurtailmentController:
    """A simple controller that curtails power to 20 MW halfway through simulation.

    This controller sets the solar farm to full rating initially, then curtails
    power to 20 MW at 500 minutes (halfway through the 1000-minute simulation).
    """

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.
        """
        self.curtailment_time = 10 * 60 * 60  # seconds
        self.curtail_power = 10000  # kW

    def step(self, h_dict):
        """Execute one control step.

        Args:
            h_dict (dict): The hercules input dictionary.

        Returns:
            dict: The updated hercules input dictionary.
        """
        current_time = h_dict["time"]

        # # Set solar farm to full rating initially
        h_dict["solar_farm"]["power_setpoint"] = 1e10

        # Apply curtailment after 500 minutes
        if current_time >= self.curtailment_time:
            # Curtail power to specified level
            h_dict["solar_farm"]["power_setpoint"] = self.curtail_power

        return h_dict


def main():
    """Run the solar timing test with power curtailment."""
    print("Starting solar timing test with power curtailment...")

    # Prepare output directory
    prepare_output_directory()

    # Load the input file
    input_file = "hercules_input_solar.yaml"

    # Initialize the Hercules model
    hmodel = HerculesModel(input_file)

    # Instantiate the controller and assign to the Hercules model
    hmodel.assign_controller(PowerCurtailmentController(hmodel.h_dict))

    # Record start time
    start_time = time.time()

    # Run the simulation
    hmodel.logger.info("Starting simulation execution...")
    hmodel.run()

    # Record end time
    end_time = time.time()
    execution_time = end_time - start_time

    hmodel.logger.info(f"Simulation execution completed in {execution_time:.2f} seconds")
    hmodel.logger.info("Process completed successfully")

    # Record timing result
    result_file = "timing_results.csv"
    record_timing_result(
        result_file=result_file,
        test_name="solar",
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
        ax.plot(df_p["time"], df_p["solar_farm.power"])
        ax.axvline(
            x=hmodel.controller.curtailment_time,
            color="red",
            linestyle="--",
            label="Curtailment Start",
        )
        ax.legend()
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Power Output (kW)")
        ax.set_title("Solar Farm Power Output")
        plt.show()


if __name__ == "__main__":
    main()
