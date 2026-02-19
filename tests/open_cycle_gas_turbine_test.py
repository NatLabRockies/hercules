import copy

import numpy as np
from hercules.plant_components.open_cycle_gas_turbine import OpenCycleGasTurbine
from hercules.utilities import hercules_float_type

from .test_inputs.h_dict import (
    h_dict_open_cycle_gas_turbine,
)


def test_init_from_dict():
    """Test that OpenCycleGasTurbine can be initialized from a dictionary."""
    ocgt = OpenCycleGasTurbine(copy.deepcopy(h_dict_open_cycle_gas_turbine))
    assert ocgt is not None


def test_default_inputs():
    """Test that OpenCycleGasTurbine uses default inputs when not provided."""
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)

    # Test that the ramp_rate_fraction is 0.5 (from test fixture)
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.ramp_rate_fraction == 0.5

    # Test that the run_up_rate_fraction is 0.2 (from test fixture)
    assert ocgt.run_up_rate_fraction == 0.2

    # Test that if the run_up_rate_fraction is not provided,
    # it defaults to the ramp_rate_fraction
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["run_up_rate_fraction"]
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.run_up_rate_fraction == ocgt.ramp_rate_fraction

    # Now test that the default value of the ramp_rate_fraction is
    # applied to both the ramp_rate_fraction and the run_up_rate_fraction
    # if they are both not provided
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["ramp_rate_fraction"]
    del h_dict["open_cycle_gas_turbine"]["run_up_rate_fraction"]
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.ramp_rate_fraction == 0.1
    assert ocgt.run_up_rate_fraction == 0.1

    # Test the remaining default values
    # Delete startup times first, since changing min_stable_load_fraction and
    # ramp rates affects ramp_time validation against startup times
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["ramp_rate_fraction"]
    del h_dict["open_cycle_gas_turbine"]["run_up_rate_fraction"]
    del h_dict["open_cycle_gas_turbine"]["cold_startup_time"]
    del h_dict["open_cycle_gas_turbine"]["warm_startup_time"]
    del h_dict["open_cycle_gas_turbine"]["hot_startup_time"]
    del h_dict["open_cycle_gas_turbine"]["min_stable_load_fraction"]
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.min_stable_load_fraction == 0.40
    assert ocgt.hot_startup_time == 7 * 60.0
    assert ocgt.warm_startup_time == 8 * 60.0
    assert ocgt.cold_startup_time == 8 * 60.0

    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["min_up_time"]
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.min_up_time == 30 * 60.0

    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["min_down_time"]
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.min_down_time == 60 * 60.0


def test_default_hhv():
    """Test that OpenCycleGasTurbine provides default HHV for natural gas from [6]."""
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["hhv"]
    ocgt = OpenCycleGasTurbine(h_dict)
    # Default HHV for natural gas is 39.05 MJ/m³ = 39,050,000 J/m³ from [6]
    assert ocgt.hhv == 39050000


def test_default_fuel_density():
    """Test that OpenCycleGasTurbine provides default fuel density from [6]."""
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    if "fuel_density" in h_dict["open_cycle_gas_turbine"]:
        del h_dict["open_cycle_gas_turbine"]["fuel_density"]
    ocgt = OpenCycleGasTurbine(h_dict)
    # Default fuel density for natural gas is 0.768 kg/m³ from [6]
    assert ocgt.fuel_density == 0.768


def test_default_efficiency_table():
    """Test that OpenCycleGasTurbine provides default HHV net efficiency table from [5].

    Default values are approximate readings from the SC1A curve in
    Exhibit ES-4 of [5].
    """
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["efficiency_table"]
    ocgt = OpenCycleGasTurbine(h_dict)
    # Default HHV net plant efficiency from SC1A curve in Exhibit ES-4 of [5]
    np.testing.assert_array_equal(
        ocgt.efficiency_power_fraction,
        np.array([0.25, 0.50, 0.75, 1.0], dtype=hercules_float_type),
    )
    np.testing.assert_array_equal(
        ocgt.efficiency_values,
        np.array([0.245, 0.325, 0.37, 0.39], dtype=hercules_float_type),
    )
