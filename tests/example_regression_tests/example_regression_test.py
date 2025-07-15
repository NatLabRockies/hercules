"""Regression tests for example cases."""

import os
import shutil
import tempfile

import numpy as np
import pandas as pd
from hercules.controller_standin import ControllerStandin
from hercules.emulator import Emulator
from hercules.py_sims import PySims
from hercules.utilities import load_hercules_input, setup_logging


def test_example_00_limited_time_regression():
    """Test that example 00 runs correctly with limited time steps.

    This test modifies the example 00 configuration to run for only a few time steps
    and verifies that the final outputs are reasonable and consistent.
    """
    # Create a temporary directory for this test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the example 00 files to the temp directory
        example_dir = "example_case_folders/00_wind_farm_only"

        # Copy input files
        shutil.copy2(f"{example_dir}/hercules_input.yaml", f"{temp_dir}/hercules_input.yaml")
        shutil.copytree(f"{example_dir}/inputs", f"{temp_dir}/inputs")

        # Copy the input generating notebook
        shutil.copy2(
            f"{example_dir}/generate_wind_history.ipynb", f"{temp_dir}/generate_wind_history.ipynb"
        )

        # Run the input generating notebook
        os.system(
            f"jupyter nbconvert --to notebook --execute {temp_dir}/generate_wind_history.ipynb"
        )

        # Create outputs directory
        os.makedirs(f"{temp_dir}/outputs", exist_ok=True)

        # Change to the temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Load the input file
            h_dict = load_hercules_input("hercules_input.yaml")

            # Modify the h_dict to limit running time to 5 time steps
            original_dt = h_dict["dt"]
            h_dict["endtime"] = h_dict["starttime"] + 5 * h_dict["dt"]  # 5 time steps
            h_dict["verbose"] = False  # Reduce logging for test

            # Set up logger
            logger = setup_logging(console_output=False)

            # Initialize the controller
            controller = ControllerStandin(h_dict)

            # Initialize the py_sims
            py_sims = PySims(h_dict)

            # Initialize the emulator
            emulator = Emulator(controller, py_sims, h_dict, logger)

            # Run the emulator
            emulator.enter_execution(function_targets=[], function_arguments=[[]])

            # Check that the output file was created
            output_file = "outputs/hercules_output.csv"
            assert os.path.exists(output_file), "Output file was not created"

            # Read the output file
            df = pd.read_csv(output_file)

            # Verify we have the expected number of rows (5 time steps + header)
            expected_rows = 5
            assert len(df) == expected_rows, f"Expected {expected_rows} rows, got {len(df)}"

            # Verify the time column progresses correctly
            expected_times = np.arange(0, 5 * original_dt, original_dt)
            np.testing.assert_allclose(df["time"].values, expected_times, rtol=1e-6)

            # Verify that wind farm power is reasonable (should be positive and finite)
            assert all(df["wind_farm.power"] >= 0), "Wind farm power should be non-negative"
            assert all(np.isfinite(df["wind_farm.power"])), "Wind farm power should be finite"

            # Verify that individual turbine powers are reasonable
            turbine_power_cols = [
                col for col in df.columns if col.startswith("wind_farm.turbine_powers.")
            ]
            assert len(turbine_power_cols) > 0, "Should have turbine power columns"

            # Test the the final wind power has not changed much
            expected_final_wind_power = 3860.285
            np.testing.assert_allclose(
                df["wind_farm.power"].iloc[-1], expected_final_wind_power, atol=1
            )

            # Test the the final plant power has not changed much

            np.testing.assert_allclose(
                df["plant.power"].iloc[-1], expected_final_wind_power, atol=1
            )

        finally:
            # Change back to original directory
            os.chdir(original_cwd)
