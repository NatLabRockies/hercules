import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from hercules.utilities import interpolate_df, load_h_dict_from_text, load_hercules_input


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
    assert result["wind_farm"]["component_type"] == "WindSimLongTerm"
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
    invalid_config = {"dt": 1.0, "starttime": 0.0, "endtime": 30.0, "plant": "not_a_dict"}

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
        "starttime": 0.0,
        "endtime": 30.0,
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
        "starttime": 0.0,
        "endtime": 30.0,
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
        "wind_farm": {"component_type": "WindSimLongTerm", "capacity": 100.0},
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
        assert result["wind_farm"]["component_type"] == "WindSimLongTerm"
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
