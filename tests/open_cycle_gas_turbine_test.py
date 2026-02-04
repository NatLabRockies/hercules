import copy

import pytest
from hercules.plant_components.open_cycle_gas_turbine import OpenCycleGasTurbine

from .test_inputs.h_dict import (
    h_dict_open_cycle_gas_turbine,
)


def test_init_from_dict():
    """Test that ThermalComponentBase can be initialized from a dictionary."""
    ocgt = OpenCycleGasTurbine(copy.deepcopy(h_dict_open_cycle_gas_turbine))
    assert ocgt is not None


def test_invalid_inputs():
    """Test that OpenCycleGasTurbine raises an error for invalid inputs."""
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)

    # Test only the parameters that are specific to OCGT
    h_dict["open_cycle_gas_turbine"]["part_load_factor"] = 0.9
    with pytest.raises(ValueError):
        OpenCycleGasTurbine(h_dict)
    h_dict["open_cycle_gas_turbine"]["part_load_factor"] = 2.1
    with pytest.raises(ValueError):
        OpenCycleGasTurbine(h_dict)
    h_dict["open_cycle_gas_turbine"]["heat_rate_at_rated_load"] = 0
    with pytest.raises(ValueError):
        OpenCycleGasTurbine(h_dict)


def test_default_inputs():
    """Test that OpenCycleGasTurbine uses default inputs when not provided."""
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    del h_dict["open_cycle_gas_turbine"]["part_load_factor"]
    del h_dict["open_cycle_gas_turbine"]["heat_rate_at_rated_load"]
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.part_load_factor == 1.0
    assert ocgt.heat_rate_at_rated_load == 10000

    # Test that the ramp_rate_fraction is 0.5
    assert ocgt.ramp_rate_fraction == 0.5

    # Test that the run_up_rate_fraction is 0.2
    assert ocgt.run_up_rate_fraction == 0.2

    # Test that if the run_up_rate_fraction is not provided,
    # it defaults to the ramp_rate_fraction
    del h_dict["open_cycle_gas_turbine"]["run_up_rate_fraction"]
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.run_up_rate_fraction == ocgt.ramp_rate_fraction

    # Now test that the default value of the ramp_rate_fraction is
    # applied to both the ramp_rate_fraction and the run_up_rate_fraction
    # if they are both not provided
    del h_dict["open_cycle_gas_turbine"]["ramp_rate_fraction"]
    del h_dict["open_cycle_gas_turbine"]["run_up_rate_fraction"]
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.ramp_rate_fraction == 0.1
    assert ocgt.run_up_rate_fraction == 0.1

    # Test the remaining default values
    del h_dict["open_cycle_gas_turbine"]["min_stable_load_fraction"]
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.min_stable_load_fraction == 0.2

    del h_dict["open_cycle_gas_turbine"]["cold_startup_time"]
    del h_dict["open_cycle_gas_turbine"]["hot_startup_time"]
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.hot_startup_time == 7 * 60.0
    assert ocgt.cold_startup_time == 8 * 60.0

    del h_dict["open_cycle_gas_turbine"]["hot_cold_cutoff_time"]
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.hot_cold_cutoff_time == 8 * 60.0 * 60.0

    del h_dict["open_cycle_gas_turbine"]["min_up_time"]
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.min_up_time == 2 * 60.0 * 60.0

    del h_dict["open_cycle_gas_turbine"]["min_down_time"]
    ocgt = OpenCycleGasTurbine(h_dict)
    assert ocgt.min_down_time == 2 * 60.0 * 60.0


# TODO: Someone familiar with heat rate and fuel consumption please add tests based
# on first principles for the heat rate and fuel consumption.
def test_post_process():
    """Test that OpenCycleGasTurbine post-processes correctly."""
    h_dict = copy.deepcopy(h_dict_open_cycle_gas_turbine)
    ocgt = OpenCycleGasTurbine(h_dict)
    h_dict = ocgt._post_process(h_dict)
