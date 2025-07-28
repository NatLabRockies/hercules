"""Regression tests for example cases."""

from test_example_utilities import run_example_regression_test

## Parameters
# Example-specific configuration
EXAMPLE_DIR = "example_case_folders/00_wind_farm_only"
EXAMPLE_NAME = "example_00"
EXAMPLE_DESCRIPTION = "Wind Farm Only"

# Test configuration
NUM_TIME_STEPS = 5
EXPECTED_FINAL_WIND_POWER = 3860.285
EXPECTED_FINAL_PLANT_POWER = 3860.285  # Same as wind power for wind-only case

# File names
INPUT_FILE = "hercules_input.yaml"
INPUTS_DIR = "inputs"
OUTPUTS_DIR = "outputs"
OUTPUT_FILE = "outputs/hercules_output.csv"
NOTEBOOK_FILE = "generate_wind_history.ipynb"
PLOT_SCRIPT_FILE = "plot_outputs.py"


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
