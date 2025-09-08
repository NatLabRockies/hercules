"""This module provides unit tests for 'SolarPySAMPVWatts'."""

import copy

import pytest
from hercules.plant_components.solar_pysam_pvwatts import SolarPySAMPVWatts
from numpy.testing import assert_almost_equal

from tests.test_inputs.h_dict import h_dict_solar_pvwatts


def create_solar_pysam():
    """Create a SolarPySAMPVWatts instance for testing."""
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    return SolarPySAMPVWatts(test_h_dict)


@pytest.fixture
def SPS():
    """Fixture to provide a SolarPySAMPVWatts instance for tests."""
    return create_solar_pysam()


def test_init():
    # testing the `init` function: reading the inputs from input dictionary
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    SPS = SolarPySAMPVWatts(test_h_dict)

    assert SPS.dt == test_h_dict["dt"]
    assert (
        SPS.model_params["SystemDesign"]["system_capacity"]
        == test_h_dict["solar_farm"]["target_system_capacity"]
    )
    assert SPS.power == test_h_dict["solar_farm"]["initial_conditions"]["power"]
    assert SPS.dc_power == test_h_dict["solar_farm"]["initial_conditions"]["power"]
    assert SPS.dni == test_h_dict["solar_farm"]["initial_conditions"]["dni"]
    assert SPS.aoi == 0


def test_return_outputs(SPS: SolarPySAMPVWatts):
    # testing the function `return_outputs`
    # outputs after initialization - all outputs should reflect input dict
    # Note: Current SolarPySAMPVWatts doesn't have return_outputs method,
    # so we test the attributes directly
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


def test_step(SPS: SolarPySAMPVWatts):
    # testing the `step` function: calculating power based on inputs at first timestep
    step_inputs = {"step": 0, "solar_farm": {"power_setpoint": 1e9}}

    SPS.step(step_inputs)

    # test the calculated power output
    assert_almost_equal(SPS.power, 16528.82749492729, decimal=8)

    # test the irradiance input
    assert_almost_equal(SPS.ghi, 68.23037719726561, decimal=8)


def test_control(SPS: SolarPySAMPVWatts):
    power_setpoint = 10000
    step_inputs = {"step": 0, "solar_farm": {"power_setpoint": power_setpoint}}
    SPS.step(step_inputs)
    assert_almost_equal(SPS.power, power_setpoint, decimal=8)

    power_setpoint = 100
    step_inputs = {"step": 0, "solar_farm": {"power_setpoint": power_setpoint}}
    SPS.step(step_inputs)
    assert_almost_equal(SPS.power, power_setpoint, decimal=8)
