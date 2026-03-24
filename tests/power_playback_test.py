"""Tests for the PowerPlayback class."""

import copy
import os
import tempfile

import numpy as np
import pandas as pd
import pytest
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


def test_power_playback_raises_on_nan_in_power_columns():
    """Test that PowerPlayback raises ValueError when power column contain NaN."""
    scada_data = {
        "time_utc": [
            "2023-01-01T00:00:00Z",
            "2023-01-01T00:00:01Z",
            "2023-01-01T00:00:02Z",
            "2023-01-01T00:00:03Z",
            "2023-01-01T00:00:04Z",
        ],
        "power": [2500.0, np.nan, 4000.0, 4500.0, 5000.0],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        pd.DataFrame(scada_data).to_csv(f.name, index=False)
        temp_scada_file = f.name

    try:
        test_h_dict = copy.deepcopy(h_dict_power_playback)
        test_h_dict["power_playback"]["scada_filename"] = temp_scada_file
        test_h_dict["starttime"] = 0.0
        test_h_dict["endtime"] = 4.0
        test_h_dict["starttime_utc"] = "2023-01-01T00:00:00Z"
        test_h_dict["endtime_utc"] = "2023-01-01T00:00:04Z"
        test_h_dict["dt"] = 1.0

        with pytest.raises(ValueError, match="SCADA file contains NaN values"):
            PowerPlayback(test_h_dict, "power_playback")
    finally:
        if os.path.exists(temp_scada_file):
            os.unlink(temp_scada_file)
