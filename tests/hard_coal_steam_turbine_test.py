import copy

import numpy as np
from hercules.plant_components.hard_coal_steam_turbine import HardCoalSteamTurbine
from hercules.utilities import hercules_float_type

from .test_inputs.h_dict import (
    h_dict_hard_coal_steam_turbine,
)


def test_init_from_dict():
    """Test that HardCoalSteamTurbine can be initialized from a dictionary."""
    hcst = HardCoalSteamTurbine(
        copy.deepcopy(h_dict_hard_coal_steam_turbine), "hard_coal_steam_turbine"
    )
    assert hcst is not None


def test_default_inputs():
    """Test that HardCoalSteamTurbine uses default inputs when not provided."""
    h_dict = copy.deepcopy(h_dict_hard_coal_steam_turbine)

    # Test that the ramp_rate_fraction input is correct from input dict
    hcst = HardCoalSteamTurbine(h_dict, "hard_coal_steam_turbine")
    assert hcst.ramp_rate_fraction == 0.04

    # Test that the run_up_rate_fraction input is correct from input dict
    assert hcst.run_up_rate_fraction == 0.02

    # Test that if the run_up_rate_fraction is not provided,
    # it defaults to the ramp_rate_fraction
    h_dict = copy.deepcopy(h_dict_hard_coal_steam_turbine)
    del h_dict["hard_coal_steam_turbine"]["run_up_rate_fraction"]
    hcst = HardCoalSteamTurbine(h_dict, "hard_coal_steam_turbine")
    assert hcst.run_up_rate_fraction == hcst.ramp_rate_fraction

    # Now test that the default value of the ramp_rate_fraction is
    # applied to both the ramp_rate_fraction and the run_up_rate_fraction
    # if they are both not provided
    h_dict = copy.deepcopy(h_dict_hard_coal_steam_turbine)
    del h_dict["hard_coal_steam_turbine"]["ramp_rate_fraction"]
    del h_dict["hard_coal_steam_turbine"]["run_up_rate_fraction"]
    hcst = HardCoalSteamTurbine(h_dict, "hard_coal_steam_turbine")
    assert hcst.ramp_rate_fraction == 0.03
    assert hcst.run_up_rate_fraction == 0.03

    # Test the remaining default values
    # Delete startup times first, since changing min_stable_load_fraction and
    # ramp rates affects ramp_time validation against startup times
    h_dict = copy.deepcopy(h_dict_hard_coal_steam_turbine)
    del h_dict["hard_coal_steam_turbine"]["ramp_rate_fraction"]
    del h_dict["hard_coal_steam_turbine"]["run_up_rate_fraction"]
    del h_dict["hard_coal_steam_turbine"]["cold_startup_time"]
    del h_dict["hard_coal_steam_turbine"]["warm_startup_time"]
    del h_dict["hard_coal_steam_turbine"]["hot_startup_time"]
    del h_dict["hard_coal_steam_turbine"]["min_stable_load_fraction"]
    hcst = HardCoalSteamTurbine(h_dict, "hard_coal_steam_turbine")
    assert hcst.min_stable_load_fraction == 0.30
    assert hcst.hot_startup_time == 7.5 * 60.0 * 60.0  # 7.5 hours in seconds
    assert hcst.warm_startup_time == 7.5 * 60.0 * 60.0  # 7.5 hours in seconds
    assert hcst.cold_startup_time == 7.5 * 60.0 * 60.0  # 7.5 hours in seconds

    h_dict = copy.deepcopy(h_dict_hard_coal_steam_turbine)
    del h_dict["hard_coal_steam_turbine"]["min_up_time"]
    hcst = HardCoalSteamTurbine(h_dict, "hard_coal_steam_turbine")
    assert hcst.min_up_time == 48 * 60.0 * 60.0  # 48 hours in seconds

    h_dict = copy.deepcopy(h_dict_hard_coal_steam_turbine)
    del h_dict["hard_coal_steam_turbine"]["min_down_time"]
    hcst = HardCoalSteamTurbine(h_dict, "hard_coal_steam_turbine")
    assert hcst.min_down_time == 48 * 60.0 * 60.0  # 48 hours in seconds


def test_default_hhv():
    """Test that HardCoalSteamTurbine provides default HHV for bituminous coal from [4]."""
    h_dict = copy.deepcopy(h_dict_hard_coal_steam_turbine)
    del h_dict["hard_coal_steam_turbine"]["hhv"]
    hcst = HardCoalSteamTurbine(h_dict, "hard_coal_steam_turbine")
    assert hcst.hhv == 29310000000


def test_default_fuel_density():
    """Test that HardCoalSteamTurbine provides default fuel density."""
    h_dict = copy.deepcopy(h_dict_hard_coal_steam_turbine)
    if "fuel_density" in h_dict["hard_coal_steam_turbine"]:
        del h_dict["hard_coal_steam_turbine"]["fuel_density"]
    hcst = HardCoalSteamTurbine(h_dict, "hard_coal_steam_turbine")
    assert hcst.fuel_density == 1000.0


def test_default_efficiency_table():
    """Test that HardCoalSteamTurbine provides default HHV net efficiency table.

    Default values are taken from [2,3]
    """
    h_dict = copy.deepcopy(h_dict_hard_coal_steam_turbine)
    del h_dict["hard_coal_steam_turbine"]["efficiency_table"]
    hcst = HardCoalSteamTurbine(h_dict, "hard_coal_steam_turbine")
    np.testing.assert_array_equal(
        hcst.efficiency_power_fraction,
        np.array([0.3, 0.5, 1.0], dtype=hercules_float_type),
    )
    np.testing.assert_array_equal(
        hcst.efficiency_values,
        np.array([0.30, 0.32, 0.35], dtype=hercules_float_type),
    )
