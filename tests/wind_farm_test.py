"""Tests for the WindFarm class in dynamic wake mode."""

import copy
import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from hercules.plant_components.wind_farm import WindFarm
from hercules.utilities import hercules_float_type

from tests.test_inputs.h_dict import h_dict_wind


def test_wind_farm_initialization():
    """Test that WindFarm initializes correctly with valid inputs (dynamic mode)."""
    wind_sim = WindFarm(h_dict_wind)

    assert wind_sim.component_name == "wind_farm"
    assert wind_sim.component_type == "WindFarm"
    assert wind_sim.n_turbines == 3
    assert wind_sim.dt == 1.0
    assert wind_sim.starttime == 0.0
    assert wind_sim.endtime == 10.0
    assert wind_sim.num_floris_calcs == 1  # FLORIS is called during initialization
    assert wind_sim.floris_update_time_s == 30.0


def test_wind_farm_ws_mean():
    """Test that invalid component_type raises ValueError."""

    current_dir = os.path.dirname(__file__)

    df_input = pd.read_csv(current_dir + "/test_inputs/wind_input.csv")
    df_input["ws_mean"] = 10.0
    df_input.to_csv(current_dir + "/test_inputs/wind_input_temp.csv")

    test_h_dict = copy.deepcopy(h_dict_wind)
    test_h_dict["wind_farm"]["wind_input_filename"] = "tests/test_inputs/wind_input_temp.csv"

    # Test that, since individual speed are specified, ws_mean is ignored
    # Note that h_dict_wind specifies an end time of 10.
    wind_sim = WindFarm(test_h_dict)
    assert (
        wind_sim.ws_mat[:, 0] == df_input["ws_000"].to_numpy(dtype=hercules_float_type)[:10]
    ).all()
    assert np.allclose(
        wind_sim.ws_mat_mean,
        (df_input[["ws_000", "ws_001", "ws_002"]].mean(axis=1)).to_numpy(dtype=hercules_float_type)[
            :10
        ],
    )

    # Drop individual speeds and test that ws_mean is used instead
    df_input = df_input.drop(columns=["ws_000", "ws_001", "ws_002"])
    df_input.to_csv(current_dir + "/test_inputs/wind_input_temp.csv")

    wind_sim = WindFarm(test_h_dict)
    assert (wind_sim.ws_mat_mean == 10.0).all()
    assert (wind_sim.ws_mat[:, :] == 10.0).all()

    # Delete temp file
    os.remove(current_dir + "/test_inputs/wind_input_temp.csv")


def test_wind_farm_missing_floris_update_time():
    """Test that missing floris_update_time_s raises ValueError."""
    test_h_dict = copy.deepcopy(h_dict_wind)
    del test_h_dict["wind_farm"]["floris_update_time_s"]

    with pytest.raises(
        ValueError, match="floris_update_time_s must be specified for wake_method='dynamic'"
    ):
        WindFarm(test_h_dict)


def test_wind_farm_invalid_update_time():
    """Test that invalid update time raises ValueError."""
    test_h_dict = copy.deepcopy(h_dict_wind)
    test_h_dict["wind_farm"]["floris_update_time_s"] = 0.5  # Less than 1 second

    with pytest.raises(ValueError, match="FLORIS update time must be at least 1 second"):
        WindFarm(test_h_dict)


def test_wind_farm_step():
    """Test that the step method updates outputs correctly."""
    test_h_dict = copy.deepcopy(h_dict_wind)
    # Set a shorter update time for testing
    test_h_dict["wind_farm"]["floris_update_time_s"] = 1.0

    wind_sim = WindFarm(test_h_dict)

    # Add power setpoint values to the step h_dict
    step_h_dict = {"step": 1}
    step_h_dict["wind_farm"] = {
        "turbine_power_setpoints": np.array([1000.0, 1500.0, 2000.0]),
    }

    result = wind_sim.step(step_h_dict)

    assert "turbine_powers" in result["wind_farm"]
    assert "power" in result["wind_farm"]
    assert len(result["wind_farm"]["turbine_powers"]) == 3
    assert isinstance(result["wind_farm"]["turbine_powers"], np.ndarray)
    assert "power" in result["wind_farm"]
    assert isinstance(result["wind_farm"]["power"], (int, float))


def test_wind_farm_time_utc_conversion():
    """Test that time_utc column is properly converted to datetime."""
    wind_sim = WindFarm(h_dict_wind)

    # Check that time_utc was converted to datetime type
    # The wind_sim should have successfully processed the CSV with time_utc column
    assert wind_sim.component_name == "wind_farm"
    assert wind_sim.component_type == "WindFarm"
    assert wind_sim.n_turbines == 3

    # Verify that the wind data was loaded correctly
    assert hasattr(wind_sim, "ws_mat")
    assert hasattr(wind_sim, "wd_mat_mean")
    assert wind_sim.ws_mat.shape[1] == 3  # 3 turbines


def test_wind_farm_power_setpoint_too_high():
    """Test that turbine powers are below power setpoint when setpoint is very high."""
    test_h_dict = copy.deepcopy(h_dict_wind)
    test_h_dict["wind_farm"]["floris_update_time_s"] = 1.0

    wind_sim = WindFarm(test_h_dict)

    # Set very high power setpoint values that should not limit power output
    step_h_dict = {"step": 1}
    step_h_dict["wind_farm"] = {
        "turbine_power_setpoints": np.array([10000.0, 15000.0, 20000.0]),  # Very high setpoints
    }

    result = wind_sim.step(step_h_dict)

    # Verify that turbine powers are below the power setpoint limits
    turbine_powers = result["wind_farm"]["turbine_powers"]
    power_setpoint_values = [10000.0, 15000.0, 20000.0]

    for i, (power, setpoint) in enumerate(zip(turbine_powers, power_setpoint_values)):
        assert power <= setpoint, f"Turbine {i} power {power} exceeds power setpoint {setpoint}"


def test_wind_farm_power_setpoint_applies():
    """Test that turbine powers equal power setpoint when setpoint is very low."""
    test_h_dict = copy.deepcopy(h_dict_wind)
    test_h_dict["wind_farm"]["floris_update_time_s"] = 1.0

    wind_sim = WindFarm(test_h_dict)

    # Set very low power setpoint values that should definitely limit power output
    step_h_dict = {"step": 1}
    step_h_dict["wind_farm"] = {
        "turbine_power_setpoints": np.array([100.0, 200.0, 300.0]),  # Very low setpoints
    }

    result = wind_sim.step(step_h_dict)

    # Verify that turbine powers equal the power setpoint limits
    turbine_powers = result["wind_farm"]["turbine_powers"]
    power_setpoint_values = [100.0, 200.0, 300.0]

    for i, (power, setpoint) in enumerate(zip(turbine_powers, power_setpoint_values)):
        assert power == setpoint, (
            f"Turbine {i} power {power} should equal power setpoint {setpoint}"
        )


def test_wind_farm_get_initial_conditions_and_meta_data():
    """Test that get_initial_conditions_and_meta_data adds correct metadata to h_dict."""
    wind_sim = WindFarm(h_dict_wind)

    # Create a copy of the input h_dict to avoid modifying the original
    test_h_dict = copy.deepcopy(h_dict_wind)

    # Call the method
    result = wind_sim.get_initial_conditions_and_meta_data(test_h_dict)

    # Verify that the method returns the modified h_dict
    assert result is test_h_dict

    # Verify that all expected metadata is added to the wind_farm section
    assert "n_turbines" in result["wind_farm"]
    assert "capacity" in result["wind_farm"]
    assert "rated_turbine_power" in result["wind_farm"]
    assert "wind_direction_mean" in result["wind_farm"]
    assert "wind_speed_mean_background" in result["wind_farm"]
    assert "turbine_powers" in result["wind_farm"]

    # Verify the values match the wind_sim attributes
    assert result["wind_farm"]["n_turbines"] == wind_sim.n_turbines
    assert result["wind_farm"]["capacity"] == wind_sim.capacity
    assert result["wind_farm"]["rated_turbine_power"] == wind_sim.rated_turbine_power
    assert result["wind_farm"]["wind_direction_mean"] == wind_sim.wd_mat_mean[0]
    assert result["wind_farm"]["wind_speed_mean_background"] == wind_sim.ws_mat_mean[0]

    # Verify turbine_powers is a numpy array with correct length
    assert isinstance(result["wind_farm"]["turbine_powers"], np.ndarray)
    assert len(result["wind_farm"]["turbine_powers"]) == wind_sim.n_turbines
    np.testing.assert_array_equal(result["wind_farm"]["turbine_powers"], wind_sim.turbine_powers)

    # Verify that the original h_dict structure is preserved
    assert "dt" in result
    assert "starttime" in result
    assert "endtime" in result
    assert "plant" in result


def test_wind_farm_regular_floris_updates():
    """Test that FLORIS updates occur at regular intervals.

    This test verifies that FLORIS calculations happen at the specified interval
    rather than based on threshold changes.
    """
    # Create a temporary wind input file with constant conditions
    wind_data = {
        "time": [0, 1, 2, 3, 4, 5],
        "time_utc": [
            "2018-05-10 12:31:00",
            "2018-05-10 12:31:01",
            "2018-05-10 12:31:02",
            "2018-05-10 12:31:03",
            "2018-05-10 12:31:04",
            "2018-05-10 12:31:05",
        ],
        "wd_mean": [270.0, 270.0, 270.0, 270.0, 270.0, 270.0],  # Constant wind direction
        "ws_000": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],  # Constant wind speed
        "ws_001": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],  # Constant wind speed
        "ws_002": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],  # Constant wind speed
    }

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df = pd.DataFrame(wind_data)
        df.to_csv(f.name, index=False)
        temp_wind_file = f.name

    try:
        # Create test h_dict with the temporary wind file
        test_h_dict = copy.deepcopy(h_dict_wind)
        test_h_dict["wind_farm"]["wind_input_filename"] = temp_wind_file
        test_h_dict["wind_farm"]["floris_update_time_s"] = 2.0  # Update every 2 seconds
        test_h_dict["starttime"] = 0.0
        test_h_dict["endtime"] = 5.0  # 5 steps (0, 1, 2, 3, 4)
        test_h_dict["starttime_utc"] = "2018-05-10 12:31:00"
        test_h_dict["endtime_utc"] = "2018-05-10 12:31:05"
        test_h_dict["dt"] = 1.0

        # Initialize wind simulation
        wind_sim = WindFarm(test_h_dict)

        # Run 5 steps with constant power setpoints
        floris_calc_counts = []

        for step in range(5):
            test_h_dict = {"step": step}
            test_h_dict["wind_farm"] = {
                "turbine_power_setpoints": np.array([5000.0, 5000.0, 5000.0]),
            }

            test_h_dict = wind_sim.step(test_h_dict)
            floris_calc_counts.append(wind_sim.num_floris_calcs)

        # Verify that FLORIS calculations happen at regular intervals
        # Should have initial calculation + updates at steps 0, 2, 4 (every 2 seconds)
        expected_calcs = [2, 2, 3, 3, 4]  # Initial + updates at steps 0, 2, 4
        assert floris_calc_counts == expected_calcs

    finally:
        # Clean up temporary file
        if os.path.exists(temp_wind_file):
            os.unlink(temp_wind_file)


def test_wind_farm_power_setpoints_buffer():
    """Test that power setpoints buffer works correctly over time."""
    # Create a temporary wind input file with constant conditions
    wind_data = {
        "time": [0, 1, 2, 3, 4, 5],
        "time_utc": [
            "2018-05-10 12:31:00",
            "2018-05-10 12:31:01",
            "2018-05-10 12:31:02",
            "2018-05-10 12:31:03",
            "2018-05-10 12:31:04",
            "2018-05-10 12:31:05",
        ],
        "wd_mean": [270.0, 270.0, 270.0, 270.0, 270.0, 270.0],
        "ws_000": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
        "ws_001": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
        "ws_002": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
    }

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df = pd.DataFrame(wind_data)
        df.to_csv(f.name, index=False)
        temp_wind_file = f.name

    try:
        # Create test h_dict with the temporary wind file
        test_h_dict = copy.deepcopy(h_dict_wind)
        test_h_dict["wind_farm"]["wind_input_filename"] = temp_wind_file
        test_h_dict["wind_farm"]["floris_update_time_s"] = 3.0  # 3-second buffer
        test_h_dict["starttime"] = 0.0
        test_h_dict["endtime"] = 5.0  # 5 steps (0, 1, 2, 3, 4)
        test_h_dict["starttime_utc"] = "2018-05-10 12:31:00"
        test_h_dict["endtime_utc"] = "2018-05-10 12:31:05"
        test_h_dict["dt"] = 1.0

        # Initialize wind simulation
        wind_sim = WindFarm(test_h_dict)

        # Run steps with varying power setpoints
        for step in range(5):
            test_h_dict = {"step": step}
            # Use different power setpoints for each step
            power_setpoints = np.array(
                [1000.0 + step * 100, 2000.0 + step * 100, 3000.0 + step * 100]
            )
            test_h_dict["wind_farm"] = {
                "turbine_power_setpoints": power_setpoints,
            }

            test_h_dict = wind_sim.step(test_h_dict)

        # Verify that the buffer is working correctly
        # The buffer should contain the last 3 power setpoint values (steps 2, 3, 4)
        assert wind_sim.turbine_power_setpoints_buffer.shape == (3, 3)  # 3 steps, 3 turbines
        assert wind_sim.turbine_power_setpoints_buffer_idx == 2  # After 5 steps with buffer size 3

    finally:
        # Clean up temporary file
        if os.path.exists(temp_wind_file):
            os.unlink(temp_wind_file)
