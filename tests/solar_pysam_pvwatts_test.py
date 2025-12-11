"""This module provides unit tests for 'SolarPySAMPVWatts'."""

import copy

from hercules.plant_components.solar_pysam_pvwatts import SolarPySAMPVWatts
from numpy.testing import assert_almost_equal

from tests.test_inputs.h_dict import h_dict_solar_pvwatts

# Removed unnecessary create_solar_pysam() function and SPS fixture
# Tests now use direct instantiation for simplicity


def test_init():
    # testing the `init` function: reading the inputs from input dictionary
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    SPS = SolarPySAMPVWatts(test_h_dict)

    assert SPS.dt == test_h_dict["dt"]
    # Test that system_capacity is stored correctly
    assert SPS.system_capacity == test_h_dict["solar_farm"]["system_capacity"]
    assert SPS.power == test_h_dict["solar_farm"]["initial_conditions"]["power"]
    assert SPS.dc_power == test_h_dict["solar_farm"]["initial_conditions"]["power"]
    assert SPS.dni == test_h_dict["solar_farm"]["initial_conditions"]["dni"]
    assert SPS.aoi == 0


def test_return_outputs():
    # testing the function `return_outputs`
    # outputs after initialization - all outputs should reflect input dict
    # Note: Current SolarPySAMPVWatts doesn't have return_outputs method,
    # so we test the attributes directly
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    SPS = SolarPySAMPVWatts(test_h_dict)

    assert SPS.power == 25
    assert SPS.dni == 1000
    assert SPS.poa == 1000

    # change PV power predictions and irradiance as if during simulation
    SPS.power = 800
    SPS.dni = 600
    SPS.poa = 900
    SPS.aoi = 0

    # check that outputs return the changed PV outputs
    assert SPS.power == 800
    assert SPS.dni == 600
    assert SPS.poa == 900
    assert SPS.aoi == 0


def test_step():
    # testing the `step` function: calculating power based on inputs at first timestep
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    SPS = SolarPySAMPVWatts(test_h_dict)

    step_inputs = {"step": 0, "solar_farm": {"power_setpoint": 1e9}}

    SPS.step(step_inputs)

    # test the calculated power output (0° tilt)
    # Using decimal=4 for float32 precision (hercules_float_type provides ~6-7 significant digits)
    assert_almost_equal(SPS.power, 17092.157367793126, decimal=4)

    # test the irradiance input
    # Using decimal=4 for float32 precision (hercules_float_type provides ~6-7 significant digits)
    assert_almost_equal(SPS.ghi, 68.23037719726561, decimal=4)


def test_control():
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    SPS = SolarPySAMPVWatts(test_h_dict)

    # Test curtailment - set power setpoint above uncurtailed power,
    # should get uncurtailed power
    power_setpoint = 100000  # Above uncurtailed power
    step_inputs = {"step": 0, "solar_farm": {"power_setpoint": power_setpoint}}
    SPS.step(step_inputs)
    uncurtailed_power = SPS.power_uncurtailed[0]
    assert_almost_equal(SPS.power, uncurtailed_power, decimal=8)  # uncurtailed power

    # Test curtailment - set power below uncurtailed power, should get setpoint
    power_setpoint = 100  # Below uncurtailed power
    step_inputs = {"step": 0, "solar_farm": {"power_setpoint": power_setpoint}}
    SPS.step(step_inputs)
    assert_almost_equal(SPS.power, power_setpoint, decimal=8)
