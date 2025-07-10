"""Tests for the WindSimLongTerm class."""

import numpy as np
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
