"""Utility functions for example regression tests."""

import os
import shutil
import subprocess
import tempfile

import numpy as np
from hercules.emulator import Emulator
from hercules.hybrid_plant import HybridPlant
from hercules.utilities import load_hercules_input, setup_logging
from hercules.utilities_examples import generate_example_inputs


def copy_example_files(example_dir, temp_dir, input_file, inputs_dir, notebook_file):
    """Copy example files to a temporary directory.

    Args:
        example_dir (str): Path to the example directory.
        temp_dir (str): Path to the temporary directory.
        input_file (str): Name of the input file.
        inputs_dir (str): Name of the inputs directory.
        notebook_file (str): Name of the notebook file.
    """
    # Copy the input file
    shutil.copy2(f"{example_dir}/{input_file}", f"{temp_dir}/{input_file}")

    # Copy the inputs directory
    if os.path.exists(f"{example_dir}/{inputs_dir}"):
        shutil.copytree(f"{example_dir}/{inputs_dir}", f"{temp_dir}/{inputs_dir}")

    # Copy the notebook file if it exists
    if os.path.exists(f"{example_dir}/{notebook_file}"):
        shutil.copy2(f"{example_dir}/{notebook_file}", f"{temp_dir}/{notebook_file}")


def update_input_file_paths(temp_dir, input_file):
    """Update the hercules input file to use absolute paths to centralized inputs.

    Args:
        temp_dir (str): Path to the temporary directory.
        input_file (str): Name of the input file.
    """
    import yaml

    input_file_path = f"{temp_dir}/{input_file}"

    # Get absolute path to centralized inputs directory
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    centralized_inputs_dir = os.path.join(repo_root, "examples", "inputs")

    # Read the input file
    with open(input_file_path, "r") as f:
        h_dict = yaml.safe_load(f)

    # Update paths in wind_farm section
    if "wind_farm" in h_dict:
        if "floris_input_file" in h_dict["wind_farm"]:
            # Convert relative path to absolute path
            filename = os.path.basename(h_dict["wind_farm"]["floris_input_file"])
            h_dict["wind_farm"]["floris_input_file"] = os.path.join(
                centralized_inputs_dir, filename
            )

        if "wind_input_filename" in h_dict["wind_farm"]:
            # Convert relative path to absolute path
            filename = os.path.basename(h_dict["wind_farm"]["wind_input_filename"])
            h_dict["wind_farm"]["wind_input_filename"] = os.path.join(
                centralized_inputs_dir, filename
            )

        if "turbine_file_name" in h_dict["wind_farm"]:
            # Convert relative path to absolute path
            filename = os.path.basename(h_dict["wind_farm"]["turbine_file_name"])
            h_dict["wind_farm"]["turbine_file_name"] = os.path.join(
                centralized_inputs_dir, filename
            )

    # Update paths in solar_farm section
    if "solar_farm" in h_dict:
        if "solar_input_filename" in h_dict["solar_farm"]:
            # Convert relative path to absolute path
            filename = os.path.basename(h_dict["solar_farm"]["solar_input_filename"])
            h_dict["solar_farm"]["solar_input_filename"] = os.path.join(
                centralized_inputs_dir, filename
            )

    # Write the updated input file
    with open(input_file_path, "w") as f:
        yaml.dump(h_dict, f, default_flow_style=False)


def generate_input_data(temp_dir, notebook_file):
    """Generate input data by running a notebook.

    Args:
        temp_dir (str): Path to the temporary directory.
        notebook_file (str): Name of the notebook file.
    """
    if os.path.exists(f"{temp_dir}/{notebook_file}"):
        # Run the notebook to generate input data
        result = subprocess.run(
            ["jupyter", "nbconvert", "--to", "notebook", "--execute", notebook_file],
            cwd=temp_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"Notebook execution failed: {result.stderr}")


def run_simulation(input_file, num_time_steps):
    """Run a simulation and return the output dataframe.

    Args:
        input_file (str): Path to the input file.
        num_time_steps (int): Number of time steps to run.

    Returns:
        pd.DataFrame: The simulation output dataframe.
    """
    # Load the input file
    h_dict = load_hercules_input(input_file)

    # Modify the endtime to run for the specified number of time steps
    h_dict["endtime"] = num_time_steps

    # Set up logging
    logger = setup_logging(console_output=False)

    class ControllerSimple:
        """A simple controller for testing."""

        def __init__(self, h_dict):
            """Initialize the controller.

            Args:
                h_dict (dict): Hercules input dictionary.
            """
            pass

        def step(self, h_dict):
            """Execute one control step.

            Args:
                h_dict (dict): Hercules input dictionary.

            Returns:
                dict: Updated Hercules input dictionary.
            """
            # Set power setpoints for wind turbines
            if "wind_farm" in h_dict:
                h_dict["wind_farm"]["turbine_power_setpoints"] = 5000 * np.ones(
                    h_dict["wind_farm"]["n_turbines"]
                )
                h_dict["wind_farm"]["turbine_power_setpoints"][0] = 500

            # Add a solar power setpoint signal which is very high to have no impact
            if "solar_farm" in h_dict:
                h_dict["solar_farm"]["power_setpoint"] = 1e10

            return h_dict

    # Initialize the controller
    controller = ControllerSimple(h_dict)

    # Initialize the hybrid plant
    hybrid_plant = HybridPlant(h_dict)

    # Initialize the emulator
    emulator = Emulator(controller, hybrid_plant, h_dict, logger)

    # Run the emulator
    emulator.enter_execution(function_targets=[], function_arguments=[[]])

    # Check that the output file was created
    output_file = "outputs/hercules_output.h5"
    assert os.path.exists(output_file), "Output file was not created"

    # Read and return the output file
    from hercules.utilities import read_hercules_hdf5

    return read_hercules_hdf5(output_file)


def verify_outputs(
    df,
    num_time_steps,
    expected_final_wind_power,
    expected_final_plant_power,
    expected_final_solar_power=None,
):
    """Verify that the simulation outputs are correct.

    Args:
        df (pd.DataFrame): The simulation output dataframe.
        num_time_steps (int): Expected number of time steps.
        expected_final_wind_power (float): Expected final wind farm power.
        expected_final_plant_power (float): Expected final plant power.
        expected_final_solar_power (float, optional): Expected final solar farm power.
            Defaults to None.
    """
    # Verify we have the expected number of rows
    assert len(df) == num_time_steps, f"Expected {num_time_steps} rows, got {len(df)}"

    # Verify the time column progresses correctly
    expected_times = np.arange(0, num_time_steps, 1)  # Assuming dt=1 for simplicity
    np.testing.assert_allclose(df["time"].values, expected_times, rtol=1e-6)

    # Verify that wind farm power is reasonable (should be positive and finite)
    if "wind_farm.power" in df.columns:
        assert all(df["wind_farm.power"] >= 0), "Wind farm power should be non-negative"
        assert all(np.isfinite(df["wind_farm.power"])), "Wind farm power should be finite"

        # Verify that individual turbine powers are reasonable
        turbine_power_cols = [
            col for col in df.columns if col.startswith("wind_farm.turbine_powers.")
        ]
        # Only check turbine power columns if they were logged by the example
        # Some examples configure log_channels to only include aggregate power
        if len(turbine_power_cols) > 0:
            # Ensure values are non-negative and finite when present
            for col in turbine_power_cols:
                assert all(df[col] >= 0), f"{col} should be non-negative"
                assert all(np.isfinite(df[col])), f"{col} should be finite"

        # Test that the final wind power has not changed much
        np.testing.assert_allclose(
            df["wind_farm.power"].iloc[-1], expected_final_wind_power, atol=1
        )

    # Verify that solar farm power is reasonable (should be non-negative and finite)
    if "solar_farm.power" in df.columns:
        assert all(df["solar_farm.power"] >= 0), "Solar farm power should be non-negative"
        assert all(np.isfinite(df["solar_farm.power"])), "Solar farm power should be finite"

        # Test that the final solar power has not changed much (if expected value provided)
        if expected_final_solar_power is not None:
            np.testing.assert_allclose(
                df["solar_farm.power"].iloc[-1], expected_final_solar_power, atol=15
            )

    # Test that the final plant power has not changed much
    np.testing.assert_allclose(df["plant.power"].iloc[-1], expected_final_plant_power, atol=15)


def verify_plot_script(temp_dir, original_cwd, example_dir, plot_script_file):
    """Test that the plot script works on the outputs.

    Args:
        temp_dir (str): Path to the temporary directory.
        original_cwd (str): Original working directory.
        example_dir (str): Path to the example directory.
        plot_script_file (str): Name of the plot script file.
    """
    # Copy the plot script to the temp directory
    # Use absolute path since we're now in the temp directory
    example_dir_abs = os.path.join(original_cwd, example_dir)
    plot_script_path = f"{example_dir_abs}/{plot_script_file}"

    if os.path.exists(plot_script_path):
        shutil.copy2(plot_script_path, f"{temp_dir}/{plot_script_file}")

        # Run the plot script with non-interactive matplotlib backend
        # to prevent plt.show() from hanging the test
        env = os.environ.copy()
        env["MPLBACKEND"] = "Agg"  # Non-interactive backend
        result = subprocess.run(
            ["python", plot_script_file],
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout
            env=env,
        )

        # Check that the script ran successfully
        assert result.returncode == 0, (
            f"{plot_script_file} failed with return code {result.returncode}. "
            f"stderr: {result.stderr}"
        )


def run_example_regression_test(
    example_dir,
    num_time_steps,
    expected_final_wind_power,
    expected_final_plant_power,
    expected_final_solar_power=None,
    input_file="hercules_input.yaml",
    inputs_dir="inputs",
    outputs_dir="outputs",
    notebook_file="generate_wind_history.ipynb",
    plot_script_file="plot_outputs.py",
):
    """Run a complete example regression test.

    Args:
        example_dir (str): Path to the example directory.
        num_time_steps (int): Number of time steps to run.
        expected_final_wind_power (float): Expected final wind farm power.
        expected_final_plant_power (float): Expected final plant power.
        expected_final_solar_power (float, optional): Expected final solar farm power.
            Defaults to None.
        input_file (str, optional): Name of the input file. Defaults to "hercules_input.yaml".
        inputs_dir (str, optional): Name of the inputs directory. Defaults to "inputs".
        outputs_dir (str, optional): Name of the outputs directory. Defaults to "outputs".
        notebook_file (str, optional): Name of the notebook file.
            Defaults to "generate_wind_history.ipynb".
        plot_script_file (str, optional): Name of the plot script file.
            Defaults to "plot_outputs.py".
    """
    # Ensure centralized example inputs exist
    generate_example_inputs()

    # Create a temporary directory for this test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the example files to the temp directory
        copy_example_files(example_dir, temp_dir, input_file, inputs_dir, notebook_file)

        # Update input file paths to use centralized inputs
        update_input_file_paths(temp_dir, input_file)

        # Generate input data if needed (skip for centralized input system)
        # generate_input_data(temp_dir, notebook_file)

        # Create outputs directory
        os.makedirs(f"{temp_dir}/{outputs_dir}", exist_ok=True)

        # Change to the temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Run the simulation
            df = run_simulation(input_file, num_time_steps)

            # Verify the outputs
            verify_outputs(
                df,
                num_time_steps,
                expected_final_wind_power,
                expected_final_plant_power,
                expected_final_solar_power,
            )

            # Test that the plot script works on the outputs
            verify_plot_script(temp_dir, original_cwd, example_dir, plot_script_file)

        finally:
            # Change back to original directory
            os.chdir(original_cwd)
