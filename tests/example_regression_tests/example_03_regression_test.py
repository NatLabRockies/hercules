"""Regression tests for example cases."""

import os
import pickle
import tempfile

import numpy as np
import pandas as pd
from test_example_utilities import (
    copy_example_files,
    run_simulation,
    verify_outputs,
    verify_plot_script,
)

## Parameters
# Example-specific configuration
EXAMPLE_DIR = "example_case_folders/03_wind_and_solar"
EXAMPLE_NAME = "example_03"
EXAMPLE_DESCRIPTION = "Wind and Solar"

# Test configuration
NUM_TIME_STEPS = 5
EXPECTED_FINAL_WIND_POWER = 3892  # Updated after running print_expected_values
EXPECTED_FINAL_SOLAR_POWER = 5784  # Updated after running print_expected_values
EXPECTED_FINAL_PLANT_POWER = 9676  # Updated after running print_expected_values

# File names
INPUT_FILE = "hercules_input.yaml"
INPUTS_DIR = "inputs"
OUTPUTS_DIR = "outputs"
OUTPUT_FILE = "outputs/hercules_output.csv"
NOTEBOOK_FILE = "resample_solar_history.ipynb"
PLOT_SCRIPT_FILE = "plot_outputs.py"


def create_test_input_files(temp_dir):
    """Create simplified wind and solar input files for testing.

    Args:
        temp_dir (str): Path to the temporary directory.
    """
    # Create inputs directory
    inputs_dir = f"{temp_dir}/{INPUTS_DIR}"
    os.makedirs(inputs_dir, exist_ok=True)

    # Create wind input data (5 time steps) - pickle format like example_03
    # We need 3 turbines (ws_000, ws_001, ws_002) with wind speeds and directions
    wind_data = {
        "time": np.arange(0, NUM_TIME_STEPS, 1),
        "ws_000": np.array([8.0, 8.1, 7.9, 8.2, 8.0]),  # Wind speed for turbine 0
        "ws_001": np.array([8.0, 8.1, 7.9, 8.2, 8.0]),  # Wind speed for turbine 1
        "ws_002": np.array([8.0, 8.1, 7.9, 8.2, 8.0]),  # Wind speed for turbine 2
        "wd_mean": np.array([270.0, 270.0, 270.0, 270.0, 270.0]),  # Wind direction
    }

    # Create solar input data (5 time steps) - pickle format like example_03
    solar_data = {
        "time": np.arange(0, NUM_TIME_STEPS, 1),
        "time_utc": pd.date_range(
            "2024-06-24 17:00:00", periods=NUM_TIME_STEPS, freq="1s", tz="UTC"
        ),
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

    # Save wind input file as pickle
    wind_df = pd.DataFrame(wind_data)
    with open(f"{inputs_dir}/wind_input.p", "wb") as f:
        pickle.dump(wind_df, f)

    # Save solar input file as pickle
    solar_df = pd.DataFrame(solar_data)
    with open(f"{inputs_dir}/solar_input.p", "wb") as f:
        pickle.dump(solar_df, f)


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

        # Create test input files
        create_test_input_files(temp_dir)

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
    # Create a temporary directory for this test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the example files to the temp directory
        example_dir_abs = os.path.join(os.getcwd(), EXAMPLE_DIR)
        copy_example_files(example_dir_abs, temp_dir, INPUT_FILE, INPUTS_DIR, NOTEBOOK_FILE)

        # Create test input files
        create_test_input_files(temp_dir)

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
