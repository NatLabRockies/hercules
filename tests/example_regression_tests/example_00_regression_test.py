"""Regression tests for example cases."""

import os
import tempfile

from test_example_utilities import (
    copy_example_files,
    generate_input_data,
    run_example_regression_test,
    run_simulation,
)

## Parameters
# Example-specific configuration
EXAMPLE_DIR = "examples/00_wind_farm_only"
EXAMPLE_NAME = "example_00"
EXAMPLE_DESCRIPTION = "Wind Farm Only"

# Test configuration
NUM_TIME_STEPS = 5
EXPECTED_FINAL_WIND_POWER = 3271  # Updated after wind model changes
EXPECTED_FINAL_PLANT_POWER = 3271  # Same as wind power for wind-only case

# File names
INPUT_FILE = "hercules_input.yaml"
INPUTS_DIR = "inputs"
OUTPUTS_DIR = "outputs"
OUTPUT_FILE = "outputs/hercules_output.feather"
NOTEBOOK_FILE = "generate_wind_history.ipynb"
PLOT_SCRIPT_FILE = "plot_outputs.py"


def print_expected_values():
    """Print the expected final wind power and plant power values for this example.

    This helper function runs the simulation and prints the actual final values
    that should be used as EXPECTED_FINAL_WIND_POWER and EXPECTED_FINAL_PLANT_POWER.
    """

    # Create a temporary directory for this helper
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the example files to the temp directory
        # Use absolute path to example directory
        example_dir_abs = os.path.join(os.getcwd(), EXAMPLE_DIR)
        copy_example_files(example_dir_abs, temp_dir, INPUT_FILE, INPUTS_DIR, NOTEBOOK_FILE)
        generate_input_data(temp_dir, NOTEBOOK_FILE)
        os.makedirs(f"{temp_dir}/{OUTPUTS_DIR}", exist_ok=True)

        # Change to the temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Run the simulation
            df = run_simulation(INPUT_FILE, NUM_TIME_STEPS)

            # Print the final values
            final_wind_power = df["wind_farm.power"].iloc[-1]
            final_plant_power = df["plant.power"].iloc[-1]

            print(f"Expected values for {EXAMPLE_NAME}:")
            print(f"EXPECTED_FINAL_WIND_POWER = {final_wind_power}")
            print(f"EXPECTED_FINAL_PLANT_POWER = {final_plant_power}")

        finally:
            # Change back to original directory
            os.chdir(original_cwd)


def test_example_00_limited_time_regression():
    """Test that example 00 runs correctly with limited time steps.

    This test modifies the example 00 configuration to run for only a few time steps
    and verifies that the final outputs are reasonable and consistent.
    """
    run_example_regression_test(
        example_dir=EXAMPLE_DIR,
        num_time_steps=NUM_TIME_STEPS,
        expected_final_wind_power=EXPECTED_FINAL_WIND_POWER,
        expected_final_plant_power=EXPECTED_FINAL_PLANT_POWER,
        input_file=INPUT_FILE,
        inputs_dir=INPUTS_DIR,
        outputs_dir=OUTPUTS_DIR,
        notebook_file=NOTEBOOK_FILE,
        plot_script_file=PLOT_SCRIPT_FILE,
    )
