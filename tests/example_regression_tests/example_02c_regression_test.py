"""Regression test for example 02c using direct wake model (no wake modeling)."""

import os
import tempfile

import numpy as np
import yaml
from hercules.utilities_examples import generate_example_inputs
from test_example_utilities import (
    copy_example_files,
    update_input_file_paths,
)

## Parameters
# Example-specific configuration
EXAMPLE_DIR = "examples/02c_wind_farm_realistic_inflow_direct"
EXAMPLE_NAME = "example_02c"
EXAMPLE_DESCRIPTION = "Wind Farm Realistic Inflow (Direct - No Wake Modeling)"

# Test configuration - use short simulation for faster testing
NUM_TIME_STEPS = 100  # About 100 seconds
# Expected values will be higher than 02b because no wake losses
EXPECTED_FINAL_WIND_POWER = 18500  # Approximate, no wake losses
EXPECTED_FINAL_PLANT_POWER = 18500  # Same as wind power for wind-only case
TOLERANCE = 1000  # Allow some tolerance in power values

# File names
INPUT_FILE = "hercules_input.yaml"
INPUTS_DIR = "inputs"
OUTPUTS_DIR = "outputs"
OUTPUT_FILE = "outputs/hercules_output.feather"
PLOT_SCRIPT_FILE = "plot_outputs.py"


def modify_input_file_for_direct(temp_dir, input_file, num_steps):
    """Modify the input file for testing with shorter duration.

    Args:
        temp_dir (str): Path to the temporary directory.
        input_file (str): Name of the input file.
        num_steps (int): Number of time steps to run.
    """
    input_path = os.path.join(temp_dir, input_file)

    # Read the YAML file
    with open(input_path) as f:
        h_dict = yaml.safe_load(f)

    # Modify the end time to run for num_steps seconds
    # Keep starttime_utc the same, just change endtime_utc
    import pandas as pd

    start_time = pd.to_datetime(h_dict["starttime_utc"])
    end_time = start_time + pd.Timedelta(seconds=num_steps)
    h_dict["endtime_utc"] = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Ensure component type is correct
    if "wind_farm" in h_dict:
        h_dict["wind_farm"]["component_type"] = "Wind_MesoToPowerDirect"
        # Ensure floris_update_time_s exists (required even though not used)
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
        example_dir_abs = os.path.join(os.getcwd(), EXAMPLE_DIR)
        copy_example_files(example_dir_abs, temp_dir, INPUT_FILE, INPUTS_DIR, None)

        # Generate example inputs if they don't exist
        generate_example_inputs()

        os.makedirs(f"{temp_dir}/{OUTPUTS_DIR}", exist_ok=True)

        # Modify the input file
        modify_input_file_for_direct(temp_dir, INPUT_FILE, NUM_TIME_STEPS)

        # Update input file paths to use absolute paths
        update_input_file_paths(temp_dir, INPUT_FILE)

        # Change to the temp directory and run
        original_dir = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Import and run
            from hercules.hercules_model import HerculesModel

            hmodel = HerculesModel(INPUT_FILE)

            # Simple controller
            class SimpleController:
                def __init__(self, h_dict):
                    pass

                def step(self, h_dict):
                    h_dict["wind_farm"]["turbine_power_setpoints"] = 5000 * np.ones(
                        h_dict["wind_farm"]["n_turbines"]
                    )
                    return h_dict

            hmodel.assign_controller(SimpleController(hmodel.h_dict))
            hmodel.run()

            # Get final values
            final_wind_power = round(hmodel.h_dict["wind_farm"]["power"])
            final_plant_power = round(hmodel.h_dict["plant"]["power"])

            print(f"\nFinal values for {EXAMPLE_NAME}:")
            print(f"EXPECTED_FINAL_WIND_POWER = {final_wind_power}")
            print(f"EXPECTED_FINAL_PLANT_POWER = {final_plant_power}")

        finally:
            os.chdir(original_dir)


def test_example_02c_direct():
    """Test example 02c (direct wake model) runs and produces expected output."""
    # Create a temporary directory for this test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the example files to the temp directory
        example_dir_abs = os.path.join(os.getcwd(), EXAMPLE_DIR)
        copy_example_files(example_dir_abs, temp_dir, INPUT_FILE, INPUTS_DIR, None)

        # Generate example inputs if they don't exist
        generate_example_inputs()

        os.makedirs(f"{temp_dir}/{OUTPUTS_DIR}", exist_ok=True)

        # Modify the input file
        modify_input_file_for_direct(temp_dir, INPUT_FILE, NUM_TIME_STEPS)

        # Update input file paths to use absolute paths
        update_input_file_paths(temp_dir, INPUT_FILE)

        # Change to the temp directory and run
        original_dir = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Import and run
            from hercules.hercules_model import HerculesModel

            hmodel = HerculesModel(INPUT_FILE)

            # Simple controller
            class SimpleController:
                def __init__(self, h_dict):
                    pass

                def step(self, h_dict):
                    h_dict["wind_farm"]["turbine_power_setpoints"] = 5000 * np.ones(
                        h_dict["wind_farm"]["n_turbines"]
                    )
                    return h_dict

            hmodel.assign_controller(SimpleController(hmodel.h_dict))
            hmodel.run()

            # Get final values
            final_wind_power = hmodel.h_dict["wind_farm"]["power"]
            final_plant_power = hmodel.h_dict["plant"]["power"]

            # Check that values are reasonable (within tolerance)
            # Direct mode should have higher power than waked scenarios
            assert final_wind_power > 0, "Final wind power should be positive"
            assert final_plant_power > 0, "Final plant power should be positive"
            assert (
                abs(final_wind_power - EXPECTED_FINAL_WIND_POWER) < TOLERANCE
            ), f"Wind power {final_wind_power} differs from expected {EXPECTED_FINAL_WIND_POWER}"
            assert (
                abs(final_plant_power - EXPECTED_FINAL_PLANT_POWER) < TOLERANCE
            ), f"Plant power {final_plant_power} differs from expected {EXPECTED_FINAL_PLANT_POWER}"

            # Verify no FLORIS calculations were performed (direct mode)
            assert (
                hmodel.hybrid_plant.component_objects["wind_farm"].num_floris_calcs == 0
            ), "Direct mode should not perform FLORIS calculations"

            # Verify wake model is correct
            assert (
                hmodel.hybrid_plant.component_objects["wind_farm"].wake_model == "none"
            ), "Wake model should be 'none' for direct mode"

        finally:
            os.chdir(original_dir)


def test_example_02c_no_wakes_applied():
    """Test that no wake deficits are applied in direct mode."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the example files to the temp directory
        example_dir_abs = os.path.join(os.getcwd(), EXAMPLE_DIR)
        copy_example_files(example_dir_abs, temp_dir, INPUT_FILE, INPUTS_DIR, None)

        # Generate example inputs if they don't exist
        generate_example_inputs()

        os.makedirs(f"{temp_dir}/{OUTPUTS_DIR}", exist_ok=True)

        # Modify the input file
        modify_input_file_for_direct(temp_dir, INPUT_FILE, 10)  # Just 10 steps

        # Update input file paths to use absolute paths
        update_input_file_paths(temp_dir, INPUT_FILE)

        # Change to the temp directory and run
        original_dir = os.getcwd()
        try:
            os.chdir(temp_dir)

            from hercules.hercules_model import HerculesModel

            hmodel = HerculesModel(INPUT_FILE)

            # Simple controller
            class SimpleController:
                def __init__(self, h_dict):
                    pass

                def step(self, h_dict):
                    h_dict["wind_farm"]["turbine_power_setpoints"] = 5000 * np.ones(
                        h_dict["wind_farm"]["n_turbines"]
                    )
                    return h_dict

            hmodel.assign_controller(SimpleController(hmodel.h_dict))
            hmodel.run()

            # Get wind farm component
            wind_farm = hmodel.hybrid_plant.component_objects["wind_farm"]

            # Verify wake deficits are zero
            assert np.all(
                wind_farm.floris_wake_deficits == 0.0
            ), "Wake deficits should be zero in direct mode"

            # Verify withwakes equals background
            assert np.allclose(
                wind_farm.wind_speeds_withwakes, wind_farm.wind_speeds_background
            ), "Wind speeds with wakes should equal background speeds in direct mode"

        finally:
            os.chdir(original_dir)


if __name__ == "__main__":
    # When run directly, print expected values
    print(f"Printing expected values for {EXAMPLE_NAME}...")
    print_expected_values()
