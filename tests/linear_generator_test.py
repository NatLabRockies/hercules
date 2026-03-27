import copy

import numpy as np
from hercules.plant_components.linear_generator import LinearGenerator
from hercules.utilities import hercules_float_type

from .test_inputs.h_dict import (
    h_dict_linear_generator,
)


def test_init_from_dict():
    """Test that LinearGenerator can be initialized from a dictionary."""
    lg = LinearGenerator(copy.deepcopy(h_dict_linear_generator), "linear_generator")
    assert lg is not None


def test_default_inputs():
    """Test that LinearGenerator uses default inputs when not provided."""
    h_dict = copy.deepcopy(h_dict_linear_generator)

    # Test that explicit fixture values are used when provided
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.ramp_rate_fraction == 0.5
    assert lg.run_up_rate_fraction == 0.3

    # Test that if run_up_rate_fraction is not provided,
    # it defaults to ramp_rate_fraction
    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["run_up_rate_fraction"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.run_up_rate_fraction == lg.ramp_rate_fraction

    # Test that default ramp_rate_fraction and run_up_rate_fraction are applied
    # when both are absent
    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["ramp_rate_fraction"]
    del h_dict["linear_generator"]["run_up_rate_fraction"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.ramp_rate_fraction == LinearGenerator.DEFAULTS["ramp_rate_fraction"]
    assert lg.run_up_rate_fraction == LinearGenerator.DEFAULTS["ramp_rate_fraction"]

    # Test remaining scalar defaults (remove startup times alongside ramp params
    # to avoid ramp_time validation failures)
    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["ramp_rate_fraction"]
    del h_dict["linear_generator"]["run_up_rate_fraction"]
    del h_dict["linear_generator"]["hot_startup_time"]
    del h_dict["linear_generator"]["warm_startup_time"]
    del h_dict["linear_generator"]["cold_startup_time"]
    del h_dict["linear_generator"]["min_stable_load_fraction"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.min_stable_load_fraction == LinearGenerator.DEFAULTS["min_stable_load_fraction"]
    assert lg.hot_startup_time == LinearGenerator.DEFAULTS["hot_startup_time"]
    assert lg.warm_startup_time == LinearGenerator.DEFAULTS["warm_startup_time"]
    assert lg.cold_startup_time == LinearGenerator.DEFAULTS["cold_startup_time"]

    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["min_up_time"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.min_up_time == LinearGenerator.DEFAULTS["min_up_time"]

    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["min_down_time"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.min_down_time == LinearGenerator.DEFAULTS["min_down_time"]


def test_default_hhv():
    """Test that LinearGenerator provides default HHV for natural gas from [3]."""
    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["hhv"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.hhv == LinearGenerator.DEFAULTS["hhv"]


def test_default_fuel_density():
    """Test that LinearGenerator provides default fuel density for natural gas from [3]."""
    h_dict = copy.deepcopy(h_dict_linear_generator)
    if "fuel_density" in h_dict["linear_generator"]:
        del h_dict["linear_generator"]["fuel_density"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.fuel_density == LinearGenerator.DEFAULTS["fuel_density"]


def test_default_efficiency_table():
    """Test that LinearGenerator provides default HHV net efficiency table from [1]."""
    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["efficiency_table"]
    lg = LinearGenerator(h_dict, "linear_generator")
    expected_pf = LinearGenerator.DEFAULTS["efficiency_table"]["power_fraction"]
    expected_eff = LinearGenerator.DEFAULTS["efficiency_table"]["efficiency"]
    np.testing.assert_array_equal(
        lg.efficiency_power_fraction,
        np.array(sorted(expected_pf), dtype=hercules_float_type),
    )
    np.testing.assert_array_equal(
        lg.efficiency_values,
        np.array(
            [e for _, e in sorted(zip(expected_pf, expected_eff))],
            dtype=hercules_float_type,
        ),
    )
