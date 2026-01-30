import copy

from hercules.plant_components.combustion_turbine_simple import CombustionTurbineSimple

from .test_inputs.h_dict import (
    h_dict_combustion_turbine,
)


def test_init_from_dict():
    """Test that CombustionTurbineSimple can be initialized from a dictionary."""
    ct = CombustionTurbineSimple(copy.deepcopy(h_dict_combustion_turbine))
    assert ct is not None


def test_member_variables():
    """Test that the member variables are set correctly."""
    ct = CombustionTurbineSimple(copy.deepcopy(h_dict_combustion_turbine))
    assert ct.rated_capacity == h_dict_combustion_turbine["combustion_turbine"]["rated_capacity"]
    assert (
        ct.min_stable_load_fraction
        == h_dict_combustion_turbine["combustion_turbine"]["min_stable_load_fraction"]
    )
    assert ct.heat_rate == h_dict_combustion_turbine["combustion_turbine"]["heat_rate"]
    assert ct.ramp_rate_up == h_dict_combustion_turbine["combustion_turbine"]["ramp_rate_up"]
    assert ct.ramp_rate_down == h_dict_combustion_turbine["combustion_turbine"]["ramp_rate_down"]
    assert ct.startup_time == h_dict_combustion_turbine["combustion_turbine"]["startup_time"]
    assert ct.shutdown_time == h_dict_combustion_turbine["combustion_turbine"]["shutdown_time"]
    assert ct.min_up_time == h_dict_combustion_turbine["combustion_turbine"]["min_up_time"]
    assert ct.min_down_time == h_dict_combustion_turbine["combustion_turbine"]["min_down_time"]
    assert (
        ct.part_load_factor == h_dict_combustion_turbine["combustion_turbine"]["part_load_factor"]
    )


def test_power_setpoint_in_normal_operation():
    """Test power setpoint control in normal operation."""
    ct = CombustionTurbineSimple(copy.deepcopy(h_dict_combustion_turbine))

    # Set the power setpoint to 750 kW and test tracking
    h_dict_combustion_turbine["combustion_turbine"]["power_setpoint"] = 750.0
    out = ct.step(copy.deepcopy(h_dict_combustion_turbine))
    assert out["combustion_turbine"]["power"] == 750.0

    # Set the power set point to rated capacity and test tracking
    h_dict_combustion_turbine["combustion_turbine"]["power_setpoint"] = ct.rated_capacity
    out = ct.step(copy.deepcopy(h_dict_combustion_turbine))
    assert out["combustion_turbine"]["power"] == ct.rated_capacity

    # Set the power setpoint above rated capacity and test tracking
    h_dict_combustion_turbine["combustion_turbine"]["power_setpoint"] = ct.rated_capacity + 100.0
    out = ct.step(copy.deepcopy(h_dict_combustion_turbine))
    assert out["combustion_turbine"]["power"] == ct.rated_capacity

    # Now exceed ramp_rate_down to test ramp rate constraints
    h_dict_combustion_turbine["combustion_turbine"]["power_setpoint"] = (
        400.0  # Ramp rate down is 500 kW/s
    )
    out = ct.step(copy.deepcopy(h_dict_combustion_turbine))
    assert out["combustion_turbine"]["power"] == 500.0

    # Now test min_stable_load_fraction constraint
    h_dict_combustion_turbine["combustion_turbine"]["power_setpoint"] = 100.0
    out = ct.step(copy.deepcopy(h_dict_combustion_turbine))
    assert out["combustion_turbine"]["power"] == 200.0  # 20% of rated capacity


def test_transitions():
    ct = CombustionTurbineSimple(copy.deepcopy(h_dict_combustion_turbine))

    # Set the power setpoint to 0 kW and test shutdown
    h_dict_combustion_turbine["combustion_turbine"]["power_setpoint"] = 0.0
    _ = ct.step(copy.deepcopy(h_dict_combustion_turbine))

    # First time step should be below min_up_time (2s)
    assert ct.state_num == ct.STATE_ON

    # Power should be at 500 kW since initial conditions was 1000 kW and
    # ramp rate down is 500 kW/s
    assert ct.power_output == 500

    # Step again and state should not be stopping
    _ = ct.step(copy.deepcopy(h_dict_combustion_turbine))
    assert ct.state_num == ct.STATE_STOPPING

    # Additionally power should be ramping down according to shutdown_time
    assert ct.time_in_state == 0.0
    assert ct.power_output == 200  # (P_min waited by progress)

    # Step again
    _ = ct.step(copy.deepcopy(h_dict_combustion_turbine))
    assert ct.state_num == ct.STATE_STOPPING
    assert ct.time_in_state == 1.0
    assert ct.power_output == 100  # (P_min waited by progress)

    # Step again and now should have transitioned to off
    _ = ct.step(copy.deepcopy(h_dict_combustion_turbine))
    assert ct.state_num == ct.STATE_OFF
    assert ct.power_output == 0  # (P_min waited by progress)

    # Now increase the power setpoint to rated
    h_dict_combustion_turbine["combustion_turbine"]["power_setpoint"] = 1000.0
    _ = ct.step(copy.deepcopy(h_dict_combustion_turbine))

    # Because min_down_time is 2s, should still be off
    assert ct.state_num == ct.STATE_OFF
    assert ct.power_output == 0  # (P_min waited by progress)

    # Step again and now should have transitioned to starting
    _ = ct.step(copy.deepcopy(h_dict_combustion_turbine))
    assert ct.state_num == ct.STATE_STARTING
    assert ct.time_in_state == 0.0
    assert ct.power_output == 0  # (P_min waited by progress)

    # Step again and should be ramping up to P_min
    _ = ct.step(copy.deepcopy(h_dict_combustion_turbine))
    assert ct.state_num == ct.STATE_STARTING
    assert ct.time_in_state == 1.0
    assert ct.power_output == ct.P_min * (1.0 - 1.0 / ct.startup_time)

    # Step again and transitioned to on
    _ = ct.step(copy.deepcopy(h_dict_combustion_turbine))
    assert ct.state_num == ct.STATE_ON
    assert ct.time_in_state == 0.0
    assert ct.power_output == ct.P_min

    # Step again and should have increased by the ramp rate up
    _ = ct.step(copy.deepcopy(h_dict_combustion_turbine))
    assert ct.state_num == ct.STATE_ON
    assert ct.time_in_state == 1.0
    assert ct.power_output == ct.P_min + ct.ramp_rate_up
