import copy

import pytest
from hercules import hybrid_plant

from .test_inputs.h_dict import (
    h_dict,
    h_dict_battery,
    h_dict_solar,
    h_dict_wind,
    h_dict_wind_solar_battery,
)


def test_init_from_dict():
    """Test that HybridPlant can be initialized from a dictionary."""
    hybrid_plant_obj = hybrid_plant.HybridPlant(copy.deepcopy(h_dict_wind))
    assert hybrid_plant_obj is not None


def test_no_components_raises_exception():
    """Test that HybridPlant raises an exception when no plant components are found."""
    with pytest.raises(Exception, match="No plant components found in input file"):
        hybrid_plant.HybridPlant(copy.deepcopy(h_dict))


def test_component_names_detection():
    """Test that HybridPlant correctly identifies component names in h_dict with components."""
    hybrid_plant_obj = hybrid_plant.HybridPlant(copy.deepcopy(h_dict_wind))
    assert len(hybrid_plant_obj.component_names) == 1
    assert "wind_farm" in hybrid_plant_obj.component_names


def test_generator_names_detection():
    """Test that HybridPlant correctly identifies generator names in h_dict with generators."""
    hybrid_plant_obj = hybrid_plant.HybridPlant(copy.deepcopy(h_dict_wind))
    assert len(hybrid_plant_obj.generator_names) == 1
    assert "wind_farm" in hybrid_plant_obj.generator_names


def test_n_components_count():
    """Test that HybridPlant correctly counts the number of components."""
    hybrid_plant_obj = hybrid_plant.HybridPlant(copy.deepcopy(h_dict_wind))
    assert hybrid_plant_obj.n_components == 1


def test_component_objects_creation():
    """Test that HybridPlant creates component objects correctly."""
    hybrid_plant_obj = hybrid_plant.HybridPlant(copy.deepcopy(h_dict_wind))
    assert len(hybrid_plant_obj.component_objects) == 1
    assert "wind_farm" in hybrid_plant_obj.component_objects


def test_wind_farm_only():
    """Test HybridPlant with wind_farm only."""
    hybrid_plant_obj = hybrid_plant.HybridPlant(copy.deepcopy(h_dict_wind))

    assert len(hybrid_plant_obj.component_names) == 1
    assert "wind_farm" in hybrid_plant_obj.component_names
    assert len(hybrid_plant_obj.generator_names) == 1
    assert "wind_farm" in hybrid_plant_obj.generator_names
    assert hybrid_plant_obj.n_components == 1


def test_solar_farm_only():
    """Test HybridPlant with solar_farm only."""
    hybrid_plant_obj = hybrid_plant.HybridPlant(copy.deepcopy(h_dict_solar))

    assert len(hybrid_plant_obj.component_names) == 1
    assert "solar_farm" in hybrid_plant_obj.component_names
    assert len(hybrid_plant_obj.generator_names) == 1
    assert "solar_farm" in hybrid_plant_obj.generator_names
    assert hybrid_plant_obj.n_components == 1


def test_battery_only():
    """Test HybridPlant with battery only."""
    hybrid_plant_obj = hybrid_plant.HybridPlant(copy.deepcopy(h_dict_battery))

    assert len(hybrid_plant_obj.component_names) == 1
    assert "battery" in hybrid_plant_obj.component_names
    assert len(hybrid_plant_obj.generator_names) == 0  # Battery is not a generator
    assert hybrid_plant_obj.n_components == 1


def test_all_three_components():
    """Test HybridPlant with all three plant components."""
    hybrid_plant_obj = hybrid_plant.HybridPlant(copy.deepcopy(h_dict_wind_solar_battery))

    assert len(hybrid_plant_obj.component_names) == 3
    assert "wind_farm" in hybrid_plant_obj.component_names
    assert "solar_farm" in hybrid_plant_obj.component_names
    assert "battery" in hybrid_plant_obj.component_names
    assert len(hybrid_plant_obj.generator_names) == 2
    assert "wind_farm" in hybrid_plant_obj.generator_names
    assert "solar_farm" in hybrid_plant_obj.generator_names
    assert hybrid_plant_obj.n_components == 3


def test_unknown_component_type():
    """Test that HybridPlant raises an exception for unknown component types."""
    invalid_h_dict = copy.deepcopy(h_dict_wind)
    invalid_h_dict["wind_farm"]["component_type"] = "UnknownType"

    with pytest.raises(Exception, match="Unknown component_type"):
        hybrid_plant.HybridPlant(invalid_h_dict)


def test_add_plant_metadata_to_h_dict():
    """Test that HybridPlant correctly adds plant metadata to h_dict."""
    hybrid_plant_obj = hybrid_plant.HybridPlant(copy.deepcopy(h_dict_wind_solar_battery))
    test_h_dict = copy.deepcopy(h_dict_wind_solar_battery)
    result = hybrid_plant_obj.add_plant_metadata_to_h_dict(test_h_dict)

    assert "component_names" in result
    assert "generator_names" in result
    assert "n_components" in result


def test_component_category_attributes():
    """Test that component objects expose the correct component_category class attribute."""
    hp = hybrid_plant.HybridPlant(copy.deepcopy(h_dict_wind_solar_battery))

    assert hp.component_objects["wind_farm"].component_category == "generator"
    assert hp.component_objects["solar_farm"].component_category == "generator"
    assert hp.component_objects["battery"].component_category == "storage"


def test_component_type_auto_set():
    """Test that component_type is automatically derived from the class name."""
    hp = hybrid_plant.HybridPlant(copy.deepcopy(h_dict_wind_solar_battery))

    assert hp.component_objects["wind_farm"].component_type == "WindFarm"
    assert hp.component_objects["solar_farm"].component_type == "SolarPySAMPVWatts"
    assert hp.component_objects["battery"].component_type == "BatterySimple"


def test_multi_instance_batteries():
    """Test that two BatterySimple instances with unique names can coexist in one plant."""
    battery_cfg = {
        "component_type": "BatterySimple",
        "energy_capacity": 100.0,
        "charge_rate": 50.0,
        "discharge_rate": 50.0,
        "max_SOC": 0.9,
        "min_SOC": 0.1,
        "log_channels": ["power"],
        "initial_conditions": {"SOC": 0.5},
    }
    multi_battery_h_dict = copy.deepcopy(h_dict_battery)
    multi_battery_h_dict["battery_unit_2"] = copy.deepcopy(battery_cfg)

    hp = hybrid_plant.HybridPlant(multi_battery_h_dict)

    assert hp.n_components == 2
    assert "battery" in hp.component_names
    assert "battery_unit_2" in hp.component_names
    # Each instance carries its unique component_name
    assert hp.component_objects["battery"].component_name == "battery"
    assert hp.component_objects["battery_unit_2"].component_name == "battery_unit_2"
    # Both have battery category → neither is a generator
    assert len(hp.generator_names) == 0


def test_custom_component_name_passed_through():
    """Test that the YAML key becomes the component_name on the instantiated object."""
    hp = hybrid_plant.HybridPlant(copy.deepcopy(h_dict_wind))

    assert hp.component_objects["wind_farm"].component_name == "wind_farm"
