import copy

import numpy as np
from hercules.plant_components.combined_cycle_gas_turbine import CombinedCycleGasTurbine
from hercules.utilities import hercules_float_type

from .test_inputs.h_dict import (
    h_dict_combined_cycle_gas_turbine,
)


def test_init_from_dict():
    """Test that CombinedCycleGasTurbine can be initialized from a dictionary."""
    ccgt = CombinedCycleGasTurbine(copy.deepcopy(h_dict_combined_cycle_gas_turbine))
    assert ccgt is not None


def test_default_inputs():
    """Test that CombinedCycleGasTurbine uses default inputs when not provided."""
    h_dict = copy.deepcopy(h_dict_combined_cycle_gas_turbine)

    # Test that the ramp_rate_fraction is 0.1 (from test fixture)
    ccgt = CombinedCycleGasTurbine(h_dict)
    assert ccgt.ramp_rate_fraction == 0.1

    # Test that the run_up_rate_fraction is 0.05 (from test fixture)
    assert ccgt.run_up_rate_fraction == 0.05

    # Test that if the run_up_rate_fraction is not provided,
    # it defaults to the ramp_rate_fraction
    h_dict = copy.deepcopy(h_dict_combined_cycle_gas_turbine)
    del h_dict["combined_cycle_gas_turbine"]["run_up_rate_fraction"]
    ccgt = CombinedCycleGasTurbine(h_dict)
    assert ccgt.run_up_rate_fraction == ccgt.ramp_rate_fraction

    # Now test that the default value of the ramp_rate_fraction is
    # applied to both the ramp_rate_fraction and the run_up_rate_fraction
    # if they are both not provided
    h_dict = copy.deepcopy(h_dict_combined_cycle_gas_turbine)
    del h_dict["combined_cycle_gas_turbine"]["ramp_rate_fraction"]
    del h_dict["combined_cycle_gas_turbine"]["run_up_rate_fraction"]
    ccgt = CombinedCycleGasTurbine(h_dict)
    assert ccgt.ramp_rate_fraction == 0.03
    assert ccgt.run_up_rate_fraction == 0.03

    # Test the remaining default values
    # Delete startup times first, since changing min_stable_load_fraction and
    # ramp rates affects ramp_time validation against startup times
    h_dict = copy.deepcopy(h_dict_combined_cycle_gas_turbine)
    del h_dict["combined_cycle_gas_turbine"]["ramp_rate_fraction"]
    del h_dict["combined_cycle_gas_turbine"]["run_up_rate_fraction"]
    del h_dict["combined_cycle_gas_turbine"]["cold_startup_time"]
    del h_dict["combined_cycle_gas_turbine"]["warm_startup_time"]
    del h_dict["combined_cycle_gas_turbine"]["hot_startup_time"]
    del h_dict["combined_cycle_gas_turbine"]["min_stable_load_fraction"]
    ccgt = CombinedCycleGasTurbine(h_dict)
    assert ccgt.min_stable_load_fraction == 0.40
    assert ccgt.hot_startup_time == 75 * 60.0
    assert ccgt.warm_startup_time == 120 * 60.0
    assert ccgt.cold_startup_time == 180 * 60.0

    h_dict = copy.deepcopy(h_dict_combined_cycle_gas_turbine)
    del h_dict["combined_cycle_gas_turbine"]["min_up_time"]
    ccgt = CombinedCycleGasTurbine(h_dict)
    assert ccgt.min_up_time == 4 * 60 * 60.0

    h_dict = copy.deepcopy(h_dict_combined_cycle_gas_turbine)
    del h_dict["combined_cycle_gas_turbine"]["min_down_time"]
    ccgt = CombinedCycleGasTurbine(h_dict)
    assert ccgt.min_down_time == 2 * 60 * 60.0


def test_default_hhv():
    """Test that CombinedCycleGasTurbine provides default HHV for natural gas from [6]."""
    h_dict = copy.deepcopy(h_dict_combined_cycle_gas_turbine)
    del h_dict["combined_cycle_gas_turbine"]["hhv"]
    ccgt = CombinedCycleGasTurbine(h_dict)
    # Default HHV for natural gas is 39.05 MJ/m³ = 39,050,000 J/m³ from [6]
    assert ccgt.hhv == 39050000


def test_default_fuel_density():
    """Test that CombinedCycleGasTurbine provides default fuel density from [6]."""
    h_dict = copy.deepcopy(h_dict_combined_cycle_gas_turbine)
    if "fuel_density" in h_dict["combined_cycle_gas_turbine"]:
        del h_dict["combined_cycle_gas_turbine"]["fuel_density"]
    ccgt = CombinedCycleGasTurbine(h_dict)
    # Default fuel density for natural gas is 0.768 kg/m³ from [6]
    assert ccgt.fuel_density == 0.768


def test_default_efficiency_table():
    """Test that CombinedCycleGasTurbine provides default HHV net efficiency table from [5].

    Default values are approximate readings from the CC1A-F curve in
    Exhibit ES-4 of [5].
    """

    h_dict = copy.deepcopy(h_dict_combined_cycle_gas_turbine)
    del h_dict["combined_cycle_gas_turbine"]["efficiency_table"]
    ccgt = CombinedCycleGasTurbine(h_dict)
    # Default HHV net plant efficiency from CC1A-F curve in Exhibit ES-4 of [5]
    np.testing.assert_array_equal(
        ccgt.efficiency_power_fraction,
        np.array(
            [0.4, 0.50, 0.55, 0.6, 0.65, 0.70, 0.75, 0.80, 0.85, 0.9, 0.95, 1.0],
            dtype=hercules_float_type,
        ),
    )
    np.testing.assert_array_equal(
        ccgt.efficiency_values,
        np.array(
            [0.47, 0.49, 0.5, 0.505, 0.515, 0.52, 0.52, 0.52, 0.52, 0.52, 0.515, 0.53],
            dtype=hercules_float_type,
        ),
    )
