"""Tests for HerculesOutput convenience class."""

import os
import tempfile

import h5py
import numpy as np
import pandas as pd
import pytest
from hercules.hercules_output import HerculesOutput


def create_test_hdf5_file(filename: str):
    """Create a test HDF5 file with sample Hercules output data.

    Args:
        filename (str): Path to the test file to create.
    """
    with h5py.File(filename, "w") as f:
        # Create basic data structure
        f.create_group("data")
        f.create_group("metadata")

        # Add time data
        f["data/time"] = np.array([0, 1, 2, 3, 4, 5])
        f["data/step"] = np.array([0, 1, 2, 3, 4, 5])

        # Add plant data
        f["data/plant_power"] = np.array([100, 200, 300, 400, 500, 600])
        f["data/plant_locally_generated_power"] = np.array([90, 180, 270, 360, 450, 540])

        # Add components group
        components_group = f.create_group("data/components")
        components_group["wind_farm.power"] = np.array([50, 100, 150, 200, 250, 300])
        components_group["solar_farm.power"] = np.array([40, 80, 120, 160, 200, 240])

        # Add external signals
        external_signals_group = f.create_group("data/external_signals")
        external_signals_group["external_signals.wind_speed"] = np.array(
            [8.5, 9.0, 8.8, 9.2, 8.9, 9.1]
        )
        external_signals_group["external_signals.temperature"] = np.array(
            [20.0, 21.0, 20.5, 22.0, 21.5, 22.5]
        )

        # Add metadata
        f["metadata"].attrs["dt_sim"] = 1.0
        f["metadata"].attrs["dt_log"] = 5.0
        f["metadata"].attrs["log_every_n"] = 5
        f["metadata"].attrs["start_clock_time"] = 1234567890.0
        f["metadata"].attrs["end_clock_time"] = 1234567895.0
        f["metadata"].attrs["starttime_utc"] = 1234567890.0  # Unix timestamp for UTC time

        # Add h_dict as JSON string
        import json

        test_h_dict = {
            "simulation": {"dt_sim": 1.0, "dt_log": 5.0, "t_final": 30.0},
            "plant": {"name": "test_plant"},
        }
        f["metadata"].attrs["h_dict"] = json.dumps(test_h_dict)


def test_hercules_output_initialization():
    """Test HerculesOutput initialization with filename."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
        temp_file = f.name

    try:
        create_test_hdf5_file(temp_file)

        ho = HerculesOutput(temp_file)
        assert ho.filename == temp_file
        assert isinstance(ho.metadata, dict)
        assert isinstance(ho.df, pd.DataFrame)

    finally:
        os.unlink(temp_file)


def test_hercules_output_metadata_access():
    """Test accessing metadata via dot notation."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
        temp_file = f.name

    try:
        create_test_hdf5_file(temp_file)

        ho = HerculesOutput(temp_file)

        # Test dot notation access
        assert ho.dt_sim == 1.0
        assert ho.dt_log == 5.0
        assert ho.log_every_n == 5
        assert ho.start_clock_time == 1234567890.0
        assert ho.end_clock_time == 1234567895.0

        # Test h_dict access
        assert "simulation" in ho.h_dict
        assert ho.h_dict["simulation"]["dt_sim"] == 1.0
        assert ho.h_dict["plant"]["name"] == "test_plant"

    finally:
        os.unlink(temp_file)


def test_hercules_output_data_access():
    """Test accessing simulation data."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
        temp_file = f.name

    try:
        create_test_hdf5_file(temp_file)

        ho = HerculesOutput(temp_file)

        # Test data access
        data = ho.df
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 6  # 6 time steps
        assert "time" in data.columns
        assert "step" in data.columns
        assert "plant.power" in data.columns
        assert "plant.locally_generated_power" in data.columns
        assert "wind_farm.power" in data.columns
        assert "solar_farm.power" in data.columns
        assert "external_signals.wind_speed" in data.columns
        assert "external_signals.temperature" in data.columns

        # Test some values
        np.testing.assert_array_equal(data["time"], [0, 1, 2, 3, 4, 5])
        np.testing.assert_array_equal(data["plant.power"], [100, 200, 300, 400, 500, 600])

    finally:
        os.unlink(temp_file)


def test_hercules_output_invalid_attribute():
    """Test that invalid attributes raise AttributeError."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
        temp_file = f.name

    try:
        create_test_hdf5_file(temp_file)

        ho = HerculesOutput(temp_file)

        # Test invalid attribute
        with pytest.raises(AttributeError):
            _ = ho.invalid_attribute

    finally:
        os.unlink(temp_file)


def test_hercules_output_print_metadata():
    """Test print_metadata method."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
        temp_file = f.name

    try:
        create_test_hdf5_file(temp_file)

        ho = HerculesOutput(temp_file)

        # Test that print_metadata doesn't raise an exception
        # We can't easily test the output since it goes to stdout
        # but we can verify the method exists and is callable
        assert hasattr(ho, "print_metadata")
        assert callable(ho.print_metadata)

        # Call the method to ensure it works
        ho.print_metadata()

    finally:
        os.unlink(temp_file)
