"""Regression tests for example cases."""

import os
import tempfile

import numpy as np
import pandas as pd
from hercules.utilities_examples import generate_example_inputs
from test_example_utilities import (
    copy_example_files,
    run_simulation,
    verify_outputs,
    verify_plot_script,
)

## Parameters
# Example-specific configuration
EXAMPLE_DIR = "examples/03_wind_and_solar"
EXAMPLE_NAME = "example_03"
EXAMPLE_DESCRIPTION = "Wind and Solar"

# Test configuration
NUM_TIME_STEPS = 5
EXPECTED_FINAL_WIND_POWER = 14322  # Updated for 9 turbines with large config
EXPECTED_FINAL_SOLAR_POWER = 20912  # Expected final solar farm power output (kW)
EXPECTED_FINAL_PLANT_POWER = 35234  # Wind + Solar (14322 + 20912)

# File names
INPUT_FILE = "hercules_input.yaml"
INPUTS_DIR = "inputs"
OUTPUTS_DIR = "outputs"
OUTPUT_FILE = "outputs/hercules_output.feather"
NOTEBOOK_FILE = "resample_solar_history.ipynb"
PLOT_SCRIPT_FILE = "plot_outputs.py"


def create_test_input_files(temp_dir):
    """Create simplified wind and solar input files for testing.

    Args:
        temp_dir (str): Path to the temporary directory.
    """
    # Create a temporary inputs directory within the test directory
    test_inputs_dir = os.path.join(temp_dir, "test_inputs")
    os.makedirs(test_inputs_dir, exist_ok=True)

    # Load starttime_utc from the copied example input to build time_utc
    import yaml

    with open(os.path.join(temp_dir, INPUT_FILE), "r") as f:
        _h = yaml.safe_load(f)
    starttime_utc = pd.to_datetime(_h["starttime_utc"], utc=True)

    # Create wind input data (5 time steps) - feather format for test
    # We need 9 turbines (ws_000 through ws_008) with wind speeds and directions for large config
    wind_data = {
        "time": np.arange(0, NUM_TIME_STEPS, 1),
        "time_utc": pd.date_range(start=starttime_utc, periods=NUM_TIME_STEPS, freq="1s", tz="UTC"),
        "wd_mean": np.array([270.0, 270.0, 270.0, 270.0, 270.0]),  # Wind direction
    }

    # Add wind speed data for all 9 turbines
    for i in range(9):
        wind_data[f"ws_{i:03d}"] = np.array([8.0, 8.1, 7.9, 8.2, 8.0])  # Wind speed for turbine i

    # Create solar input data (5 time steps) - feather format for test
    solar_data = {
        "time": np.arange(0, NUM_TIME_STEPS, 1),
        "time_utc": pd.date_range(start=starttime_utc, periods=NUM_TIME_STEPS, freq="1s", tz="UTC"),
        # GHI (daytime - realistic values from actual data ~735 W/m²)
        "SRRL BMS Global Horizontal Irradiance (W/m²_irr)": np.array(
            [735.0, 737.0, 732.0, 739.0, 735.0]
        ),
        # DNI (daytime - realistic values from actual data ~434 W/m²)
        "SRRL BMS Direct Normal Irradiance (W/m²_irr)": np.array(
            [434.0, 436.0, 431.0, 438.0, 434.0]
        ),
        # DHI (daytime - realistic values from actual data ~315 W/m²)
        "SRRL BMS Diffuse Horizontal Irradiance (W/m²_irr)": np.array(
            [315.0, 317.0, 312.0, 319.0, 315.0]
        ),
        # Air temperature
        "SRRL BMS Dry Bulb Temperature (°C)": np.array([25.0, 25.0, 25.0, 25.0, 25.0]),
        # Wind speed at solar farm
        "SRRL BMS Wind Speed at 19' (m/s)": np.array([2.0, 2.1, 1.9, 2.2, 2.0]),
        "Avg Wind Speed @ 10m [m/s]": np.array([2.0, 2.1, 1.9, 2.2, 2.0]),  # Average wind speed
        "Peak Wind Speed @ 2m [m/s]": np.array([2.5, 2.6, 2.4, 2.7, 2.5]),  # Peak wind speed 2m
        "Peak Wind Speed @ 10m [m/s]": np.array([2.5, 2.6, 2.4, 2.7, 2.5]),  # Peak wind speed 10m
    }

    # Save wind input file as feather in test directory (not overwriting centralized files)
    wind_df = pd.DataFrame(wind_data)
    wind_df.to_feather(f"{test_inputs_dir}/wind_input_large.ftr")

    # Save solar input file as feather in test directory (not overwriting centralized files)
    solar_df = pd.DataFrame(solar_data)
    solar_df.to_feather(f"{test_inputs_dir}/solar_input.ftr")

    return test_inputs_dir


def update_input_file_paths_for_test(temp_dir, input_file, test_inputs_dir):
    """Update the hercules input file to use test-specific input files.

    Args:
        temp_dir (str): Path to the temporary directory.
        input_file (str): Name of the input file.
        test_inputs_dir (str): Path to the test inputs directory.
    """
    import yaml

    input_file_path = f"{temp_dir}/{input_file}"

    # Read the input file
    with open(input_file_path, "r") as f:
        h_dict = yaml.safe_load(f)

    # Update paths in wind_farm section to use test inputs
    if "wind_farm" in h_dict:
        if "floris_input_file" in h_dict["wind_farm"]:
            # Use absolute path to centralized FLORIS config (it's not modified by tests)
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            centralized_inputs_dir = os.path.join(repo_root, "examples", "inputs")
            filename = os.path.basename(h_dict["wind_farm"]["floris_input_file"])
            h_dict["wind_farm"]["floris_input_file"] = os.path.join(
                centralized_inputs_dir, filename
            )

        if "wind_input_filename" in h_dict["wind_farm"]:
            # Use test wind input file
            filename = os.path.basename(h_dict["wind_farm"]["wind_input_filename"])
            h_dict["wind_farm"]["wind_input_filename"] = os.path.join(test_inputs_dir, filename)

        if "turbine_file_name" in h_dict["wind_farm"]:
            # Use absolute path to centralized turbine config (it's not modified by tests)
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            centralized_inputs_dir = os.path.join(repo_root, "examples", "inputs")
            filename = os.path.basename(h_dict["wind_farm"]["turbine_file_name"])
            h_dict["wind_farm"]["turbine_file_name"] = os.path.join(
                centralized_inputs_dir, filename
            )

    # Update paths in solar_farm section to use test inputs
    if "solar_farm" in h_dict:
        if "solar_input_filename" in h_dict["solar_farm"]:
            # Use test solar input file
            filename = os.path.basename(h_dict["solar_farm"]["solar_input_filename"])
            h_dict["solar_farm"]["solar_input_filename"] = os.path.join(test_inputs_dir, filename)

    # Also adjust endtime_utc to match the shortened test duration
    if "starttime_utc" in h_dict:
        start_ts = pd.to_datetime(h_dict["starttime_utc"], utc=True)
        # For NUM_TIME_STEPS time steps (0, 1, 2, ..., NUM_TIME_STEPS-1),
        # the end time should be at starttime + (NUM_TIME_STEPS - 1) seconds
        new_end = start_ts + pd.to_timedelta(NUM_TIME_STEPS - 1, unit="s")
        h_dict["endtime_utc"] = new_end.isoformat().replace("+00:00", "Z")

    # Write the updated input file
    with open(input_file_path, "w") as f:
        yaml.dump(h_dict, f, default_flow_style=False)


def print_expected_values():
    """Print the expected final wind power, solar power, and plant power values for this example.

    This helper function runs the simulation and prints the actual final values
    that should be used as EXPECTED_FINAL_WIND_POWER, EXPECTED_FINAL_SOLAR_POWER,
    and EXPECTED_FINAL_PLANT_POWER.
    """

    # Create a temporary directory for this helper
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the example files to the temp directory
        # Use absolute path to example directory
        example_dir_abs = os.path.join(os.getcwd(), EXAMPLE_DIR)
        copy_example_files(example_dir_abs, temp_dir, INPUT_FILE, INPUTS_DIR, NOTEBOOK_FILE)

        # Create test input files in a separate test directory
        test_inputs_dir = create_test_input_files(temp_dir)

        # Update input file paths to use test-specific inputs
        update_input_file_paths_for_test(temp_dir, INPUT_FILE, test_inputs_dir)

        # Skip notebook execution since we're creating our own input files
        # generate_input_data(temp_dir, NOTEBOOK_FILE)
        os.makedirs(f"{temp_dir}/{OUTPUTS_DIR}", exist_ok=True)

        # Change to the temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Run the simulation
            df = run_simulation(INPUT_FILE, NUM_TIME_STEPS)

            # Print the final values
            final_wind_power = df["wind_farm.power"].iloc[-1]
            final_solar_power = df["solar_farm.power"].iloc[-1]
            final_plant_power = df["plant.power"].iloc[-1]

            print(f"Expected values for {EXAMPLE_NAME}:")
            print(f"EXPECTED_FINAL_WIND_POWER = {final_wind_power}")
            print(f"EXPECTED_FINAL_SOLAR_POWER = {final_solar_power}")
            print(f"EXPECTED_FINAL_PLANT_POWER = {final_plant_power}")

        finally:
            # Change back to original directory
            os.chdir(original_cwd)


def test_example_03_limited_time_regression():
    """Test that example 03 runs correctly with limited time steps.

    This test modifies the example 03 configuration to run for only a few time steps
    and verifies that the final outputs are reasonable and consistent.
    """
    # Ensure centralized example inputs exist
    generate_example_inputs()

    # Create a temporary directory for this test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the example files to the temp directory
        example_dir_abs = os.path.join(os.getcwd(), EXAMPLE_DIR)
        copy_example_files(example_dir_abs, temp_dir, INPUT_FILE, INPUTS_DIR, NOTEBOOK_FILE)

        # Create test input files in a separate test directory
        test_inputs_dir = create_test_input_files(temp_dir)

        # Update input file paths to use test-specific inputs (not centralized ones)
        update_input_file_paths_for_test(temp_dir, INPUT_FILE, test_inputs_dir)

        # Skip notebook execution since we're creating our own input files
        # generate_input_data(temp_dir, NOTEBOOK_FILE)
        os.makedirs(f"{temp_dir}/{OUTPUTS_DIR}", exist_ok=True)

        # Change to the temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Run the simulation
            df = run_simulation(INPUT_FILE, NUM_TIME_STEPS)

            # Verify the outputs

            verify_outputs(
                df,
                NUM_TIME_STEPS,
                EXPECTED_FINAL_WIND_POWER,
                EXPECTED_FINAL_PLANT_POWER,
                EXPECTED_FINAL_SOLAR_POWER,
            )

            # Test that the plot script works on the outputs

            verify_plot_script(temp_dir, original_cwd, example_dir_abs, PLOT_SCRIPT_FILE)

        finally:
            # Change back to original directory
            os.chdir(original_cwd)
