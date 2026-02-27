"""Tests for the WindFarmSCADAPower class."""

import copy
import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from hercules.plant_components.wind_farm_scada_power import WindFarmSCADAPower
from hercules.utilities import hercules_float_type

from tests.test_inputs.h_dict import h_dict_wind

# Create a base test dictionary for WindFarmSCADAPower
h_dict_wind_scada = copy.deepcopy(h_dict_wind)
# Update component type and remove unneeded parameters
h_dict_wind_scada["wind_farm"]["component_type"] = "WindFarmSCADAPower"
h_dict_wind_scada["wind_farm"]["scada_filename"] = "tests/test_inputs/scada_input.csv"
# Remove FLORIS-specific parameters
del h_dict_wind_scada["wind_farm"]["floris_input_file"]
del h_dict_wind_scada["wind_farm"]["wind_input_filename"]
del h_dict_wind_scada["wind_farm"]["floris_update_time_s"]


def test_wind_farm_scada_power_initialization():
    """Test that WindFarmSCADAPower initializes correctly with valid inputs."""
    wind_sim = WindFarmSCADAPower(h_dict_wind_scada, "wind_farm")

    assert wind_sim.component_name == "wind_farm"
    assert wind_sim.component_type == "WindFarmSCADAPower"
    assert wind_sim.n_turbines == 3
    assert wind_sim.dt == 1.0
    assert wind_sim.starttime == 0.0
    assert wind_sim.endtime == 10.0


def test_wind_farm_scada_power_infers_n_turbines():
    """Test that number of turbines is correctly inferred from power columns."""
    wind_sim = WindFarmSCADAPower(h_dict_wind_scada, "wind_farm")

    assert wind_sim.n_turbines == 3
    assert len(wind_sim.power_columns) == 3
    assert wind_sim.power_columns == ["pow_000", "pow_001", "pow_002"]


def test_wind_farm_scada_power_infers_rated_power():
    """Test that rated power is correctly inferred from 99th percentile."""
    wind_sim = WindFarmSCADAPower(h_dict_wind_scada, "wind_farm")

    # Check that rated power is positive and reasonable
    assert wind_sim.rated_turbine_power == 5000.0
    assert wind_sim.capacity == wind_sim.n_turbines * wind_sim.rated_turbine_power


def test_wind_farm_scada_power_no_wakes():
    """Test that no wake deficits are applied in SCADA power mode."""
    wind_sim = WindFarmSCADAPower(h_dict_wind_scada, "wind_farm")

    # Verify initial wake deficits are zero
    assert np.all(wind_sim.floris_wake_deficits == 0.0)

    # Verify initial wind speeds with wakes equal background
    assert np.allclose(wind_sim.wind_speeds_withwakes, wind_sim.wind_speeds_background)


def test_wind_farm_scada_power_step():
    """Test that the step method works correctly."""
    wind_sim = WindFarmSCADAPower(h_dict_wind_scada, "wind_farm")

    step_h_dict = {"step": 1}
    step_h_dict["wind_farm"] = {}

    result = wind_sim.step(step_h_dict)

    # Verify outputs exist
    assert "turbine_powers" in result["wind_farm"]
    assert "power" in result["wind_farm"]
    assert len(result["wind_farm"]["turbine_powers"]) == 3
    assert isinstance(result["wind_farm"]["turbine_powers"], np.ndarray)
    assert isinstance(result["wind_farm"]["power"], (int, float, np.floating))

    # Verify no wake deficits applied
    assert np.all(wind_sim.floris_wake_deficits == 0.0)
    assert np.allclose(
        result["wind_farm"]["wind_speeds_withwakes"],
        result["wind_farm"]["wind_speeds_background"],
    )

    # Verify turbine powers
    assert np.allclose(result["wind_farm"]["turbine_powers"], [3200.0, 3100.0, 3300.0])
    assert np.isclose(result["wind_farm"]["power"], 3200.0 + 3100.0 + 3300.0)


def test_wind_farm_scada_power_get_initial_conditions_and_meta_data():
    """Test that get_initial_conditions_and_meta_data adds correct metadata to h_dict."""
    wind_sim = WindFarmSCADAPower(h_dict_wind_scada, "wind_farm")

    # Create a copy of the input h_dict to avoid modifying the original
    test_h_dict_copy = copy.deepcopy(h_dict_wind_scada)

    # Call the method
    result = wind_sim.get_initial_conditions_and_meta_data(test_h_dict_copy)

    # Verify that the method returns the modified h_dict
    assert result is test_h_dict_copy

    # Verify that all expected metadata is added to the wind_farm section
    assert "n_turbines" in result["wind_farm"]
    assert "capacity" in result["wind_farm"]
    assert "rated_turbine_power" in result["wind_farm"]
    assert "wind_direction_mean" in result["wind_farm"]
    assert "wind_speed_mean_background" in result["wind_farm"]
    assert "turbine_powers" in result["wind_farm"]

    # Verify the values match the wind_sim attributes
    assert result["wind_farm"]["n_turbines"] == wind_sim.n_turbines
    assert result["wind_farm"]["capacity"] == wind_sim.capacity
    assert result["wind_farm"]["rated_turbine_power"] == wind_sim.rated_turbine_power
    assert result["wind_farm"]["wind_direction_mean"] == wind_sim.wd_mat_mean[0]
    assert result["wind_farm"]["wind_speed_mean_background"] == wind_sim.ws_mat_mean[0]

    # Verify turbine_powers is a numpy array with correct length
    assert isinstance(result["wind_farm"]["turbine_powers"], np.ndarray)
    assert len(result["wind_farm"]["turbine_powers"]) == wind_sim.n_turbines
    np.testing.assert_array_equal(result["wind_farm"]["turbine_powers"], wind_sim.turbine_powers)

    # Verify that the original h_dict structure is preserved
    assert "dt" in result
    assert "starttime" in result
    assert "endtime" in result
    assert "plant" in result


def test_wind_farm_scada_power_time_utc_handling():
    """Test that time_utc is correctly parsed and validated."""
    # Create wind input data with time_utc columns
    scada_data = {
        "time_utc": [
            "2023-01-01T00:00:00Z",
            "2023-01-01T00:00:01Z",
            "2023-01-01T00:00:02Z",
            "2023-01-01T00:00:03Z",
            "2023-01-01T00:00:04Z",
        ],
        "wd_mean": [270.0, 275.0, 280.0, 285.0, 290.0],
        "ws_000": [8.0, 9.0, 10.0, 11.0, 12.0],
        "ws_001": [8.5, 9.5, 10.5, 11.5, 12.5],
        "ws_002": [9.0, 10.0, 11.0, 12.0, 13.0],
        "pow_000": [2500.0, 3200.0, 4000.0, 4500.0, 5000.0],
        "pow_001": [2400.0, 3100.0, 3900.0, 4400.0, 4900.0],
        "pow_002": [2600.0, 3300.0, 4100.0, 4600.0, 5000.0],
    }

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df = pd.DataFrame(scada_data)
        df.to_csv(f.name, index=False)
        temp_scada_file = f.name

    try:
        # Create test h_dict with the temporary scada file
        test_h_dict = copy.deepcopy(h_dict_wind_scada)
        test_h_dict["wind_farm"]["scada_filename"] = temp_scada_file
        test_h_dict["starttime"] = 0.0
        test_h_dict["endtime"] = 4.0
        test_h_dict["starttime_utc"] = "2023-01-01T00:00:00Z"
        test_h_dict["endtime_utc"] = "2023-01-01T00:00:04Z"
        test_h_dict["dt"] = 1.0

        # Initialize wind simulation
        wind_sim = WindFarmSCADAPower(test_h_dict, "wind_farm")

        # Verify that starttime_utc is set correctly
        assert hasattr(wind_sim, "starttime_utc"), "starttime_utc should be set"

        expected_start_time = pd.to_datetime("2023-01-01T00:00:00Z", utc=True)

        # Convert to pandas Timestamp for comparison
        actual_start_time = pd.Timestamp(wind_sim.starttime_utc)

        # Compare datetime values
        assert actual_start_time.replace(tzinfo=None) == expected_start_time.replace(tzinfo=None), (
            f"starttime_utc mismatch: expected {expected_start_time}, got {actual_start_time}"
        )

    finally:
        # Clean up temporary file
        if os.path.exists(temp_scada_file):
            os.unlink(temp_scada_file)


def test_wind_farm_scada_power_time_utc_validation_start_too_early():
    """Test that error is raised when starttime_utc is before earliest SCADA data."""
    # Create SCADA data starting at 2023-01-01T00:00:00Z
    scada_data = {
        "time_utc": [
            "2023-01-01T00:00:00Z",
            "2023-01-01T00:00:01Z",
            "2023-01-01T00:00:02Z",
        ],
        "wd_mean": [270.0, 275.0, 280.0],
        "ws_000": [8.0, 9.0, 10.0],
        "ws_001": [8.5, 9.5, 10.5],
        "ws_002": [9.0, 10.0, 11.0],
        "pow_000": [2500.0, 3200.0, 4000.0],
        "pow_001": [2400.0, 3100.0, 3900.0],
        "pow_002": [2600.0, 3300.0, 4100.0],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df = pd.DataFrame(scada_data)
        df.to_csv(f.name, index=False)
        temp_scada_file = f.name

    try:
        test_h_dict = copy.deepcopy(h_dict_wind_scada)
        test_h_dict["wind_farm"]["scada_filename"] = temp_scada_file
        test_h_dict["starttime"] = 0.0
        test_h_dict["endtime"] = 2.0
        # Try to start before earliest SCADA data
        test_h_dict["starttime_utc"] = "2022-12-31T23:59:59Z"
        test_h_dict["endtime_utc"] = "2023-01-01T00:00:02Z"
        test_h_dict["dt"] = 1.0

        with pytest.raises(ValueError, match="Start time UTC .* is before the earliest time"):
            WindFarmSCADAPower(test_h_dict, "wind_farm")

    finally:
        if os.path.exists(temp_scada_file):
            os.unlink(temp_scada_file)


def test_wind_farm_scada_power_time_utc_validation_end_too_late():
    """Test that error is raised when endtime_utc is after latest SCADA data."""
    # Create SCADA data ending at 2023-01-01T00:00:02Z
    scada_data = {
        "time_utc": [
            "2023-01-01T00:00:00Z",
            "2023-01-01T00:00:01Z",
            "2023-01-01T00:00:02Z",
        ],
        "wd_mean": [270.0, 275.0, 280.0],
        "ws_000": [8.0, 9.0, 10.0],
        "ws_001": [8.5, 9.5, 10.5],
        "ws_002": [9.0, 10.0, 11.0],
        "pow_000": [2500.0, 3200.0, 4000.0],
        "pow_001": [2400.0, 3100.0, 3900.0],
        "pow_002": [2600.0, 3300.0, 4100.0],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df = pd.DataFrame(scada_data)
        df.to_csv(f.name, index=False)
        temp_scada_file = f.name

    try:
        test_h_dict = copy.deepcopy(h_dict_wind_scada)
        test_h_dict["wind_farm"]["scada_filename"] = temp_scada_file
        test_h_dict["starttime"] = 0.0
        test_h_dict["endtime"] = 5.0
        test_h_dict["starttime_utc"] = "2023-01-01T00:00:00Z"
        # Try to end after latest SCADA data
        test_h_dict["endtime_utc"] = "2023-01-01T00:00:05Z"
        test_h_dict["dt"] = 1.0

        with pytest.raises(ValueError, match="End time UTC .* is after the latest time"):
            WindFarmSCADAPower(test_h_dict, "wind_farm")

    finally:
        if os.path.exists(temp_scada_file):
            os.unlink(temp_scada_file)


def test_wind_farm_scada_power_ws_mean_handling():
    """Test that ws_mean is correctly handled when individual speeds are not present."""
    # Create SCADA data with ws_mean but no individual speeds
    scada_data = {
        "time_utc": [
            "2023-01-01T00:00:00Z",
            "2023-01-01T00:00:01Z",
            "2023-01-01T00:00:02Z",
            "2023-01-01T00:00:03Z",
            "2023-01-01T00:00:04Z",
        ],
        "wd_mean": [270.0, 275.0, 280.0, 285.0, 290.0],
        "ws_mean": [8.0, 9.0, 10.0, 11.0, 12.0],
        "pow_000": [2500.0, 3200.0, 4000.0, 4500.0, 5000.0],
        "pow_001": [2400.0, 3100.0, 3900.0, 4400.0, 4900.0],
        "pow_002": [2600.0, 3300.0, 4100.0, 4600.0, 5000.0],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df = pd.DataFrame(scada_data)
        df.to_csv(f.name, index=False)
        temp_scada_file = f.name

    try:
        test_h_dict = copy.deepcopy(h_dict_wind_scada)
        test_h_dict["wind_farm"]["scada_filename"] = temp_scada_file
        test_h_dict["starttime"] = 0.0
        test_h_dict["endtime"] = 4.0
        test_h_dict["starttime_utc"] = "2023-01-01T00:00:00Z"
        test_h_dict["endtime_utc"] = "2023-01-01T00:00:04Z"
        test_h_dict["dt"] = 1.0

        wind_sim = WindFarmSCADAPower(test_h_dict, "wind_farm")

        # Verify that ws_mat is properly tiled from ws_mean
        assert wind_sim.ws_mat.shape == (4, 3)
        # All turbines should have the same wind speed (from ws_mean)
        assert (wind_sim.ws_mat[:, 0] == wind_sim.ws_mat[:, 1]).all()
        assert (wind_sim.ws_mat[:, 1] == wind_sim.ws_mat[:, 2]).all()

    finally:
        if os.path.exists(temp_scada_file):
            os.unlink(temp_scada_file)


def test_wind_farm_scada_power_output_consistency():
    """Test that outputs are consistent with no wake modeling."""
    wind_sim = WindFarmSCADAPower(h_dict_wind_scada, "wind_farm")

    # Run a step
    step_h_dict = {"step": 2}
    step_h_dict["wind_farm"] = {}

    result = wind_sim.step(step_h_dict)

    # Calculate expected mean withwakes speed (should equal background mean)
    expected_mean_withwakes = np.mean(
        result["wind_farm"]["wind_speeds_background"], dtype=hercules_float_type
    )

    assert np.isclose(result["wind_farm"]["wind_speed_mean_withwakes"], expected_mean_withwakes)

    # Total power should be sum of turbine powers
    assert np.isclose(result["wind_farm"]["power"], np.sum(result["wind_farm"]["turbine_powers"]))


def test_wind_farm_scada_power_multiple_file_formats():
    """Test that SCADA data can be loaded from different file formats."""
    # Test CSV (already tested above, but included for completeness)
    wind_sim_csv = WindFarmSCADAPower(h_dict_wind_scada, "wind_farm")
    assert wind_sim_csv.n_turbines == 3

    # Test pickle format
    current_dir = os.path.dirname(__file__)
    df_scada = pd.read_csv(current_dir + "/test_inputs/scada_input.csv")

    # Create temporary pickle file
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        df_scada.to_pickle(f.name)
        temp_pickle_file = f.name

    try:
        test_h_dict = copy.deepcopy(h_dict_wind_scada)
        test_h_dict["wind_farm"]["scada_filename"] = temp_pickle_file

        wind_sim_pkl = WindFarmSCADAPower(test_h_dict, "wind_farm")
        assert wind_sim_pkl.n_turbines == 3

    finally:
        if os.path.exists(temp_pickle_file):
            os.unlink(temp_pickle_file)

    # Test feather format
    with tempfile.NamedTemporaryFile(suffix=".ftr", delete=False) as f:
        df_scada.to_feather(f.name)
        temp_feather_file = f.name

    try:
        test_h_dict = copy.deepcopy(h_dict_wind_scada)
        test_h_dict["wind_farm"]["scada_filename"] = temp_feather_file

        wind_sim_ftr = WindFarmSCADAPower(test_h_dict, "wind_farm")
        assert wind_sim_ftr.n_turbines == 3

    finally:
        if os.path.exists(temp_feather_file):
            os.unlink(temp_feather_file)


def test_wind_farm_scada_power_invalid_file_format():
    """Test that invalid file format raises ValueError."""
    test_h_dict = copy.deepcopy(h_dict_wind_scada)
    test_h_dict["wind_farm"]["scada_filename"] = "tests/test_inputs/invalid.txt"

    # Create a dummy file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("dummy")
        temp_file = f.name

    try:
        test_h_dict["wind_farm"]["scada_filename"] = temp_file

        with pytest.raises(ValueError, match="SCADA file must be a .csv or .p, .f or .ftr file"):
            WindFarmSCADAPower(test_h_dict, "wind_farm")

    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)
