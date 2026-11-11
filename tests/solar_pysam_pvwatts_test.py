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
    SPS = SolarPySAMPVWatts(test_h_dict, "solar_farm")

    assert SPS.dt == test_h_dict["dt"]
    # Test that system_capacity is stored correctly
    assert SPS.DC_capacity_rated == test_h_dict["solar_farm"]["system_capacity"]
    assert SPS.power == test_h_dict["solar_farm"]["initial_conditions"]["power"]
    assert SPS.power_hypothetical == SPS.power_hypothetical_array[0]
    assert SPS.DC_power_hypothetical == SPS.DC_power_hypothetical_array[0]
    assert SPS.DNI == test_h_dict["solar_farm"]["initial_conditions"]["DNI"]
    assert SPS.AOI == 0


def test_init_defaults():
    # testing the `init` function: reading the inputs from input dictionary
    # and using defaults for missing PySAM options
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    # Remove PySAM options to test defaults
    if "pysam_options" in test_h_dict["solar_farm"]:
        del test_h_dict["solar_farm"]["pysam_options"]

    SPS = SolarPySAMPVWatts(test_h_dict, "solar_farm")

    # Test that Hercules defaults are used when pysam_options are missing
    assert SPS.model_params["SystemDesign"]["array_type"] == 3.0  # single axis backtracking
    assert SPS.model_params["SystemDesign"]["azimuth"] == 180.0
    assert (
        SPS.model_params["SystemDesign"]["dc_ac_ratio"] == 1.0
    )  # default is 1.0 so there are no inverter losses.
    assert SPS.model_params["SystemDesign"]["module_type"] == 0.0  # standard crystalline silicon


def test_init_pysam_options():
    # testing the `init` function: reading the inputs from input dictionary
    # and using provided PySAM options instead of defaults
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    # Add custom PySAM options to test that they are read correctly
    test_h_dict["solar_farm"]["pysam_options"] = {
        "SystemDesign": {
            "array_type": 1.0,  # fixed open rack
            "azimuth": 170.0,
            "dc_ac_ratio": 1.5,
            "module_type": 1.0,  # premium crystalline silicon
        }
    }

    SPS = SolarPySAMPVWatts(test_h_dict, "solar_farm")

    # Test that provided PySAM options are used instead of defaults
    assert SPS.model_params["SystemDesign"]["array_type"] == 1.0  # fixed open rack
    assert SPS.model_params["SystemDesign"]["azimuth"] == 170.0
    assert SPS.model_params["SystemDesign"]["dc_ac_ratio"] == 1.5
    assert SPS.model_params["SystemDesign"]["module_type"] == 1.0  # premium crystalline silicon


def test_init_invalid_pysam_options():
    # testing the `init` function: handling invalid PySAM options
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    # Add invalid PySAM options to test error handling
    test_h_dict["solar_farm"]["pysam_options"] = {
        "SystemDesign": {
            "array_type": 1.0,  # Invalid array type
            "azimuth": 170.0,
            "dc_ac_ratio": 1.5,
            "module_type": 1.0,  # premium crystalline silicon
            "losses": 0.1,
        }
    }

    try:
        SolarPySAMPVWatts(test_h_dict, "solar_farm")
        # If no error is raised, the test should fail
        assert False, "Expected ValueError for invalid pysam_options entry."
    except ValueError as e:
        assert (
            str(e)
            == "Error: The following parameters are provided in both the top-level input\
                        and the PySAM options: {'losses'}. Please remove these parameters\
                        from the PySAM options."
        )


def test_init_partial_pysam_options():
    # testing the `init` function: handling partial PySAM options (some provided, some defaults)
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    # Add partial PySAM options to test that provided options are used and missing ones default
    test_h_dict["solar_farm"]["pysam_options"] = {
        "SystemDesign": {
            "array_type": 1.0,  # fixed open rack
            "azimuth": 170.0,
            # dc_ac_ratio and module_type are not provided, should use defaults
        }
    }

    SPS = SolarPySAMPVWatts(test_h_dict, "solar_farm")

    # Test that provided PySAM options are used and missing ones default
    assert SPS.model_params["SystemDesign"]["array_type"] == 1.0  # fixed open rack
    assert SPS.model_params["SystemDesign"]["azimuth"] == 170.0
    assert (
        SPS.model_params["SystemDesign"]["dc_ac_ratio"] == 1.0
    )  # default is 1.0 so there are no inverter losses.
    assert SPS.model_params["SystemDesign"]["module_type"] == 0.0  # standard crystalline silicon


def test_return_outputs():
    # testing the function `return_outputs`
    # outputs after initialization - all outputs should reflect input dict
    # Note: Current SolarPySAMPVWatts doesn't have return_outputs method,
    # so we test the attributes directly
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    SPS = SolarPySAMPVWatts(test_h_dict, "solar_farm")

    assert SPS.power == 25
    assert SPS.DNI == 1000
    assert SPS.POA == 1000

    # change PV power predictions and irradiance as if during simulation
    SPS.power = 800
    SPS.DNI = 600
    SPS.POA = 900
    SPS.AOI = 0

    # check that outputs return the changed PV outputs
    assert SPS.power == 800
    assert SPS.DNI == 600
    assert SPS.POA == 900
    assert SPS.AOI == 0


def test_step():
    # testing the `step` function: calculating power based on inputs at first timestep
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    SPS = SolarPySAMPVWatts(test_h_dict, "solar_farm")

    step_inputs = {"step": 0, "solar_farm": {"power_setpoint": 1e9}}

    SPS.step(step_inputs)

    # test the calculated power output (0° tilt, AC post-inverter)
    # Using decimal=4 for float32 precision (hercules_float_type provides ~6-7 significant digits)
    assert_almost_equal(SPS.power, 16010.88671875, decimal=4)

    # test the irradiance input
    # Using decimal=4 for float32 precision (hercules_float_type provides ~6-7 significant digits)
    assert_almost_equal(SPS.GHI, 68.23037719726561, decimal=4)


def test_control():
    test_h_dict = copy.deepcopy(h_dict_solar_pvwatts)
    SPS = SolarPySAMPVWatts(test_h_dict, "solar_farm")

    # Test curtailment - set power setpoint above available power,
    # should get available power
    power_setpoint = 100000  # Above available power
    step_inputs = {"step": 0, "solar_farm": {"power_setpoint": power_setpoint}}
    SPS.step(step_inputs)
    power_hypothetical = SPS.power_hypothetical_array[0]
    assert_almost_equal(SPS.power, power_hypothetical, decimal=8)  # available power

    # Test curtailment - set power below available power, should get setpoint
    power_setpoint = 100  # Below available power
    step_inputs = {"step": 0, "solar_farm": {"power_setpoint": power_setpoint}}
    out = SPS.step(step_inputs)
    assert_almost_equal(SPS.power, power_setpoint, decimal=8)
    # power_hypothetical is unaffected by curtailment
    assert out["solar_farm"]["power_hypothetical"] == power_hypothetical
    assert out["solar_farm"]["power"] < out["solar_farm"]["power_hypothetical"]
