"""Tests for the WindFarm class in direct wake mode (WindFarm with no_added_wakes)."""

import copy

import numpy as np
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
    assert isinstance(result["wind_farm"]["power"], (int, float))

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
