import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from hercules.utilities import (
    find_time_utc_value,
    interpolate_df,
    interpolate_df_fast,
    load_h_dict_from_text,
    load_hercules_input,
    local_time_to_utc,
)


def test_upsampling():
    """
    Test upsampling with interpolate_df function.

    Creates a simple DataFrame with linear values and tests interpolation
    by upsampling (adding more points between existing ones).
    """
    # Create a simple dataframe with time points 0, 2, 4, 6, 8, 10
    # and linear values for 'value' column
    df = pd.DataFrame(
        {
            "time": [0, 2, 4, 6, 8, 10],
            "value": [0, 2, 4, 6, 8, 10],  # Linear function y = x
        }
    )

    # Create new_time with more points (upsampling)
    new_time = np.linspace(0, 10, 11)  # [0, 1, 2, 3, ..., 10]

    # Interpolate
    result = interpolate_df(df, new_time)

    # Assert time is correct
    assert np.allclose(result["time"], new_time)

    # Assert values are correct
    expected_values = new_time  # Linear function y = x
    assert np.allclose(result["value"], expected_values), "Interpolated values should match y = x"


def test_downsampling():
    """
    Test downsampling with interpolate_df function.

    Creates a simple DataFrame with a non-linear (quadratic) function
    and tests interpolation by downsampling (using fewer points).
    """

    time_points = np.linspace(0, 10, 11)
    df = pd.DataFrame({"time": time_points, "value": time_points * 1.7})

    # Create new_time with fewer points (downsampling)
    new_time = np.array([0, 2, 4])

    # Interpolate
    result = interpolate_df(df, new_time)

    # For our quadratic function, the interpolated values should be the square of new_time
    expected_values = new_time * 1.7
    assert np.allclose(result["value"], expected_values)

    # Check the shape is correct
    assert result.shape[0] == len(new_time)


def test_datetime_interpolation():
    """
    Test interpolation of datetime columns with interpolate_df function.

    Creates a DataFrame with a 'time_utc' column containing datetime values
    and tests that datetime interpolation works correctly.
    """
    # Create a simple dataframe with time points and corresponding datetime values
    df = pd.DataFrame(
        {
            "time": [0, 5, 10],
            "value": [10, 20, 30],  # Linear function
            "time_utc": [
                "2023-01-01 00:00:00",
                "2023-01-01 05:00:00",  # 5 hours later
                "2023-01-01 10:00:00",  # 10 hours later
            ],
        }
    )

    # Set time_utc to utc
    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)

    # Create new_time points for interpolation
    new_time = np.array([0, 2.5, 5, 7.5, 10])

    # Interpolate
    result = interpolate_df(df, new_time)

    # Assert time is correct
    assert np.allclose(result["time"], new_time)

    # Assert datetime values are interpolated correctly
    expected_datetimes = pd.to_datetime(
        [
            "2023-01-01 00:00:00",
            "2023-01-01 02:30:00",  # Interpolated value
            "2023-01-01 05:00:00",
            "2023-01-01 07:30:00",  # Interpolated value
            "2023-01-01 10:00:00",
        ],
        utc=True,
    )

    # Assert time interpolated correctly
    assert np.all(result["time_utc"] == expected_datetimes)


def test_load_hercules_input_valid_file():
    """Test loading the existing test input file.

    Verifies that the function can successfully load and validate
    the existing hercules_input_test.yaml file.
    """
    test_file = "tests/test_inputs/hercules_input_test.yaml"
    result = load_hercules_input(test_file)

    # Check required keys are present
    assert "dt" in result
    assert "starttime" in result
    assert "endtime" in result
    assert "plant" in result

    # Check plant structure
    assert isinstance(result["plant"], dict)
    assert "interconnect_limit" in result["plant"]
    assert isinstance(result["plant"]["interconnect_limit"], float)

    # Check component configurations
    assert "wind_farm" in result
    assert "solar_farm" in result
    assert result["wind_farm"]["component_type"] == "Wind_MesoToPower"
    assert result["solar_farm"]["component_type"] == "SolarPySAMPVWatts"

    # Check verbose defaults to False
    assert result["verbose"] is False


def test_load_hercules_input_missing_required_key():
    """Test that missing required key raises ValueError.

    Creates a minimal invalid config missing dt and verifies
    the function raises appropriate error.
    """
    invalid_config = {"starttime": 0.0, "endtime": 30.0, "plant": {"interconnect_limit": 30000.0}}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        import yaml

        yaml.dump(invalid_config, f)
        temp_file = f.name

    try:
        with pytest.raises(ValueError, match="Required key dt not found"):
            load_hercules_input(temp_file)
    finally:
        os.unlink(temp_file)


def test_load_hercules_input_invalid_plant_structure():
    """Test that invalid plant structure raises ValueError.

    Creates a config with plant as string instead of dict
    and verifies the function raises appropriate error.
    """
    invalid_config = {
        "dt": 1.0,
        "starttime_utc": "2018-05-10 12:31:00",
        "endtime_utc": "2018-05-10 12:31:30",
        "plant": "not_a_dict",
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        import yaml

        yaml.dump(invalid_config, f)
        temp_file = f.name

    try:
        with pytest.raises(ValueError, match="Plant must be a dictionary"):
            load_hercules_input(temp_file)
    finally:
        os.unlink(temp_file)


def test_load_hercules_input_invalid_component_type():
    """Test that invalid component_type raises ValueError.

    Creates a config with invalid component_type and verifies
    the function raises appropriate error.
    """
    invalid_config = {
        "dt": 1.0,
        "starttime_utc": "2018-05-10 12:31:00",
        "endtime_utc": "2018-05-10 12:31:30",
        "plant": {"interconnect_limit": 30000.0},
        "wind_farm": {"component_type": "InvalidType"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        import yaml

        yaml.dump(invalid_config, f)
        temp_file = f.name

    try:
        with pytest.raises(ValueError, match="wind_farm has an invalid component_type"):
            load_hercules_input(temp_file)
    finally:
        os.unlink(temp_file)


def test_load_hercules_input_verbose_default():
    """Test that verbose defaults to False when not specified.

    Creates a minimal config without verbose and verifies
    it defaults to False.
    """
    config_without_verbose = {
        "dt": 1.0,
        "starttime_utc": "2018-05-10 12:31:00",
        "endtime_utc": "2018-05-10 12:31:30",
        "plant": {"interconnect_limit": 30000.0},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        import yaml

        yaml.dump(config_without_verbose, f)
        temp_file = f.name

    try:
        result = load_hercules_input(temp_file)
        assert result["verbose"] is False
    finally:
        os.unlink(temp_file)


def test_load_h_dict_from_text_valid_file():
    """Test loading h_dict from a text file created by _save_h_dict_as_text.

    Creates a sample h_dict, saves it to a text file using the same format
    as _save_h_dict_as_text, then loads it back and verifies the content
    matches the original.
    """
    # Create a sample h_dict similar to what would be used in Hercules
    sample_h_dict = {
        "dt": 1.0,
        "starttime": 0.0,
        "endtime": 3600.0,
        "plant": {"interconnect_limit": 30000.0, "location": "test_site"},
        "wind_farm": {"component_type": "Wind_MesoToPower", "capacity": 100.0},
        "solar_farm": {"component_type": "SolarPySAMPVWatts", "capacity": 50.0},
        "verbose": False,
        "time": 1800.0,
        "step": 1800,
        "external_signals": {"wind_speed": 8.5, "solar_irradiance": 750.0},
    }

    # Create a temporary file and write the h_dict in the same format as _save_h_dict_as_text
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(str(sample_h_dict))
        temp_file = f.name

    try:
        # Load the h_dict back from the file
        result = load_h_dict_from_text(temp_file)

        # Verify all keys and values match the original
        assert result == sample_h_dict

        # Verify specific nested structures
        assert result["plant"]["interconnect_limit"] == 30000.0
        assert result["plant"]["location"] == "test_site"
        assert result["wind_farm"]["component_type"] == "Wind_MesoToPower"
        assert result["solar_farm"]["capacity"] == 50.0
        assert result["external_signals"]["wind_speed"] == 8.5

    finally:
        os.unlink(temp_file)


def test_load_h_dict_from_text_file_not_found():
    """Test that FileNotFoundError is raised when file doesn't exist."""
    with pytest.raises(FileNotFoundError, match="Could not find file"):
        load_h_dict_from_text("nonexistent_file.txt")


def test_load_h_dict_from_text_invalid_content():
    """Test that ValueError is raised when file contains invalid content.

    Creates a file with invalid Python dictionary syntax and verifies
    the function raises appropriate error.
    """
    invalid_content = "This is not a valid Python dictionary"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(invalid_content)
        temp_file = f.name

    try:
        with pytest.raises(ValueError, match="Could not parse dictionary"):
            load_h_dict_from_text(temp_file)
    finally:
        os.unlink(temp_file)


def test_load_h_dict_from_text_not_a_dict():
    """Test that ValueError is raised when file contains valid Python but not a dict.

    Creates a file with a valid Python literal that is not a dictionary
    and verifies the function raises appropriate error.
    """
    not_a_dict_content = "[1, 2, 3, 4, 5]"  # Valid Python list, not a dict

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(not_a_dict_content)
        temp_file = f.name

    try:
        with pytest.raises(ValueError, match="File content does not represent a valid dictionary"):
            load_h_dict_from_text(temp_file)
    finally:
        os.unlink(temp_file)


def test_output_configuration_validation():
    """Test validation of new output configuration options."""

    base_h_dict = {
        "dt": 1.0,
        "starttime_utc": "2018-05-10 12:31:00",
        "endtime_utc": "2018-05-10 12:31:10",
        "plant": {"interconnect_limit": 5000},
        "solar_farm": {"component_type": "SolarPySAMPVWatts"},
    }

    # Test valid log_every_n
    test_dict = base_h_dict.copy()
    test_dict["log_every_n"] = 2
    result = load_hercules_input_from_dict(test_dict)
    assert result["log_every_n"] == 2

    test_dict["log_every_n"] = 5
    result = load_hercules_input_from_dict(test_dict)
    assert result["log_every_n"] == 5

    # Test invalid log_every_n
    test_dict["log_every_n"] = 0
    with pytest.raises(ValueError, match="log_every_n must be a positive integer"):
        load_hercules_input_from_dict(test_dict)


def test_load_hercules_input_utc_validation():
    """Test UTC datetime string validation.

    Verifies that:
    - Strings with 'Z' are accepted
    - Naive strings are accepted
    - Strings with timezone offsets are rejected
    """
    # Test accepted formats: explicit UTC with Z
    valid_config_z = {
        "dt": 1.0,
        "starttime_utc": "2020-01-01T00:00:00Z",
        "endtime_utc": "2020-01-01T01:00:00Z",
        "plant": {"interconnect_limit": 30000.0},
    }
    result = load_hercules_input_from_dict(valid_config_z)
    assert isinstance(result["starttime_utc"], pd.Timestamp)
    assert result["starttime_utc"].tz is not None

    # Test accepted formats: naive string (treated as UTC)
    valid_config_naive = {
        "dt": 1.0,
        "starttime_utc": "2020-01-01T00:00:00",
        "endtime_utc": "2020-01-01T01:00:00",
        "plant": {"interconnect_limit": 30000.0},
    }
    result = load_hercules_input_from_dict(valid_config_naive)
    assert isinstance(result["starttime_utc"], pd.Timestamp)
    assert result["starttime_utc"].tz is not None

    # Test rejected formats: timezone offset (positive)
    invalid_config_positive_offset = {
        "dt": 1.0,
        "starttime_utc": "2020-01-01T00:00:00+05:00",
        "endtime_utc": "2020-01-01T01:00:00+05:00",
        "plant": {"interconnect_limit": 30000.0},
    }
    with pytest.raises(ValueError, match="contains a timezone offset"):
        load_hercules_input_from_dict(invalid_config_positive_offset)

    # Test rejected formats: timezone offset (negative)
    invalid_config_negative_offset = {
        "dt": 1.0,
        "starttime_utc": "2020-01-01T00:00:00-08:00",
        "endtime_utc": "2020-01-01T01:00:00-08:00",
        "plant": {"interconnect_limit": 30000.0},
    }
    with pytest.raises(ValueError, match="contains a timezone offset"):
        load_hercules_input_from_dict(invalid_config_negative_offset)

    # Test rejected formats: UTC offset (even +00:00 should use Z)
    invalid_config_utc_offset = {
        "dt": 1.0,
        "starttime_utc": "2020-01-01T00:00:00+00:00",
        "endtime_utc": "2020-01-01T01:00:00+00:00",
        "plant": {"interconnect_limit": 30000.0},
    }
    with pytest.raises(ValueError, match="contains a timezone offset"):
        load_hercules_input_from_dict(invalid_config_utc_offset)


def load_hercules_input_from_dict(h_dict):
    """Helper function to test hercules input validation from a dictionary."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        import yaml

        yaml.dump(h_dict, f)
        temp_file = f.name

    try:
        return load_hercules_input(temp_file)
    finally:
        os.unlink(temp_file)


# ==================== INTERPOLATION COMPARISON TESTS ====================


def test_interpolate_df_functions_identical_simple():
    """Test that interpolate_df and interpolate_df_fast produce identical results for simple case.

    Creates a simple DataFrame with linear values and verifies both functions
    produce exactly the same interpolated results.
    """
    # Create a simple dataframe with time points 0, 2, 4, 6, 8, 10
    df = pd.DataFrame(
        {
            "time": [0, 2, 4, 6, 8, 10],
            "value": [0, 2, 4, 6, 8, 10],  # Linear function y = x
            "power": [0, 4, 16, 36, 64, 100],  # Quadratic function y = x^2
        }
    )

    # Create new_time with more points (upsampling)
    new_time = np.linspace(0, 10, 21)  # 0, 0.5, 1.0, ..., 10.0

    # Interpolate with both functions
    result_original = interpolate_df(df, new_time)
    result_fast = interpolate_df_fast(df, new_time)

    # Verify results are identical
    pd.testing.assert_frame_equal(result_original, result_fast, check_dtype=False)


# ==================== find_time_utc_value TESTS ====================


def test_find_time_utc_interpolates_midpoint():
    """Interpolates UTC between two points at the midpoint time."""
    df = pd.DataFrame(
        {
            "time": [0.0, 10.0],
            "time_utc": pd.to_datetime(
                [
                    "2023-01-01 00:00:00+00:00",
                    "2023-01-01 00:00:10+00:00",
                ],
                utc=True,
            ),
        }
    )

    mid = find_time_utc_value(df, 5.0)
    assert mid == pd.Timestamp("2023-01-01 00:00:05", tz="UTC")


def test_find_time_utc_extrapolates_before_range():
    """Extrapolates UTC for a time before the first sample."""
    df = pd.DataFrame(
        {
            "time": [0.0, 10.0],
            "time_utc": pd.to_datetime(
                [
                    "2023-01-01 00:00:00+00:00",
                    "2023-01-01 00:00:10+00:00",
                ],
                utc=True,
            ),
        }
    )

    # 1 second per unit time -> time=-5 yields -5 seconds from start
    t = find_time_utc_value(df, -5.0)
    assert t == pd.Timestamp("2022-12-31 23:59:55", tz="UTC")


def test_find_time_utc_extrapolates_after_range():
    """Extrapolates UTC for a time after the last sample."""
    df = pd.DataFrame(
        {
            "time": [0.0, 10.0],
            "time_utc": pd.to_datetime(
                [
                    "2023-01-01 00:00:00+00:00",
                    "2023-01-01 00:00:10+00:00",
                ],
                utc=True,
            ),
        }
    )

    t = find_time_utc_value(df, 15.0)
    assert t == pd.Timestamp("2023-01-01 00:00:15", tz="UTC")


def test_interpolate_df_functions_identical_with_datetime():
    """Test that both functions produce identical results with datetime columns.

    Creates a DataFrame with both numeric and datetime columns and verifies
    both interpolation functions produce exactly the same results.
    """
    # Create a dataframe with time, numeric, and datetime columns
    df = pd.DataFrame(
        {
            "time": [0, 5, 10, 15, 20],
            "temperature": [20.0, 25.0, 30.0, 28.0, 22.0],
            "pressure": [1013.25, 1015.0, 1012.0, 1014.5, 1013.8],
            "time_utc": [
                "2023-01-01 00:00:00",
                "2023-01-01 05:00:00",
                "2023-01-01 10:00:00",
                "2023-01-01 15:00:00",
                "2023-01-01 20:00:00",
            ],
        }
    )

    # Convert time_utc to datetime
    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)

    # Create new_time points for interpolation
    new_time = np.array([0, 2.5, 5, 7.5, 10, 12.5, 15, 17.5, 20])

    # Interpolate with both functions
    result_original = interpolate_df(df, new_time)
    result_fast = interpolate_df_fast(df, new_time)

    # Verify results are identical
    pd.testing.assert_frame_equal(result_original, result_fast, check_dtype=False)


def test_interpolate_df_functions_identical_large_dataset():
    """Test that both functions produce identical results for larger datasets.

    Creates a larger DataFrame to test the polars code path and verify
    both functions produce identical results even with size optimizations.
    """
    # Create a larger dataset (>1000 rows to trigger polars path)
    n_points = 1500
    time_orig = np.linspace(0, 1000, n_points)

    # Create multiple columns with different patterns
    df = pd.DataFrame(
        {
            "time": time_orig,
            "wind_speed": 8 + 4 * np.sin(time_orig / 50) + np.random.normal(0, 0.5, n_points),
            "wind_direction": 180 + 45 * np.cos(time_orig / 30) + np.random.normal(0, 5, n_points),
            "temperature": 20 + 10 * np.sin(time_orig / 100) + np.random.normal(0, 1, n_points),
            "pressure": 1013 + 10 * np.cos(time_orig / 80) + np.random.normal(0, 2, n_points),
        }
    )

    # Add a datetime column
    start_time = pd.Timestamp("2023-01-01 00:00:00", tz="UTC")
    df["time_utc"] = start_time + pd.to_timedelta(df["time"], unit="h")

    # Create new time points (downsampling to 500 points)
    new_time = np.linspace(0, 1000, 500)

    # Interpolate with both functions
    result_original = interpolate_df(df, new_time)
    result_fast = interpolate_df_fast(df, new_time)

    # Verify results are identical (allow small floating point differences)
    pd.testing.assert_frame_equal(result_original, result_fast, check_dtype=False, rtol=1e-10)


def test_interpolate_df_functions_identical_edge_cases():
    """Test that both functions handle edge cases identically.

    Tests various edge cases including single data points, identical time points,
    and boundary conditions.
    """
    # Test with minimal dataset (3 points)
    df_minimal = pd.DataFrame(
        {
            "time": [0, 1, 2],
            "value": [10, 20, 30],
        }
    )
    new_time_minimal = np.array([0, 0.5, 1, 1.5, 2])

    result_orig_minimal = interpolate_df(df_minimal, new_time_minimal)
    result_fast_minimal = interpolate_df_fast(df_minimal, new_time_minimal)
    pd.testing.assert_frame_equal(result_orig_minimal, result_fast_minimal, check_dtype=False)

    # Test with boundary points only
    new_time_boundary = np.array([0, 2])
    result_orig_boundary = interpolate_df(df_minimal, new_time_boundary)
    result_fast_boundary = interpolate_df_fast(df_minimal, new_time_boundary)
    pd.testing.assert_frame_equal(result_orig_boundary, result_fast_boundary, check_dtype=False)


def test_interpolate_df_functions_identical_multiple_dtypes():
    """Test both functions with various data types.

    Creates a DataFrame with different numeric types and verifies
    both functions handle them identically.
    """
    df = pd.DataFrame(
        {
            "time": np.array([0, 1, 2, 3, 4], dtype=np.float64),
            "int_col": np.array([10, 20, 30, 40, 50], dtype=np.int32),
            "float32_col": np.array([1.1, 2.2, 3.3, 4.4, 5.5], dtype=np.float32),
            "float64_col": np.array([100.1, 200.2, 300.3, 400.4, 500.5], dtype=np.float64),
        }
    )

    new_time = np.array([0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4])

    result_original = interpolate_df(df, new_time)
    result_fast = interpolate_df_fast(df, new_time)

    # Verify results are identical
    pd.testing.assert_frame_equal(result_original, result_fast, check_dtype=False)


def test_read_hercules_hdf5_external_signals():
    """Test reading external signals from HDF5 file.

    Creates a mock HDF5 file with external signals and verifies
    they are correctly read and added to the DataFrame.
    """
    import h5py

    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
        temp_file = f.name

    try:
        # Create mock HDF5 file with external signals
        with h5py.File(temp_file, "w") as f:
            # Create basic data structure
            f.create_group("data")
            metadata = f.create_group("metadata")

            # Add starttime_utc metadata (required)
            import pandas as pd

            starttime_utc = pd.to_datetime("2018-05-10 12:31:00", utc=True)
            metadata.attrs["starttime_utc"] = starttime_utc.timestamp()

            # Add basic time data
            f["data/time"] = np.array([0, 1, 2])
            f["data/step"] = np.array([0, 1, 2])
            f["data/clock_time"] = np.array([0.0, 1.0, 2.0])

            # Add plant data
            f["data/plant_power"] = np.array([100, 200, 300])
            f["data/plant_locally_generated_power"] = np.array([90, 180, 270])

            # Add components group (required)
            f.create_group("data/components")

            # Add external signals
            external_signals_group = f.create_group("data/external_signals")
            external_signals_group["external_signals.wind_speed"] = np.array([8.5, 9.0, 8.8])
            external_signals_group["external_signals.temperature"] = np.array([20.0, 21.0, 20.5])

        # Read the file
        from hercules.utilities import read_hercules_hdf5

        result = read_hercules_hdf5(temp_file)

        # Verify external signals are present
        assert "external_signals.wind_speed" in result.columns
        assert "external_signals.temperature" in result.columns

        # Verify values are correct
        np.testing.assert_array_equal(result["external_signals.wind_speed"], [8.5, 9.0, 8.8])
        np.testing.assert_array_equal(result["external_signals.temperature"], [20.0, 21.0, 20.5])

    finally:
        os.unlink(temp_file)


def test_local_time_to_utc_with_timezone():
    """Test local_time_to_utc with explicit timezone.

    Tests conversion of local time to UTC with daylight saving time handling.
    """
    # Midnight Jan 1, 2025 in Mountain Time (MST, UTC-7, no DST)
    result_jan = local_time_to_utc("2025-01-01T00:00:00", tz="America/Denver")
    assert result_jan == "2025-01-01T07:00:00Z"

    # Midnight July 1, 2025 in Mountain Time (MDT, UTC-6, DST)
    result_july = local_time_to_utc("2025-07-01T00:00:00", tz="America/Denver")
    assert result_july == "2025-07-01T06:00:00Z"

    # Test with different timezone (Eastern Time)
    # Midnight Jan 1, 2025 in Eastern Time (EST, UTC-5, no DST)
    result_eastern_jan = local_time_to_utc("2025-01-01T00:00:00", tz="America/New_York")
    assert result_eastern_jan == "2025-01-01T05:00:00Z"

    # Midnight July 1, 2025 in Eastern Time (EDT, UTC-4, DST)
    result_eastern_july = local_time_to_utc("2025-07-01T00:00:00", tz="America/New_York")
    assert result_eastern_july == "2025-07-01T04:00:00Z"


def test_local_time_to_utc_with_pandas_timestamp():
    """Test local_time_to_utc with pandas Timestamp input."""
    dt = pd.Timestamp("2025-01-01T00:00:00")
    result = local_time_to_utc(dt, tz="America/Denver")
    assert result == "2025-01-01T07:00:00Z"


def test_local_time_to_utc_with_different_formats():
    """Test local_time_to_utc with different datetime string formats."""
    # ISO format with T
    result1 = local_time_to_utc("2025-01-01T00:00:00", tz="America/Denver")
    assert result1 == "2025-01-01T07:00:00Z"

    # ISO format with space
    result2 = local_time_to_utc("2025-01-01 00:00:00", tz="America/Denver")
    assert result2 == "2025-01-01T07:00:00Z"

    # Date only (defaults to midnight)
    result3 = local_time_to_utc("2025-01-01", tz="America/Denver")
    assert result3 == "2025-01-01T07:00:00Z"


def test_local_time_to_utc_invalid_timezone():
    """Test local_time_to_utc with invalid timezone raises error."""
    with pytest.raises(ValueError, match="Invalid timezone"):
        local_time_to_utc("2025-01-01T00:00:00", tz="Invalid/Timezone")


def test_local_time_to_utc_invalid_datetime():
    """Test local_time_to_utc with invalid datetime string raises error."""
    with pytest.raises(ValueError, match="Cannot parse local_time"):
        local_time_to_utc("invalid-datetime", tz="America/Denver")


def test_local_time_to_utc_missing_timezone():
    """Test local_time_to_utc with missing timezone parameter raises error."""
    with pytest.raises(ValueError, match="Timezone parameter 'tz' is required"):
        local_time_to_utc("2025-01-01T00:00:00", tz=None)


def test_local_time_to_utc_returns_z_suffix():
    """Test that local_time_to_utc returns string with Z suffix."""
    result = local_time_to_utc("2025-01-01T00:00:00", tz="America/Denver")
    assert result.endswith("Z")
    assert "T" in result
    assert len(result) == 20  # Format: YYYY-MM-DDTHH:MM:SSZ


# def test_read_hercules_hdf5_subset():
#     """Test reading subset of HDF5 file data.

#     Creates a mock HDF5 file and verifies that the subset function
#     correctly filters by columns and time range.
#     """
#     import h5py

#     with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
#         temp_file = f.name

#     try:
#         # Create mock HDF5 file with more data
#         with h5py.File(temp_file, "w") as f:
#             f.create_group("data")
#             f.create_group("metadata")

#             # Add time data (0, 1, 2, 3, 4, 5 seconds)
#             f["data/time"] = np.array([0, 1, 2, 3, 4, 5])
#             f["data/step"] = np.array([0, 1, 2, 3, 4, 5])
#             f["data/clock_time"] = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])

#             # Add plant data
#             f["data/plant_power"] = np.array([100, 200, 300, 400, 500, 600])
#             f["data/plant_locally_generated_power"] = np.array([90, 180, 270, 360, 450, 540])

#             # Add components group
#             components_group = f.create_group("data/components")
#             components_group["wind_farm.power"] = np.array([50, 100, 150, 200, 250, 300])
#             components_group["solar_farm.power"] = np.array([40, 80, 120, 160, 200, 240])

#             # Add external signals
#             external_signals_group = f.create_group("data/external_signals")
#             external_signals_group["external_signals.wind_speed"] = np.array(
#                 [8.5, 9.0, 8.8, 9.2, 8.9, 9.1]
#             )
#             external_signals_group["external_signals.temperature"] = np.array(
#                 [20.0, 21.0, 20.5, 22.0, 21.5, 22.5]
#             )

#         # Test column filtering
#         from hercules.utilities import read_hercules_hdf5_subset

#         result_columns = read_hercules_hdf5_subset(
#             temp_file, columns=["wind_farm.power", "external_signals.wind_speed"]
#         )

#         # Verify only requested columns plus time are present
#         expected_columns = {
#             "time",
#             "wind_farm.power",
#             "external_signals.wind_speed",
#         }
#         assert set(result_columns.columns) == expected_columns

#         # Test time range filtering
#         result_time = read_hercules_hdf5_subset(temp_file, time_range=(1.5, 4.5))

#         # Verify time range is correct (should include times 2, 3, 4)
#         assert len(result_time) == 3
#         np.testing.assert_array_equal(result_time["time"], [2, 3, 4])

#         # Test both filters together
#         result_both = read_hercules_hdf5_subset(
#             temp_file, columns=["solar_farm.power"], time_range=(1.0, 3.0)
#         )

#         # Verify both filters work together
#         assert len(result_both) == 3  # times 1, 2, 3 (inclusive of end time)
#         assert "solar_farm.power" in result_both.columns
#         assert "wind_farm.power" not in result_both.columns
#         assert set(result_both.columns) == {"time", "solar_farm.power"}

#         # Test stride parameter
#         result_stride = read_hercules_hdf5_subset(temp_file, stride=2)

#         # Verify stride works (should read every 2nd point: 0, 2, 4)
#         assert len(result_stride) == 3
#         np.testing.assert_array_equal(result_stride["time"], [0, 2, 4])

#         # Test stride with time range
#         result_stride_time = read_hercules_hdf5_subset(temp_file, time_range=(1.0, 4.0), stride=2)

#         # Should get times 1, 3 (within range, every 2nd point starting from first in range)
#         assert len(result_stride_time) == 2
#         np.testing.assert_array_equal(result_stride_time["time"], [1, 3])

#         # Test with no columns specified (should return only time)
#         result_time_only = read_hercules_hdf5_subset(temp_file)
#         assert set(result_time_only.columns) == {"time"}
#         assert len(result_time_only) == 6  # All time points

#     finally:
#         os.unlink(temp_file)
