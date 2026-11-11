import copy

import numpy as np
from hercules.plant_components.open_cycle_gas_turbine import OpenCycleGasTurbine
from hercules.utilities import hercules_float_type

from .test_inputs.h_dict import (
    h_dict_open_cycle_gas_turbine,
)


def test_init_from_dict():
    """Test that OpenCycleGasTurbine can be initialized from a dictionary."""
    ocgt = OpenCycleGasTurbine(
        copy.deepcopy(h_dict_open_cycle_gas_turbine), "open_cycle_gas_turbine"
    )
    assert ocgt is not None


def test_default_inputs():
    """Test that OpenCycleGasTurbine uses default inputs when not provided."""
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)

    # Test that the ramp_rate_fraction_per_min is 0.5 (from test fixture)
    ocgt = OpenCycleGasTurbine(h_dict, "open_cycle_gas_turbine")
    assert ocgt.ramp_rate_fraction_per_min == 0.5

    # Test that the run_up_rate_fraction_per_min is 0.2 (from test fixture)
    assert ocgt.run_up_rate_fraction_per_min == 0.2

    # Test that if the run_up_rate_fraction_per_min is not provided,
    # it defaults to the ramp_rate_fraction_per_min
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["run_up_rate_fraction_per_min"]
    ocgt = OpenCycleGasTurbine(h_dict, "open_cycle_gas_turbine")
    assert ocgt.run_up_rate_fraction_per_min == ocgt.ramp_rate_fraction_per_min

    # Now test that the default value of the ramp_rate_fraction_per_min is
    # applied to both the ramp_rate_fraction_per_min and the run_up_rate_fraction_per_min
    # if they are both not provided
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["ramp_rate_fraction_per_min"]
    del h_dict["open_cycle_gas_turbine"]["run_up_rate_fraction_per_min"]
    ocgt = OpenCycleGasTurbine(h_dict, "open_cycle_gas_turbine")
    assert ocgt.ramp_rate_fraction_per_min == 0.1
    assert ocgt.run_up_rate_fraction_per_min == 0.1

    # Test the remaining default values
    # Delete startup times first, since changing load_stable_min_fraction and
    # ramp rates affects ramp_time validation against startup times
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["ramp_rate_fraction_per_min"]
    del h_dict["open_cycle_gas_turbine"]["run_up_rate_fraction_per_min"]
    del h_dict["open_cycle_gas_turbine"]["startup_time_cold"]
    del h_dict["open_cycle_gas_turbine"]["startup_time_warm"]
    del h_dict["open_cycle_gas_turbine"]["startup_time_hot"]
    del h_dict["open_cycle_gas_turbine"]["load_stable_min_fraction"]
    ocgt = OpenCycleGasTurbine(h_dict, "open_cycle_gas_turbine")
    assert ocgt.load_stable_min_fraction == 0.40
    assert ocgt.startup_time_hot == 7 * 60.0
    assert ocgt.startup_time_warm == 8 * 60.0
    assert ocgt.startup_time_cold == 8 * 60.0

    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["up_time_min"]
    ocgt = OpenCycleGasTurbine(h_dict, "open_cycle_gas_turbine")
    assert ocgt.up_time_min == 30 * 60.0

    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["down_time_min"]
    ocgt = OpenCycleGasTurbine(h_dict, "open_cycle_gas_turbine")
    assert ocgt.down_time_min == 60 * 60.0

    # Test cooldown threshold defaults
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["cooldown_time_warm"]
    ocgt = OpenCycleGasTurbine(h_dict, "open_cycle_gas_turbine")
    assert ocgt.cooldown_time_warm == 28800.0  # 8 hours

    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["cooldown_time_cold"]
    ocgt = OpenCycleGasTurbine(h_dict, "open_cycle_gas_turbine")
    assert ocgt.cooldown_time_cold == 172800.0  # 48 hours


def test_default_hhv():
    """Test that OpenCycleGasTurbine provides default HHV for natural gas from [6]."""
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["HHV"]
    ocgt = OpenCycleGasTurbine(h_dict, "open_cycle_gas_turbine")
    # Default HHV for natural gas is 39.05 MJ/m³ = 39,050,000 J/m³ from [6]
    assert ocgt.HHV == 39050000


def test_default_fuel_density():
    """Test that OpenCycleGasTurbine provides default fuel density from [6]."""
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    if "fuel_density" in h_dict["open_cycle_gas_turbine"]:
        del h_dict["open_cycle_gas_turbine"]["fuel_density"]
    ocgt = OpenCycleGasTurbine(h_dict, "open_cycle_gas_turbine")
    # Default fuel density for natural gas is 0.768 kg/m³ from [6]
    assert ocgt.fuel_density == 0.768


def test_default_efficiency_table():
    """Test that OpenCycleGasTurbine provides default HHV net efficiency table from [5].

    Default values are approximate readings from the SC1A curve in
    Exhibit ES-4 of [5].
    """
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["efficiency_table"]
    ocgt = OpenCycleGasTurbine(h_dict, "open_cycle_gas_turbine")
    # Default HHV net plant efficiency from SC1A curve in Exhibit ES-4 of [5]
    np.testing.assert_array_equal(
        ocgt.efficiency_power_fraction,
        np.array([0.25, 0.50, 0.75, 1.0], dtype=hercules_float_type),
    )
    np.testing.assert_array_equal(
        ocgt.efficiency_values,
        np.array([0.245, 0.325, 0.37, 0.39], dtype=hercules_float_type),
    )
