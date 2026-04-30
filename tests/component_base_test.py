"""Tests for ComponentBase behavior shared by all plant components."""

import copy

import pytest
from hercules.plant_components.battery_simple import BatterySimple

from .test_inputs.h_dict import battery


def _battery_h_dict(**battery_overrides):
    """Build a minimal h_dict with one BatterySimple component.

    Args:
        **battery_overrides: Keys merged into the battery component dict.

    Returns:
        dict: Copy suitable for BatterySimple(h_dict, "battery").
    """
    batt = copy.deepcopy(battery)
    batt.update(battery_overrides)
    return {
        "dt": 1.0,
        "starttime": 0.0,
        "endtime": 10.0,
        "verbose": False,
        "plant": {"interconnect_limit": 30000.0},
        "battery": batt,
    }


def test_component_group_defaults_to_component_name():
    """When component_group is omitted, it equals component_name and is written to h_dict."""
    h_dict = _battery_h_dict()
    assert "component_group" not in h_dict["battery"]

    battery_obj = BatterySimple(h_dict, "battery")

    assert battery_obj.component_group == "battery"
    assert h_dict["battery"]["component_group"] == "battery"


def test_component_group_explicit_value():
    """Explicit component_group is stored on the instance and echoed into h_dict."""
    h_dict = _battery_h_dict(component_group="hybrid_unit_a")

    battery_obj = BatterySimple(h_dict, "battery")

    assert battery_obj.component_group == "hybrid_unit_a"
    assert h_dict["battery"]["component_group"] == "hybrid_unit_a"


def test_component_group_must_be_string():
    """Non-string component_group raises TypeError."""
    h_dict = _battery_h_dict(component_group=42)

    with pytest.raises(TypeError, match="component_group"):
        BatterySimple(h_dict, "battery")
