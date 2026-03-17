"""Tests for the WindFarm class in direct wake mode (WindFarm with no_added_wakes)."""

import copy
import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from hercules.plant_components.wind_farm import WindFarm
from hercules.utilities import hercules_float_type

from tests.test_inputs.h_dict import h_dict_wind

# Create a base test dictionary for no_added_wakes
h_dict_wind_direct = copy.deepcopy(h_dict_wind)
# Update component type
h_dict_wind_direct["wind_farm"]["wake_method"] = "no_added_wakes"


def test_wind_farm_direct_initialization():
    """Test that WindFarm initializes correctly with wake_method='no_added_wakes'."""
    wind_sim = WindFarm(h_dict_wind_direct, "wind_farm")

    assert wind_sim.component_name == "wind_farm"
    assert wind_sim.component_type == "WindFarm"
    assert wind_sim.wake_method == "no_added_wakes"
    assert wind_sim.n_turbines == 3
    assert wind_sim.dt == 1.0
    assert wind_sim.starttime == 0.0
    assert wind_sim.endtime == 10.0
    # No FLORIS calculations in direct mode
    assert wind_sim.num_floris_calcs == 0
    assert wind_sim.floris_update_time_s is None


def test_wind_farm_direct_no_wakes():
    """Test that no wake deficits are applied in direct mode."""
    wind_sim = WindFarm(h_dict_wind_direct, "wind_farm")

    # Verify initial wake deficits are zero
    assert np.all(wind_sim.floris_wake_deficits == 0.0)

    # Verify initial wind speeds with wakes equal background
    assert np.allclose(wind_sim.wind_speeds_withwakes, wind_sim.wind_speeds_background)


def test_wind_farm_direct_step():
    """Test that the step method works correctly in direct mode."""
    wind_sim = WindFarm(h_dict_wind_direct, "wind_farm")

    # Add power setpoint values to the step h_dict
    step_h_dict = {"step": 1}
    step_h_dict["wind_farm"] = {
        "turbine_power_setpoints": np.array([1000.0, 1500.0, 2000.0]),
    }

    result = wind_sim.step(step_h_dict)

    # Verify outputs exist
    assert "turbine_powers" in result["wind_farm"]
    assert "power" in result["wind_farm"]
    assert len(result["wind_farm"]["turbine_powers"]) == 3
    assert isinstance(result["wind_farm"]["turbine_powers"], np.ndarray)
    assert "power" in result["wind_farm"]
    assert isinstance(result["wind_farm"]["power"], (int, float, hercules_float_type))

    # Verify no wake deficits applied
    assert np.all(wind_sim.floris_wake_deficits == 0.0)
    assert np.allclose(
        result["wind_farm"]["wind_speeds_withwakes"],
        result["wind_farm"]["wind_speeds_background"],
    )


def test_wind_farm_direct_no_wake_deficits_over_time():
    """Test that wake deficits remain zero throughout simulation."""
    wind_sim = WindFarm(h_dict_wind_direct, "wind_farm")

    # Run multiple steps
    for step in range(5):
        step_h_dict = {"step": step}
        step_h_dict["wind_farm"] = {
            "turbine_power_setpoints": np.ones(3, dtype=hercules_float_type) * 5000.0,
        }

        result = wind_sim.step(step_h_dict)

        # Verify no wakes at each step
        assert np.all(wind_sim.floris_wake_deficits == 0.0)
        assert np.allclose(
            result["wind_farm"]["wind_speeds_withwakes"],
            result["wind_farm"]["wind_speeds_background"],
        )


def test_wind_farm_direct_turbine_dynamics():
    """Test that turbine dynamics still work in direct mode."""
    wind_sim = WindFarm(h_dict_wind_direct, "wind_farm")

    # Run a step with very low power setpoint
    step_h_dict = {"step": 1}
    step_h_dict["wind_farm"] = {
        "turbine_power_setpoints": np.array([100.0, 100.0, 100.0]),
    }

    result = wind_sim.step(step_h_dict)

    # Turbine powers should be limited by setpoint
    assert np.all(result["wind_farm"]["turbine_powers"] <= 100.0 + 1e-6)


def test_wind_farm_direct_power_setpoint_zero():
    """Test that turbine powers go to zero when setpoint is zero."""
    wind_sim = WindFarm(h_dict_wind_direct, "wind_farm")

    # Run multiple steps with zero setpoint to ensure filter settles
    for step in range(10):
        step_h_dict = {"step": step}
        step_h_dict["wind_farm"] = {
            "turbine_power_setpoints": np.zeros(3, dtype=hercules_float_type),
        }
        result = wind_sim.step(step_h_dict)

    # After multiple steps, powers should be effectively zero
    assert np.all(result["wind_farm"]["turbine_powers"] < 1.0)


def test_wind_farm_direct_initial_conditions():
    """Test that initial conditions are correctly set in h_dict."""
    wind_sim = WindFarm(h_dict_wind_direct, "wind_farm")

    initial_h_dict = copy.deepcopy(h_dict_wind_direct)
    result_h_dict = wind_sim.get_initial_conditions_and_meta_data(initial_h_dict)

    assert "n_turbines" in result_h_dict["wind_farm"]
    assert "capacity" in result_h_dict["wind_farm"]
    assert "rated_turbine_power" in result_h_dict["wind_farm"]
    assert "wind_direction_mean" in result_h_dict["wind_farm"]
    assert "wind_speed_mean_background" in result_h_dict["wind_farm"]
    assert "turbine_powers" in result_h_dict["wind_farm"]
    assert "power" in result_h_dict["wind_farm"]

    assert result_h_dict["wind_farm"]["n_turbines"] == 3
    assert result_h_dict["wind_farm"]["capacity"] > 0
    assert result_h_dict["wind_farm"]["rated_turbine_power"] > 0


def test_wind_farm_direct_output_consistency():
    """Test that outputs are consistent with no wake modeling."""
    wind_sim = WindFarm(h_dict_wind_direct, "wind_farm")

    # Run a step
    step_h_dict = {"step": 2}
    step_h_dict["wind_farm"] = {
        "turbine_power_setpoints": np.ones(3, dtype=hercules_float_type) * 5000.0,
    }

    result = wind_sim.step(step_h_dict)

    # Calculate expected mean withwakes speed (should equal background mean)
    expected_mean_withwakes = np.mean(
        result["wind_farm"]["wind_speeds_background"], dtype=hercules_float_type
    )

    assert np.isclose(result["wind_farm"]["wind_speed_mean_withwakes"], expected_mean_withwakes)

    # Total power should be sum of turbine powers
    assert np.isclose(result["wind_farm"]["power"], np.sum(result["wind_farm"]["turbine_powers"]))


def test_wind_farm_raises_on_nan_in_wind_input():
    """Test that WindFarm raises ValueError when wind input file contains NaN values."""
    wind_data = {
        "time_utc": [
            "2018-05-10 12:31:00",
            "2018-05-10 12:31:01",
            "2018-05-10 12:31:02",
            "2018-05-10 12:31:03",
            "2018-05-10 12:31:04",
            "2018-05-10 12:31:05",
            "2018-05-10 12:31:06",
            "2018-05-10 12:31:07",
            "2018-05-10 12:31:08",
            "2018-05-10 12:31:09",
            "2018-05-10 12:31:10",
        ],
        "wd_mean": [180.5, 185.2, 190.8, 175.3, 170.1, 165.7, 160.4, 155.9, 150.2, 145.6, 140.3],
        "ws_000": [8.2, np.nan, 7.8, 6.5, 10.2, 11.5, 9.8, 8.7, 7.3, 6.9, 8.4],
        "ws_001": [8.1, 9.0, 7.7, 6.4, 10.1, 11.4, 9.7, 8.6, 7.2, 6.8, 8.3],
        "ws_002": [8.3, 9.2, 7.9, 6.6, 10.3, 11.6, 9.9, 8.8, 7.4, 7.0, 8.5],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        pd.DataFrame(wind_data).to_csv(f.name, index=False)
        temp_wind_file = f.name

    try:
        test_h_dict = copy.deepcopy(h_dict_wind_direct)
        test_h_dict["wind_farm"]["wind_input_filename"] = temp_wind_file

        with pytest.raises(ValueError, match="wind input file contains NaN values"):
            WindFarm(test_h_dict, "wind_farm")
    finally:
        if os.path.exists(temp_wind_file):
            os.unlink(temp_wind_file)
