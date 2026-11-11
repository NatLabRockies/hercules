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
    assert lg.ramp_rate_fraction_per_min == 0.5
    assert lg.run_up_rate_fraction_per_min == 0.3

    # Test that if run_up_rate_fraction_per_min is not provided,
    # it defaults to ramp_rate_fraction_per_min
    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["run_up_rate_fraction_per_min"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.run_up_rate_fraction_per_min == lg.ramp_rate_fraction_per_min

    # Test that default ramp_rate_fraction_per_min and run_up_rate_fraction_per_min are applied
    # when both are absent
    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["ramp_rate_fraction_per_min"]
    del h_dict["linear_generator"]["run_up_rate_fraction_per_min"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.ramp_rate_fraction_per_min == LinearGenerator.DEFAULTS["ramp_rate_fraction_per_min"]
    assert lg.run_up_rate_fraction_per_min == LinearGenerator.DEFAULTS["ramp_rate_fraction_per_min"]

    # Test remaining scalar defaults (remove startup times alongside ramp params
    # to avoid ramp_time validation failures)
    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["ramp_rate_fraction_per_min"]
    del h_dict["linear_generator"]["run_up_rate_fraction_per_min"]
    del h_dict["linear_generator"]["startup_time_hot"]
    del h_dict["linear_generator"]["startup_time_warm"]
    del h_dict["linear_generator"]["startup_time_cold"]
    del h_dict["linear_generator"]["load_stable_min_fraction"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.load_stable_min_fraction == LinearGenerator.DEFAULTS["load_stable_min_fraction"]
    assert lg.startup_time_hot == LinearGenerator.DEFAULTS["startup_time_hot"]
    assert lg.startup_time_warm == LinearGenerator.DEFAULTS["startup_time_warm"]
    assert lg.startup_time_cold == LinearGenerator.DEFAULTS["startup_time_cold"]

    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["up_time_min"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.up_time_min == LinearGenerator.DEFAULTS["up_time_min"]

    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["down_time_min"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.down_time_min == LinearGenerator.DEFAULTS["down_time_min"]

    # Test cooldown threshold defaults
    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["cooldown_time_warm"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.cooldown_time_warm == LinearGenerator.DEFAULTS["cooldown_time_warm"]

    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["cooldown_time_cold"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.cooldown_time_cold == LinearGenerator.DEFAULTS["cooldown_time_cold"]


def test_default_hhv():
    """Test that LinearGenerator provides default HHV for natural gas from [3]."""
    h_dict = copy.deepcopy(h_dict_linear_generator)
    del h_dict["linear_generator"]["HHV"]
    lg = LinearGenerator(h_dict, "linear_generator")
    assert lg.HHV == LinearGenerator.DEFAULTS["HHV"]


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
