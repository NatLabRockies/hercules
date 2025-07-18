import copy

import pytest
from hercules import py_sims

from .test_inputs.h_dict import (
    h_dict,
    h_dict_battery,
    h_dict_solar,
    h_dict_wind,
    h_dict_wind_solar_battery,
)


def test_init_from_dict():
    """Test that PySims can be initialized from a dictionary."""
    pysims = py_sims.PySims(copy.deepcopy(h_dict_wind))
    assert pysims is not None


def test_no_py_sims_raises_exception():
    """Test that PySims raises an exception when no py_sims are found in input file."""
    with pytest.raises(Exception, match="No py_sims found in input file"):
        py_sims.PySims(copy.deepcopy(h_dict))


def test_py_sim_names_detection():
    """Test that PySims correctly identifies py_sim names in h_dict with py_sims."""
    pysims = py_sims.PySims(copy.deepcopy(h_dict_wind))
    assert len(pysims.py_sim_names) == 1
    assert "wind_farm" in pysims.py_sim_names


def test_generator_names_detection():
    """Test that PySims correctly identifies generator names in h_dict with generators."""
    pysims = py_sims.PySims(copy.deepcopy(h_dict_wind))
    assert len(pysims.generator_names) == 1
    assert "wind_farm" in pysims.generator_names


def test_n_py_sim_count():
    """Test that PySims correctly counts the number of py_sims."""
    pysims = py_sims.PySims(copy.deepcopy(h_dict_wind))
    assert pysims.n_py_sim == 1


def test_py_sim_objects_creation():
    """Test that PySims creates py_sim objects correctly."""
    pysims = py_sims.PySims(copy.deepcopy(h_dict_wind))
    assert len(pysims.py_sim_objects) == 1
    assert "wind_farm" in pysims.py_sim_objects


def test_wind_farm_only():
    """Test PySims with wind_farm only."""
    pysims = py_sims.PySims(copy.deepcopy(h_dict_wind))

    assert len(pysims.py_sim_names) == 1
    assert "wind_farm" in pysims.py_sim_names
    assert len(pysims.generator_names) == 1
    assert "wind_farm" in pysims.generator_names
    assert pysims.n_py_sim == 1


def test_solar_farm_only():
    """Test PySims with solar_farm only."""
    pysims = py_sims.PySims(copy.deepcopy(h_dict_solar))

    assert len(pysims.py_sim_names) == 1
    assert "solar_farm" in pysims.py_sim_names
    assert len(pysims.generator_names) == 1
    assert "solar_farm" in pysims.generator_names
    assert pysims.n_py_sim == 1


def test_battery_only():
    """Test PySims with battery only."""
    pysims = py_sims.PySims(copy.deepcopy(h_dict_battery))

    assert len(pysims.py_sim_names) == 1
    assert "battery" in pysims.py_sim_names
    assert len(pysims.generator_names) == 0  # Battery is not a generator
    assert pysims.n_py_sim == 1


def test_all_three_py_sims():
    """Test PySims with all three py_sim components."""
    pysims = py_sims.PySims(copy.deepcopy(h_dict_wind_solar_battery))

    assert len(pysims.py_sim_names) == 3
    assert "wind_farm" in pysims.py_sim_names
    assert "solar_farm" in pysims.py_sim_names
    assert "battery" in pysims.py_sim_names
    assert len(pysims.generator_names) == 2
    assert "wind_farm" in pysims.generator_names
    assert "solar_farm" in pysims.generator_names
    assert pysims.n_py_sim == 3


def test_unknown_py_sim_type():
    """Test that PySims raises an exception for unknown py_sim types."""
    invalid_h_dict = copy.deepcopy(h_dict_battery)
    invalid_h_dict["battery"]["py_sim_type"] = "UnknownType"

    with pytest.raises(Exception, match="Unknown py_sim_type"):
        py_sims.PySims(invalid_h_dict)


def test_add_py_sim_metadata_to_h_dict():
    """Test that add_py_sim_metadata_to_h_dict calls all py_sim methods."""
    pysims = py_sims.PySims(copy.deepcopy(h_dict_wind_solar_battery))

    # Create a copy of the input h_dict
    test_h_dict = copy.deepcopy(h_dict_wind_solar_battery)

    # Call the method
    result = pysims.add_py_sim_metadata_to_h_dict(test_h_dict)

    # Verify that the method returns the modified h_dict
    assert result is test_h_dict

    # Verify that wind_farm adds its metadata (it's the only one that actually adds data)
    assert "n_turbines" in result["wind_farm"]
    assert "capacity" in result["wind_farm"]
    assert "rated_turbine_power" in result["wind_farm"]
    assert "wind_direction" in result["wind_farm"]
    assert "wind_speed" in result["wind_farm"]
    assert "turbine_powers" in result["wind_farm"]

    # Verify that solar_farm and battery sections still exist (they don't add metadata)
    assert "solar_farm" in result
    assert "battery" in result

    # Verify that the original structure is preserved
    assert "dt" in result
    assert "plant" in result
