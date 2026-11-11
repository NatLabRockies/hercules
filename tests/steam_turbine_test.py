import copy

import numpy as np
from hercules.plant_components.steam_turbine import SteamTurbine
from hercules.utilities import hercules_float_type

from .test_inputs.h_dict import (
    h_dict_steam_turbine,
)


def test_init_from_dict():
    """Test that SteamTurbine can be initialized from a dictionary."""
    hcst = SteamTurbine(copy.deepcopy(h_dict_steam_turbine), "steam_turbine")

    assert hcst is not None


def test_default_inputs():
    """Test that SteamTurbine uses default inputs when not provided."""
    h_dict = copy.deepcopy(h_dict_steam_turbine)

    # Test that the ramp_rate_fraction_per_min input is correct from input dict
    hcst = SteamTurbine(h_dict, "steam_turbine")
    assert hcst.ramp_rate_fraction_per_min == 0.04

    # Test that the run_up_rate_fraction_per_min input is correct from input dict
    assert hcst.run_up_rate_fraction_per_min == 0.02

    # Test that if the run_up_rate_fraction_per_min is not provided,
    # it defaults to the ramp_rate_fraction_per_min
    h_dict = copy.deepcopy(h_dict_steam_turbine)
    del h_dict["steam_turbine"]["run_up_rate_fraction_per_min"]
    hcst = SteamTurbine(h_dict, "steam_turbine")
    assert hcst.run_up_rate_fraction_per_min == hcst.ramp_rate_fraction_per_min

    # Now test that the default value of the ramp_rate_fraction_per_min is
    # applied to both the ramp_rate_fraction_per_min and the run_up_rate_fraction_per_min
    # if they are both not provided
    h_dict = copy.deepcopy(h_dict_steam_turbine)
    del h_dict["steam_turbine"]["ramp_rate_fraction_per_min"]
    del h_dict["steam_turbine"]["run_up_rate_fraction_per_min"]
    hcst = SteamTurbine(h_dict, "steam_turbine")
    assert hcst.ramp_rate_fraction_per_min == 0.03
    assert hcst.run_up_rate_fraction_per_min == 0.03

    # Test the remaining default values
    # Delete startup times first, since changing load_stable_min_fraction and
    # ramp rates affects ramp_time validation against startup times
    h_dict = copy.deepcopy(h_dict_steam_turbine)
    del h_dict["steam_turbine"]["ramp_rate_fraction_per_min"]
    del h_dict["steam_turbine"]["run_up_rate_fraction_per_min"]
    del h_dict["steam_turbine"]["startup_time_cold"]
    del h_dict["steam_turbine"]["startup_time_warm"]
    del h_dict["steam_turbine"]["startup_time_hot"]
    del h_dict["steam_turbine"]["load_stable_min_fraction"]
    hcst = SteamTurbine(h_dict, "steam_turbine")
    assert hcst.load_stable_min_fraction == 0.30
    assert hcst.startup_time_hot == 7.5 * 60.0 * 60.0  # 7.5 hours in seconds
    assert hcst.startup_time_warm == 7.5 * 60.0 * 60.0  # 7.5 hours in seconds
    assert hcst.startup_time_cold == 7.5 * 60.0 * 60.0  # 7.5 hours in seconds

    h_dict = copy.deepcopy(h_dict_steam_turbine)
    del h_dict["steam_turbine"]["up_time_min"]
    hcst = SteamTurbine(h_dict, "steam_turbine")
    assert hcst.up_time_min == 48 * 60.0 * 60.0  # 48 hours in seconds

    h_dict = copy.deepcopy(h_dict_steam_turbine)
    del h_dict["steam_turbine"]["down_time_min"]
    hcst = SteamTurbine(h_dict, "steam_turbine")
    assert hcst.down_time_min == 48 * 60.0 * 60.0  # 48 hours in seconds

    # Test cooldown threshold defaults
    h_dict = copy.deepcopy(h_dict_steam_turbine)
    del h_dict["steam_turbine"]["cooldown_time_warm"]
    hcst = SteamTurbine(h_dict, "steam_turbine")
    assert hcst.cooldown_time_warm == 28800.0  # 8 hours

    h_dict = copy.deepcopy(h_dict_steam_turbine)
    del h_dict["steam_turbine"]["cooldown_time_cold"]
    hcst = SteamTurbine(h_dict, "steam_turbine")
    assert hcst.cooldown_time_cold == 172800.0  # 48 hours


def test_default_hhv():
    """Test that SteamTurbine provides default HHV for bituminous coal from [4]."""
    h_dict = copy.deepcopy(h_dict_steam_turbine)
    del h_dict["steam_turbine"]["HHV"]
    hcst = SteamTurbine(h_dict, "steam_turbine")
    assert hcst.HHV == 29310000000


def test_default_fuel_density():
    """Test that SteamTurbine provides default fuel density."""
    h_dict = copy.deepcopy(h_dict_steam_turbine)
    if "fuel_density" in h_dict["steam_turbine"]:
        del h_dict["steam_turbine"]["fuel_density"]
    hcst = SteamTurbine(h_dict, "steam_turbine")
    assert hcst.fuel_density == 1000.0


def test_default_efficiency_table():
    """Test that SteamTurbine provides default HHV net efficiency table.

    Default values are taken from [2,3]
    """
    h_dict = copy.deepcopy(h_dict_steam_turbine)
    del h_dict["steam_turbine"]["efficiency_table"]
    hcst = SteamTurbine(h_dict, "steam_turbine")
    np.testing.assert_array_equal(
        hcst.efficiency_power_fraction,
        np.array([0.3, 0.5, 1.0], dtype=hercules_float_type),
    )
    np.testing.assert_array_equal(
        hcst.efficiency_values,
        np.array([0.30, 0.32, 0.35], dtype=hercules_float_type),
    )
