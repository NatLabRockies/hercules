"""Tests for the PowerPlayback class."""

import copy

import numpy as np
from hercules.plant_components.power_playback import PowerPlayback

from tests.test_inputs.h_dict import h_dict_power_playback

# Create a base test dictionary for PowerPlayback
h_dict_power_playback = copy.deepcopy(h_dict_power_playback)


def test_power_playback_initialization():
    """Test that PowerPlayback initializes correctly with valid inputs."""
    power_playback = PowerPlayback(h_dict_power_playback, "power_playback")

    assert power_playback.component_name == "power_playback"
    assert power_playback.component_type == "PowerPlayback"
    assert power_playback.component_category == "generator"
    assert power_playback.dt == 1.0
    assert power_playback.starttime == 0.0
    assert power_playback.endtime == 10.0


def test_power_playback_step():
    """Test that the step method works correctly."""
    power_playback = PowerPlayback(h_dict_power_playback, "power_playback")

    step_h_dict = {"step": 0}
    step_h_dict["power_playback"] = {}

    result = power_playback.step(step_h_dict)

    # Verify outputs exist
    assert "power" in result["power_playback"]

    # Verify power
    assert np.isclose(result["power_playback"]["power"], 1000.0)

    # Step one more time
    step_h_dict["step"] = 1
    result = power_playback.step(step_h_dict)

    # Verify power
    assert np.isclose(result["power_playback"]["power"], 2000.0)
