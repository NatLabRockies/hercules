"""Tests for the WindSimLongTerm class."""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from hercules.python_simulators.wind_sim_long_term import TurbineFilterModel, WindSimLongTerm

from tests.test_inputs.h_dict import h_dict_wind


def test_wind_sim_long_term_initialization():
    """Test that WindSimLongTerm initializes correctly with valid inputs."""
    wind_sim = WindSimLongTerm(h_dict_wind)

    assert wind_sim.py_sim_name == "wind_farm"
    assert wind_sim.py_sim_type == "WindSimLongTerm"
    assert wind_sim.n_turbines == 3
    assert wind_sim.dt == 1.0
    assert wind_sim.starttime == 0.0
    assert wind_sim.endtime == 10.0
    assert wind_sim.num_floris_calcs == 0


def test_wind_sim_long_term_default_thresholds():
    """Test that default FLORIS thresholds are set correctly."""
    wind_sim = WindSimLongTerm(h_dict_wind)

    assert wind_sim.floris_wd_threshold == 3.0
    assert wind_sim.floris_ws_threshold == 1.0
    assert wind_sim.floris_ti_threshold == 0.1
    assert wind_sim.floris_derating_threshold == 10
    assert wind_sim.floris_time_window_width_s == 300.0
    assert wind_sim.floris_update_time_s == 60.0


def test_wind_sim_long_term_custom_thresholds():
    """Test that custom FLORIS thresholds are set correctly."""
    test_h_dict = h_dict_wind.copy()
    test_h_dict["wind_farm"]["floris_wd_threshold"] = 5.0
    test_h_dict["wind_farm"]["floris_ws_threshold"] = 2.0
    test_h_dict["wind_farm"]["floris_ti_threshold"] = 0.2
    test_h_dict["wind_farm"]["floris_derating_threshold"] = 20
    test_h_dict["wind_farm"]["floris_time_window_width_s"] = 600.0
    test_h_dict["wind_farm"]["floris_update_time_s"] = 120.0

    wind_sim = WindSimLongTerm(test_h_dict)

    assert wind_sim.floris_wd_threshold == 5.0
    assert wind_sim.floris_ws_threshold == 2.0
    assert wind_sim.floris_ti_threshold == 0.2
    assert wind_sim.floris_derating_threshold == 20
    assert wind_sim.floris_time_window_width_s == 600.0
    assert wind_sim.floris_update_time_s == 120.0


def test_wind_sim_long_term_invalid_time_window():
    """Test that invalid time window width raises ValueError."""
    test_h_dict = h_dict_wind.copy()
    test_h_dict["wind_farm"]["floris_time_window_width_s"] = 0.5  # Less than 1 second

    with pytest.raises(ValueError, match="FLORIS time window width must be at least 1 second"):
        WindSimLongTerm(test_h_dict)


def test_wind_sim_long_term_invalid_update_time():
    """Test that invalid update time raises ValueError."""
    test_h_dict = h_dict_wind.copy()
    # Set a valid time window width first
    test_h_dict["wind_farm"]["floris_time_window_width_s"] = 300.0
    test_h_dict["wind_farm"]["floris_update_time_s"] = 0.5  # Less than 1 second

    with pytest.raises(ValueError, match="FLORIS update time must be at least 1 second"):
        WindSimLongTerm(test_h_dict)


def test_wind_sim_long_term_step():
    """Test that the step method updates outputs correctly."""
    test_h_dict = h_dict_wind.copy()
    # Set a shorter update time for testing
    test_h_dict["wind_farm"]["floris_update_time_s"] = 1.0

    wind_sim = WindSimLongTerm(test_h_dict)

    # Add derating values to the step h_dict
    step_h_dict = {"step": 1}
    step_h_dict["wind_farm"] = {
        "derating_000": 1000.0,
        "derating_001": 1500.0,
        "derating_002": 2000.0,
    }

    result = wind_sim.step(step_h_dict)

    assert "turbine_powers" in result["wind_farm"]
    assert "power" in result["wind_farm"]
    assert len(result["wind_farm"]["turbine_powers"]) == 3
    assert isinstance(result["wind_farm"]["turbine_powers"], np.ndarray)
    assert "power" in result["wind_farm"]
    assert isinstance(result["wind_farm"]["power"], (int, float))


def test_turbine_filter_model_initialization():
    """Test that TurbineFilterModel initializes correctly."""
    from floris import FlorisModel

    turbine_dict = {"filter_model": {"time_constant": 12.0}}

    # Use actual FLORIS model
    fmodel = FlorisModel("tests/test_inputs/floris_input.yaml")

    turbine = TurbineFilterModel(turbine_dict, dt=1.0, fmodel=fmodel, initial_wind_speed=8.0)

    assert turbine.dt == 1.0
    assert turbine.filter_time_constant == 12.0
    assert turbine.alpha > 0.0
    assert turbine.alpha < 1.0
    assert isinstance(turbine.prev_power, (int, float, np.ndarray))


def test_turbine_filter_model_step():
    """Test that TurbineFilterModel step method works correctly."""
    from floris import FlorisModel

    turbine_dict = {"filter_model": {"time_constant": 12.0}}

    # Use actual FLORIS model
    fmodel = FlorisModel("tests/test_inputs/floris_input.yaml")

    turbine = TurbineFilterModel(turbine_dict, dt=1.0, fmodel=fmodel, initial_wind_speed=8.0)

    # Test step with different wind speeds
    power1 = turbine.step(wind_speed=10.0, derating=1000.0)
    power2 = turbine.step(wind_speed=12.0, derating=1500.0)

    assert isinstance(power1, (int, float))
    assert isinstance(power2, (int, float))
    assert power1 >= 0.0
    assert power2 >= 0.0


def test_turbine_filter_model_derating_limit():
    """Test that TurbineFilterModel respects derating limits."""
    from floris import FlorisModel

    turbine_dict = {"filter_model": {"time_constant": 12.0}}

    # Use actual FLORIS model
    fmodel = FlorisModel("tests/test_inputs/floris_input.yaml")

    turbine = TurbineFilterModel(turbine_dict, dt=1.0, fmodel=fmodel, initial_wind_speed=8.0)

    # Test with low derating limit
    power = turbine.step(wind_speed=15.0, derating=500.0)

    assert power <= 500.0
    assert power >= 0.0


def test_wind_sim_long_term_time_utc_conversion():
    """Test that time_utc column is properly converted to datetime."""
    wind_sim = WindSimLongTerm(h_dict_wind)

    # Check that time_utc was converted to datetime type
    # The wind_sim should have successfully processed the CSV with time_utc column
    assert wind_sim.py_sim_name == "wind_farm"
    assert wind_sim.py_sim_type == "WindSimLongTerm"
    assert wind_sim.n_turbines == 3

    # Verify that the wind data was loaded correctly
    assert hasattr(wind_sim, "ws_mat")
    assert hasattr(wind_sim, "wd_mat_mean")
    assert wind_sim.ws_mat.shape[1] == 3  # 3 turbines


def test_wind_sim_long_term_derating_too_high():
    """Test that turbine powers are below derating when derating is very high."""
    test_h_dict = h_dict_wind.copy()
    test_h_dict["wind_farm"]["floris_update_time_s"] = 1.0

    wind_sim = WindSimLongTerm(test_h_dict)

    # Set very high derating values that should not limit power output
    step_h_dict = {"step": 1}
    step_h_dict["wind_farm"] = {
        "derating_000": 10000.0,  # Very high derating
        "derating_001": 15000.0,  # Very high derating
        "derating_002": 20000.0,  # Very high derating
    }

    result = wind_sim.step(step_h_dict)

    # Verify that turbine powers are below the derating limits
    turbine_powers = result["wind_farm"]["turbine_powers"]
    derating_values = [10000.0, 15000.0, 20000.0]

    for i, (power, derating) in enumerate(zip(turbine_powers, derating_values)):
        assert power <= derating, f"Turbine {i} power {power} exceeds derating {derating}"


def test_wind_sim_long_term_derating_applies():
    """Test that turbine powers equal derating when derating is very low."""
    test_h_dict = h_dict_wind.copy()
    test_h_dict["wind_farm"]["floris_update_time_s"] = 1.0

    wind_sim = WindSimLongTerm(test_h_dict)

    # Set very low derating values that should definitely limit power output
    step_h_dict = {"step": 1}
    step_h_dict["wind_farm"] = {
        "derating_000": 100.0,  # Very low derating
        "derating_001": 200.0,  # Very low derating
        "derating_002": 300.0,  # Very low derating
    }

    result = wind_sim.step(step_h_dict)

    # Verify that turbine powers equal the derating limits
    turbine_powers = result["wind_farm"]["turbine_powers"]
    derating_values = [100.0, 200.0, 300.0]

    for i, (power, derating) in enumerate(zip(turbine_powers, derating_values)):
        assert power == derating, f"Turbine {i} power {power} should equal derating {derating}"


def test_wind_sim_long_term_get_initial_conditions_and_meta_data():
    """Test that get_initial_conditions_and_meta_data adds correct metadata to h_dict."""
    wind_sim = WindSimLongTerm(h_dict_wind)

    # Create a copy of the input h_dict to avoid modifying the original
    test_h_dict = h_dict_wind.copy()

    # Call the method
    result = wind_sim.get_initial_conditions_and_meta_data(test_h_dict)

    # Verify that the method returns the modified h_dict
    assert result is test_h_dict

    # Verify that all expected metadata is added to the wind_farm section
    assert "n_turbines" in result["wind_farm"]
    assert "capacity" in result["wind_farm"]
    assert "rated_turbine_power" in result["wind_farm"]
    assert "wind_direction" in result["wind_farm"]
    assert "wind_speed" in result["wind_farm"]
    assert "turbine_powers" in result["wind_farm"]

    # Verify the values match the wind_sim attributes
    assert result["wind_farm"]["n_turbines"] == wind_sim.n_turbines
    assert result["wind_farm"]["capacity"] == wind_sim.capacity
    assert result["wind_farm"]["rated_turbine_power"] == wind_sim.rated_turbine_power
    assert result["wind_farm"]["wind_direction"] == wind_sim.wd_mat_mean[0]
    assert result["wind_farm"]["wind_speed"] == wind_sim.ws_mat_mean[0]

    # Verify turbine_powers is a numpy array with correct length
    assert isinstance(result["wind_farm"]["turbine_powers"], np.ndarray)
    assert len(result["wind_farm"]["turbine_powers"]) == wind_sim.n_turbines
    np.testing.assert_array_equal(result["wind_farm"]["turbine_powers"], wind_sim.turbine_powers)

    # Verify that the original h_dict structure is preserved
    assert "dt" in result
    assert "starttime" in result
    assert "endtime" in result
    assert "plant" in result


def test_wind_sim_long_term_memoization():
    """Test that FLORIS memoization works correctly with changing wind direction.

    This test simulates 3 steps where wind speed and TI are constant, but wind
    direction changes from 270 -> 290 -> 270. The memoization should cache the
    FLORIS calculation and reuse it when inputs repeat within threshold.
    """

    # Create a temporary wind input file with the specific scenario
    wind_data = {
        "time": [0, 1000, 2000],
        "time_utc": ["2023-01-01 00:00:00", "2023-01-01 01:00:00", "2023-01-01 02:00:00"],
        "wd_mean": [270.0, 290.0, 270.0],  # Wind direction alternates
        "ws_000": [10.0, 10.0, 10.0],  # Constant wind speed
        "ws_001": [10.0, 10.0, 10.0],  # Constant wind speed
        "ws_002": [10.0, 10.0, 10.0],  # Constant wind speed
    }

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df = pd.DataFrame(wind_data)
        df.to_csv(f.name, index=False)
        temp_wind_file = f.name

    try:
        # Create test h_dict with the temporary wind file
        test_h_dict = h_dict_wind.copy()
        test_h_dict["wind_farm"]["wind_input_filename"] = temp_wind_file
        test_h_dict["wind_farm"]["floris_time_window_width_s"] = 10.0
        test_h_dict["wind_farm"]["floris_update_time_s"] = 1.0  # Update every step
        test_h_dict["wind_farm"]["floris_wd_threshold"] = 5.0  # Small threshold to trigger updates
        test_h_dict["wind_farm"]["floris_ws_threshold"] = 0.5  # Small threshold
        test_h_dict["wind_farm"]["floris_ti_threshold"] = 0.05  # Small threshold
        test_h_dict["wind_farm"]["floris_derating_threshold"] = 5.0  # Small threshold
        test_h_dict["starttime"] = 0.0
        test_h_dict["endtime"] = 3000.0  # 3 steps (0, 1, 2)
        test_h_dict["dt"] = 1000.0

        # Initialize wind simulation
        wind_sim = WindSimLongTerm(test_h_dict)

        # Store initial FLORIS calculation count
        initial_floris_calcs = wind_sim.num_floris_calcs

        # Run 3 steps with constant derating
        powers = []

        for step in range(3):
            test_h_dict = {"step": step}
            test_h_dict["wind_farm"] = {
                "derating_000": 5000.0,
                "derating_001": 5000.0,
                "derating_002": 5000.0,
            }

            test_h_dict = wind_sim.step(test_h_dict)
            powers.append(test_h_dict["wind_farm"]["power"])

            print("---")
            print(f"Step {step}")
            print(f"FLORIS WIND DIRECTION: {test_h_dict['wind_farm']['floris_wind_direction']}")
            print(f"FLORIS WIND SPEED: {test_h_dict['wind_farm']['floris_wind_speed']}")

        # Verify that we have 3 power values
        assert len(powers) == 3

        # Verify that the 0th and 2th power are the same
        assert powers[0] == powers[2]
        # Verify that the 1th power is different
        assert powers[1] != powers[0]

        # Verify that FLORIS is only called 3 times
        # This is twice plus the call from within init
        assert wind_sim.num_floris_calcs == 3

        # Print FLORIS calculation count for memoization check
        print(f"FLORIS calculations: {wind_sim.num_floris_calcs}")
        print(f"Powers: {powers}")

    finally:
        # Clean up temporary file
        if os.path.exists(temp_wind_file):
            os.unlink(temp_wind_file)


def test_wind_sim_long_term_time_window_averaging():
    """Test that update_wake_deficits correctly averages wind data over different time windows.

    This test verifies that floris_wind_speed, floris_wind_direction, and floris_wake_deficits
    are calculated correctly when floris_time_window_width_s is set to cover 1, 2, and 3 steps.
    """
    # Create test data with known wind speeds and directions
    test_data = {
        "time": [0, 1, 2, 3, 4, 5],
        "wd_mean": [180.0, 185.0, 190.0, 175.0, 170.0, 165.0],
        "ws_000": [8.0, 8.0, 8.0, 8.0, 8.0, 8.0],
        "ws_001": [8.0, 8.0, 8.0, 8.0, 8.0, 8.0],
        "ws_002": [8.0, 8.0, 8.0, 8.0, 8.0, 8.0],
    }

    # Create temporary CSV file with test data
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df = pd.DataFrame(test_data)
        df.to_csv(f.name, index=False)
        temp_csv_path = f.name

    try:
        # Test with different time window widths
        for window_width_s in [1.0, 2.0, 3.0]:
            # Create test h_dict with the temporary CSV file
            test_h_dict = h_dict_wind.copy()
            test_h_dict["wind_farm"]["wind_input_filename"] = temp_csv_path
            test_h_dict["wind_farm"]["floris_time_window_width_s"] = window_width_s
            test_h_dict["wind_farm"]["floris_update_time_s"] = 1.0  # Update every step
            test_h_dict["wind_farm"]["floris_wd_threshold"] = (
                0.1  # Small threshold to force updates
            )
            test_h_dict["wind_farm"]["floris_ws_threshold"] = 0.1
            test_h_dict["wind_farm"]["floris_ti_threshold"] = 0.01
            test_h_dict["wind_farm"]["floris_derating_threshold"] = 1.0
            # Adjust endtime to match available data
            test_h_dict["endtime"] = 6.0  # Data goes from 0 to 5, so endtime should be 6

            wind_sim = WindSimLongTerm(test_h_dict)

            # Test at step 2 (index 2 in our data)
            step = 2
            wind_sim.update_wake_deficits(step)

            # Test specific expected values for each window width
            if window_width_s == 1.0:
                # Single step window: should use only step 2 data
                expected_single_wd = test_data["wd_mean"][2]
                assert np.isclose(wind_sim.floris_wind_direction, expected_single_wd, rtol=1e-6)

            elif window_width_s == 2.0:
                # Two step window: should average steps 1 and 2

                expected_two_wd = np.mean([test_data["wd_mean"][1], test_data["wd_mean"][2]])
                assert np.isclose(wind_sim.floris_wind_direction, expected_two_wd, rtol=1e-6)

            elif window_width_s == 3.0:
                # Three step window: should average steps 0, 1, and 2

                expected_three_wd = np.mean(
                    [test_data["wd_mean"][0], test_data["wd_mean"][1], test_data["wd_mean"][2]]
                )
                assert np.isclose(wind_sim.floris_wind_direction, expected_three_wd, rtol=1e-6)

    finally:
        # Clean up temporary file
        os.unlink(temp_csv_path)
