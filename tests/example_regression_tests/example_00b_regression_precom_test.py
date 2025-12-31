"""Regression tests for example cases using precomputed FLORIS."""

import os
import tempfile

import yaml
from hercules.utilities_examples import generate_example_inputs
from test_example_utilities import (
    copy_example_files,
    generate_input_data,
    run_simulation,
    update_input_file_paths,
)

## Parameters
# Example-specific configuration
EXAMPLE_DIR = "examples/00_wind_farm_only"
EXAMPLE_NAME = "example_00b"
EXAMPLE_DESCRIPTION = "Wind Farm Only with Precomputed FLORIS"

# Test configuration
NUM_TIME_STEPS = 5
EXPECTED_FINAL_WIND_POWER = 3021  # Updated for precomputed FLORIS model
EXPECTED_FINAL_PLANT_POWER = 3021  # Same as wind power for wind-only case

# File names
INPUT_FILE = "hercules_input.yaml"
INPUTS_DIR = "inputs"
OUTPUTS_DIR = "outputs"
OUTPUT_FILE = "outputs/hercules_output.feather"
NOTEBOOK_FILE = "generate_wind_history.ipynb"
PLOT_SCRIPT_FILE = "plot_outputs.py"


def modify_input_file_for_precom_floris(temp_dir, input_file):
    """Modify the input file to use Wind_MesoToPowerPrecomFloris component.

    Args:
        temp_dir (str): Path to the temporary directory.
        input_file (str): Name of the input file.
    """
    input_path = os.path.join(temp_dir, input_file)

    # Read the YAML file
    with open(input_path, "r") as f:
        h_dict = yaml.safe_load(f)

    # Modify the wind farm component type and ensure floris_update_time_s is present
    if "wind_farm" in h_dict:
        h_dict["wind_farm"]["component_type"] = "Wind_MesoToPowerPrecomFloris"
        # Ensure a reasonable floris_update_time_s value exists
        h_dict["wind_farm"]["floris_update_time_s"] = h_dict["wind_farm"].get(
            "floris_update_time_s", 300.0
        )

    # Write the modified YAML file back
    with open(input_path, "w") as f:
        yaml.dump(h_dict, f, default_flow_style=False)


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

        # Modify the input file to use precomputed FLORIS
        modify_input_file_for_precom_floris(temp_dir, INPUT_FILE)

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


def test_example_00b_precom_floris_limited_time_regression():
    """Test that example 00 with precomputed FLORIS runs correctly with limited time steps.

    This test modifies the example 00 configuration to use Wind_MesoToPowerPrecomFloris
    component type and run for only a few time steps. It verifies that the final
    outputs are reasonable and consistent.
    """
    # Ensure centralized example inputs exist
    generate_example_inputs()

    # Create a temporary directory for this test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the example files to the temp directory
        example_dir_abs = os.path.join(os.getcwd(), EXAMPLE_DIR)
        copy_example_files(example_dir_abs, temp_dir, INPUT_FILE, INPUTS_DIR, NOTEBOOK_FILE)

        # Update input file paths to use centralized inputs
        update_input_file_paths(temp_dir, INPUT_FILE)

        # Modify the input file to use precomputed FLORIS
        modify_input_file_for_precom_floris(temp_dir, INPUT_FILE)

        # Generate input data if needed (skip for centralized input system)
        # generate_input_data(temp_dir, NOTEBOOK_FILE)

        # Create outputs directory
        os.makedirs(f"{temp_dir}/{OUTPUTS_DIR}", exist_ok=True)

        # Change to the temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Run the simulation
            df = run_simulation(INPUT_FILE, NUM_TIME_STEPS)

            # Verify the outputs using the same utilities as the original test
            from test_example_utilities import verify_outputs

            verify_outputs(
                df,
                NUM_TIME_STEPS,
                EXPECTED_FINAL_WIND_POWER,
                EXPECTED_FINAL_PLANT_POWER,
            )

            # Test that the plot script works on the outputs
            from test_example_utilities import verify_plot_script

            verify_plot_script(temp_dir, original_cwd, EXAMPLE_DIR, PLOT_SCRIPT_FILE)

        finally:
            # Change back to original directory
            os.chdir(original_cwd)
