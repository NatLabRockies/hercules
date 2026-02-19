import copy

import pytest
from hercules.plant_components.thermal_component_base import ThermalComponentBase

from .test_inputs.h_dict import (
    h_dict_thermal_component,
)


def test_init_from_dict():
    """Test that ThermalComponentBase can be initialized from a dictionary."""
    tpb = ThermalComponentBase(copy.deepcopy(h_dict_thermal_component))
    assert tpb is not None


def test_invalid_inputs():
    """Test that ThermalComponentBase raises an error for invalid inputs."""

    # Test input must be a number
    h_dict = copy.deepcopy(h_dict_thermal_component)
    h_dict["thermal_component"]["rated_capacity"] = "1000"
    with pytest.raises(ValueError):
        ThermalComponentBase(h_dict)

    # Test min_stable_load_fraction must be between 0 and 1
    h_dict = copy.deepcopy(h_dict_thermal_component)
    h_dict["thermal_component"]["min_stable_load_fraction"] = 1.1
    with pytest.raises(ValueError):
        ThermalComponentBase(h_dict)
    h_dict["thermal_component"]["min_stable_load_fraction"] = -0.1
    with pytest.raises(ValueError):
        ThermalComponentBase(h_dict)

    # Test ramp_rate_fraction must be a number greater than 0
    h_dict = copy.deepcopy(h_dict_thermal_component)
    h_dict["thermal_component"]["ramp_rate_fraction"] = 0
    with pytest.raises(ValueError):
        ThermalComponentBase(h_dict)

    # Test run_up_rate_fraction must be a number greater than 0
    h_dict = copy.deepcopy(h_dict_thermal_component)
    h_dict["thermal_component"]["run_up_rate_fraction"] = 0
    with pytest.raises(ValueError):
        ThermalComponentBase(h_dict)

    # Test min_up_time must be a number greater than or equal to 0
    h_dict = copy.deepcopy(h_dict_thermal_component)
    h_dict["thermal_component"]["min_up_time"] = 0
    ThermalComponentBase(h_dict)
    h_dict["thermal_component"]["min_up_time"] = -1
    with pytest.raises(ValueError):
        ThermalComponentBase(h_dict)

    # Test min_down_time must be a number greater than or equal to 0
    h_dict = copy.deepcopy(h_dict_thermal_component)
    h_dict["thermal_component"]["min_down_time"] = 0
    ThermalComponentBase(h_dict)
    h_dict["thermal_component"]["min_down_time"] = -1
    with pytest.raises(ValueError):
        ThermalComponentBase(h_dict)

    # Test hot_startup_time must be a number greater than the ramp_time
    # determined by the run_up_rate_fraction
    h_dict = copy.deepcopy(h_dict_thermal_component)
    h_dict["thermal_component"]["min_stable_load_fraction"] = 0.2
    h_dict["thermal_component"]["run_up_rate_fraction"] = 0.2

    # The above implies a ramp_time of 60s
    h_dict["thermal_component"]["hot_startup_time"] = 59
    with pytest.raises(ValueError):
        ThermalComponentBase(h_dict)
    h_dict["thermal_component"]["hot_startup_time"] = 60
    ThermalComponentBase(h_dict)

    # Test cold_startup_time must be a number greater than or equal to the
    # hot_startup_time (which in this setup equals the ramp_time determined
    # by the run_up_rate_fraction)
    h_dict = copy.deepcopy(h_dict_thermal_component)
    h_dict["thermal_component"]["min_stable_load_fraction"] = 0.2
    h_dict["thermal_component"]["run_up_rate_fraction"] = 0.2

    # Lower hot and warm startup times to 60 seconds
    h_dict["thermal_component"]["hot_startup_time"] = 60
    h_dict["thermal_component"]["warm_startup_time"] = 60

    # The above implies a ramp_time of 60s
    h_dict["thermal_component"]["cold_startup_time"] = 59
    with pytest.raises(ValueError):
        ThermalComponentBase(h_dict)
    h_dict["thermal_component"]["cold_startup_time"] = 60
    ThermalComponentBase(h_dict)


def test_compute_ramp_and_readying_times():
    """Test that the ramp_time and readying times are computed correctly."""
    h_dict = copy.deepcopy(h_dict_thermal_component)
    h_dict["thermal_component"]["min_stable_load_fraction"] = 0.2
    h_dict["thermal_component"]["run_up_rate_fraction"] = 0.2

    # The above implies a ramp_time of 60s
    h_dict["thermal_component"]["hot_startup_time"] = 60
    h_dict["thermal_component"]["cold_startup_time"] = 120
    tcb = ThermalComponentBase(h_dict)
    assert tcb.ramp_time == 60
    assert tcb.hot_readying_time == 0
    assert tcb.cold_readying_time == 60


def test_initial_conditions():
    """Test that the initial conditions are set correctly."""

    # Test that power > 0 implies ON state
    h_dict = copy.deepcopy(h_dict_thermal_component)
    h_dict["thermal_component"]["initial_conditions"]["power"] = 1000
    tcb = ThermalComponentBase(h_dict)
    assert tcb.power_output == 1000
    assert tcb.state == ThermalComponentBase.STATES.ON
    # When ON, time_in_state should equal min_up_time (ready to stop)
    assert tcb.time_in_state == tcb.min_up_time

    # Test that power == 0 implies OFF state
    h_dict = copy.deepcopy(h_dict_thermal_component)
    h_dict["thermal_component"]["initial_conditions"]["power"] = 0
    tcb = ThermalComponentBase(h_dict)
    assert tcb.power_output == 0
    assert tcb.state == ThermalComponentBase.STATES.OFF
    # When OFF, time_in_state should equal min_down_time (ready to start)
    assert tcb.time_in_state == tcb.min_down_time

    # Check that invalid power values are rejected
    h_dict = copy.deepcopy(h_dict_thermal_component)
    h_dict["thermal_component"]["initial_conditions"]["power"] = -1
    with pytest.raises(ValueError):
        ThermalComponentBase(h_dict)
    h_dict["thermal_component"]["initial_conditions"]["power"] = 1100
    with pytest.raises(ValueError):
        ThermalComponentBase(h_dict)


def test_power_setpoint_in_normal_operation():
    """Test power setpoint control in normal operation."""
    h_dict = copy.deepcopy(h_dict_thermal_component)

    # Set the ramp rate to be 100 kW/s
    # Since the rated capacity is 1000 kW, and the ramp rate fraction is
    # fraction of rated capacity per minute we can compute the ramp rate fraction as
    # 100 kW/s / 1000 kW * 60 = 6
    h_dict["thermal_component"]["ramp_rate_fraction"] = 6

    # Set the initial conditions to be 500 kW (implies ON state)
    h_dict["thermal_component"]["initial_conditions"]["power"] = 500

    tcb = ThermalComponentBase(h_dict)

    # Set the power setpoint to the initial condition
    h_dict["thermal_component"]["power_setpoint"] = 500.0
    out = tcb.step(copy.deepcopy(h_dict))
    assert out["thermal_component"]["power"] == 500.0

    # Set the power setpoint to change by an amount less than the ramp rate
    h_dict["thermal_component"]["power_setpoint"] = 550  # kW
    out = tcb.step(copy.deepcopy(h_dict))
    assert out["thermal_component"]["power"] == 550.0

    # Set the power setpoint to change by an amount less than the ramp rate
    h_dict["thermal_component"]["power_setpoint"] = 500  # kW
    out = tcb.step(copy.deepcopy(h_dict))
    assert out["thermal_component"]["power"] == 500.0

    # Set the power setpoint to change by an amount greater than the ramp rate
    h_dict["thermal_component"]["power_setpoint"] = 650  # kW
    out = tcb.step(copy.deepcopy(h_dict))
    assert out["thermal_component"]["power"] == 600.0

    # Set the power setpoint to change by an amount greater than the ramp rate
    h_dict["thermal_component"]["power_setpoint"] = 400  # kW
    out = tcb.step(copy.deepcopy(h_dict))
    assert out["thermal_component"]["power"] == 500.0

    # Set the power setpoint to above the rated capacity and test that
    # it is constrained to the rated capacity
    h_dict["thermal_component"]["power_setpoint"] = 1100  # kW
    out = tcb.step(copy.deepcopy(h_dict))
    assert out["thermal_component"]["power"] == 600.0
    out = tcb.step(copy.deepcopy(h_dict))
    assert out["thermal_component"]["power"] == 700.0
    out = tcb.step(copy.deepcopy(h_dict))
    assert out["thermal_component"]["power"] == 800.0
    out = tcb.step(copy.deepcopy(h_dict))
    assert out["thermal_component"]["power"] == 900.0
    out = tcb.step(copy.deepcopy(h_dict))
    assert out["thermal_component"]["power"] == 1000.0
    out = tcb.step(copy.deepcopy(h_dict))
    assert out["thermal_component"]["power"] == 1000.0

    # Test that setting power setpoint to a negative number triggers the shutdown sequence
    h_dict["thermal_component"]["power_setpoint"] = -1
    out = tcb.step(copy.deepcopy(h_dict))
    assert out["thermal_component"]["state"] == ThermalComponentBase.STATES.STOPPING


def test_transition_on_to_off():
    """Test transition from on state to off state with ramp down and min_up_time."""
    h_dict = copy.deepcopy(h_dict_thermal_component)

    # Set the ramp rate to be 100 kW/s
    # Since the rated capacity is 1000 kW, and the ramp rate fraction is
    # fraction of rated capacity per minute we can compute the ramp rate fraction as
    # 100 kW/s / 1000 kW * 60 = 6
    h_dict["thermal_component"]["ramp_rate_fraction"] = 6

    # Set the initial conditions to be 500 kW (implies ON state)
    h_dict["thermal_component"]["initial_conditions"]["power"] = 500

    # Set the min_up_time to 5s
    h_dict["thermal_component"]["min_up_time"] = 5

    # Set the min_stable_load_fraction to be 0.2 (200 kW)
    h_dict["thermal_component"]["min_stable_load_fraction"] = 0.2

    tcb = ThermalComponentBase(h_dict)

    # Initial state: ON with time_in_state = min_up_time (5s, ready to stop)
    assert tcb.state == tcb.STATES.ON
    assert tcb.power_output == 500
    assert tcb.time_in_state == 5.0

    # Force time_in_state to 0 to test the min_up_time wait behavior
    tcb.time_in_state = 0.0

    # Now assign power setpoint to 0, the expected behavior is that the
    # power will ramp_down at the ramp rate until it reaches P_min
    # It will hold there until min_up_time is satisfied,
    # Then it will ramp to 0 at the ramp rate
    # When it reaches 0 it will transition to off
    h_dict["thermal_component"]["power_setpoint"] = 0

    # First step
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 1.0
    assert out["thermal_component"]["state"] == tcb.STATES.ON
    assert out["thermal_component"]["power"] == 400

    # Second step
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 2.0
    assert out["thermal_component"]["state"] == tcb.STATES.ON
    assert out["thermal_component"]["power"] == 300

    # Third step
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 3.0
    assert out["thermal_component"]["state"] == tcb.STATES.ON
    assert out["thermal_component"]["power"] == 200

    # Fourth step (Saturate at P_min)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 4.0
    assert out["thermal_component"]["state"] == tcb.STATES.ON
    assert out["thermal_component"]["power"] == 200

    # Fifth step (Satisfy min_up_time, transition to stopping)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 0.0  # Just entered stopping state
    assert out["thermal_component"]["state"] == tcb.STATES.STOPPING
    assert out["thermal_component"]["power"] == 100

    # Sixth step (Transition to off)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 0.0
    assert out["thermal_component"]["state"] == tcb.STATES.OFF
    assert out["thermal_component"]["power"] == 0


def test_transition_off_to_on():
    # Test off to on transition using a hot start

    h_dict = copy.deepcopy(h_dict_thermal_component)

    # Set the ramp rate to be 100 kW/s
    # Since the rated capacity is 1000 kW, and the ramp rate fraction is
    # fraction of rated capacity per minute we can compute the ramp rate fraction as
    # 100 kW/s / 1000 kW * 60 = 6
    h_dict["thermal_component"]["ramp_rate_fraction"] = 6

    # Set the initial conditions to be 0 kW (implies OFF state)
    h_dict["thermal_component"]["initial_conditions"]["power"] = 0

    # Set the min_down_time to 3
    h_dict["thermal_component"]["min_down_time"] = 3

    # Set the min_stable_load_fraction to be 0.2 (200 kW)
    h_dict["thermal_component"]["min_stable_load_fraction"] = 0.2

    # Set the hot_startup_time to be 7s
    h_dict["thermal_component"]["hot_startup_time"] = 7

    # Set the run_up_rate_fraction to be 3 (implying 50 kW/s)
    h_dict["thermal_component"]["run_up_rate_fraction"] = 3

    # This run up time and min_stable_load_fraction imply a ramp_time of 4 seconds
    # so the hot readying time should be 3 seconds

    tcb = ThermalComponentBase(h_dict)

    # Initial state: OFF with time_in_state = min_down_time (3s, ready to start)
    assert tcb.state == tcb.STATES.OFF
    assert tcb.power_output == 0
    assert tcb.time_in_state == 3.0

    # Force time_in_state to 0 to test the min_down_time wait behavior
    tcb.time_in_state = 0.0

    # Confirm that the hot readying time is 3 seconds
    assert tcb.hot_readying_time == 3

    # Now assign power setpoint to be 500, the expected behavior is that the
    # the unit will stay in off state until min_down_time is satisfied
    # Then it will transition to hot starting
    # Power will remain at 0 until the hot readying time is satisfied
    # Then it will ramp up at the run up rate (50 kW/s)
    # When the power reaches P_min (200 kW) it will transition to on
    # Then the ramp will increase to the ramp rate (100 kW/s)
    h_dict["thermal_component"]["power_setpoint"] = 500

    # First step (still waiting for min_down_time)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 1.0
    assert out["thermal_component"]["state"] == tcb.STATES.OFF
    assert out["thermal_component"]["power"] == 0

    # Second step (still waiting for min_down_time)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 2.0
    assert out["thermal_component"]["state"] == tcb.STATES.OFF
    assert out["thermal_component"]["power"] == 0

    # Third step (min_down_time satisfied, transition to hot starting)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 0.0
    assert out["thermal_component"]["state"] == tcb.STATES.HOT_STARTING
    assert out["thermal_component"]["power"] == 0

    # Fourth step (HOT START READYING)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 1.0
    assert out["thermal_component"]["state"] == tcb.STATES.HOT_STARTING
    assert out["thermal_component"]["power"] == 0

    # Fifth step (HOT START READYING)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 2.0
    assert out["thermal_component"]["state"] == tcb.STATES.HOT_STARTING
    assert out["thermal_component"]["power"] == 0

    # Sixth step (HOT START RAMPING)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 3.0
    assert out["thermal_component"]["state"] == tcb.STATES.HOT_STARTING
    assert out["thermal_component"]["power"] == 0

    # Seventh step (HOT START RAMPING)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 4.0
    assert out["thermal_component"]["state"] == tcb.STATES.HOT_STARTING
    assert out["thermal_component"]["power"] == 50

    # Eighth step (HOT START RAMPING)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 5.0
    assert out["thermal_component"]["state"] == tcb.STATES.HOT_STARTING
    assert out["thermal_component"]["power"] == 100

    # Ninth step (HOT START RAMPING)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 6.0
    assert out["thermal_component"]["state"] == tcb.STATES.HOT_STARTING
    assert out["thermal_component"]["power"] == 150

    # Tenth step (Transition to on)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 0.0
    assert out["thermal_component"]["state"] == tcb.STATES.ON
    assert out["thermal_component"]["power"] == 200

    # Eleventh step (Ramping in on state)
    out = tcb.step(copy.deepcopy(h_dict))
    assert tcb.time_in_state == 1.0
    assert out["thermal_component"]["state"] == tcb.STATES.ON
    assert out["thermal_component"]["power"] == 300


def test_efficiency_clamping():
    """Test clamping behavior at efficiency table boundaries."""
    h_dict = copy.deepcopy(h_dict_thermal_component)
    # Set up efficiency table that doesn't cover full range
    h_dict["thermal_component"]["efficiency_table"] = {
        "power_fraction": [0.25, 0.50, 0.75, 0.9],
        "efficiency": [0.30, 0.35, 0.38, 0.40],
    }
    tcb = ThermalComponentBase(h_dict)

    # Test above highest power fraction (should clamp to 0.40)
    # rated_capacity = 1000 kW, so 1000 kW = 100% load (above table max of 0.9)
    eff_100 = tcb.calculate_efficiency(1000)
    assert eff_100 == 0.40

    # Test as a value above 0 but below the lower defined power fraction (0.25)
    eff_200 = tcb.calculate_efficiency(200)  # 200 kW = 20% load (below table min of 0.25)
    assert eff_200 == 0.30

    # Test at zero power (should return first efficiency value)
    eff_0 = tcb.calculate_efficiency(0)
    assert eff_0 == 0.30


def test_efficiency_interpolation():
    """Test efficiency interpolation at various power levels."""
    import numpy as np

    h_dict = copy.deepcopy(h_dict_thermal_component)
    # Set up a simple efficiency table for testing
    # power_fraction: [0.25, 0.50, 0.75, 1.0]
    # efficiency:     [0.30, 0.35, 0.38, 0.40]
    h_dict["thermal_component"]["efficiency_table"] = {
        "power_fraction": [0.25, 0.50, 0.75, 1.0],
        "efficiency": [0.30, 0.35, 0.38, 0.40],
    }
    tcb = ThermalComponentBase(h_dict)

    # Test at table points (rated_capacity = 1000 kW)
    assert tcb.calculate_efficiency(1000) == 0.40  # 100% load
    assert tcb.calculate_efficiency(750) == 0.38  # 75% load
    assert tcb.calculate_efficiency(500) == 0.35  # 50% load
    assert tcb.calculate_efficiency(250) == 0.30  # 25% load

    # Test interpolation between points
    # At 625 kW (62.5%), should be between 0.35 and 0.38
    eff_625 = tcb.calculate_efficiency(625)
    assert 0.35 < eff_625 < 0.38
    np.testing.assert_allclose(eff_625, 0.365, rtol=1e-6)
