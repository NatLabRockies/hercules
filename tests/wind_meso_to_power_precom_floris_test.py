"""Tests for the Wind_MesoToPowerPrecomFloris class."""

import copy
import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from hercules.plant_components.wind_meso_to_power_precom_floris import (
    Wind_MesoToPowerPrecomFloris,
)
from hercules.utilities import hercules_float_type

from tests.test_inputs.h_dict import h_dict_wind

# Create a base test dictionary for Wind_MesoToPowerPrecomFloris
h_dict_wind_precom_floris = copy.deepcopy(h_dict_wind)
# Update component type and add logging_option for precom_floris tests
h_dict_wind_precom_floris["wind_farm"]["component_type"] = "Wind_MesoToPowerPrecomFloris"
h_dict_wind_precom_floris["wind_farm"]["logging_option"] = "all"


def test_wind_meso_to_power_precom_floris_initialization():
    """Test that Wind_MesoToPowerPrecomFloris initializes correctly with valid inputs."""
    wind_sim = Wind_MesoToPowerPrecomFloris(h_dict_wind_precom_floris)

    assert wind_sim.component_name == "wind_farm"
    assert wind_sim.component_type == "Wind_MesoToPowerPrecomFloris"
    assert wind_sim.n_turbines == 3
    assert wind_sim.dt == 1.0
    assert wind_sim.starttime == 0.0
    assert wind_sim.endtime == 10.0
    # FLORIS is called during initialization for precomputed version
    assert wind_sim.num_floris_calcs == 1
    assert (
        wind_sim.floris_update_time_s
        == h_dict_wind_precom_floris["wind_farm"]["floris_update_time_s"]
    )

def test_wind_meso_to_power_precom_floris_ws_mean():
    """Test that invalid component_type raises ValueError."""

    current_dir = os.path.dirname(__file__)

    df_input = pd.read_csv(current_dir+"/test_inputs/wind_input.csv")
    df_input["ws_mean"] = 10.0
    df_input.to_csv(current_dir+"/test_inputs/wind_input_temp.csv")

    test_h_dict = copy.deepcopy(h_dict_wind_precom_floris)
    test_h_dict["wind_farm"]["wind_input_filename"] = "tests/test_inputs/wind_input_temp.csv"

    # Test that, since individual speed are specified, ws_mean is ignored
    # Note that h_dict_wind_precom_floris specifies an end time of 10.
    wind_sim = Wind_MesoToPowerPrecomFloris(test_h_dict)
    assert (
        wind_sim.ws_mat[:, 0]
        == df_input["ws_000"].to_numpy(dtype=hercules_float_type)[:10]
    ).all()
    assert np.allclose(
        wind_sim.ws_mat_mean,
        (df_input[["ws_000", "ws_001", "ws_002"]].mean(axis=1)).to_numpy(
            dtype=hercules_float_type
        )[:10]
    )

    # Drop individual speeds and test that ws_mean is used instead
    df_input = df_input.drop(columns=["ws_000", "ws_001", "ws_002"])
    df_input.to_csv(current_dir+"/test_inputs/wind_input_temp.csv")

    wind_sim = Wind_MesoToPowerPrecomFloris(test_h_dict)
    assert (wind_sim.ws_mat_mean == 10.0).all()
    assert (wind_sim.ws_mat[:, :] == 10.0).all()

    # Delete temp file
    os.remove(current_dir+"/test_inputs/wind_input_temp.csv")

def test_wind_meso_to_power_precom_floris_requires_floris_update_time():
    """Test that missing floris_update_time_s raises ValueError."""
    test_h_dict = copy.deepcopy(h_dict_wind_precom_floris)
    del test_h_dict["wind_farm"]["floris_update_time_s"]

    with pytest.raises(ValueError, match="floris_update_time_s must be in the h_dict"):
        Wind_MesoToPowerPrecomFloris(test_h_dict)


def test_wind_meso_to_power_precom_floris_invalid_update_time():
    """Test that invalid floris_update_time_s (<1) raises ValueError."""
    test_h_dict = copy.deepcopy(h_dict_wind_precom_floris)
    test_h_dict["wind_farm"]["floris_update_time_s"] = 0.5

    with pytest.raises(ValueError, match="FLORIS update time must be at least 1 second"):
        Wind_MesoToPowerPrecomFloris(test_h_dict)


def test_wind_meso_to_power_precom_floris_step():
    """Test that the step method updates outputs correctly."""
    wind_sim = Wind_MesoToPowerPrecomFloris(h_dict_wind_precom_floris)

    # Add power setpoint values to the step h_dict
    step_h_dict = {"step": 1}
    step_h_dict["wind_farm"] = {
        "turbine_power_setpoints": np.array([1000.0, 1500.0, 2000.0]),
    }

    result = wind_sim.step(step_h_dict)

    assert "turbine_powers" in result["wind_farm"]
    assert "power" in result["wind_farm"]
    assert len(result["wind_farm"]["turbine_powers"]) == 3
    assert isinstance(result["wind_farm"]["turbine_powers"], np.ndarray)
    assert "power" in result["wind_farm"]
    assert isinstance(result["wind_farm"]["power"], (int, float))


def test_wind_meso_to_power_precom_floris_power_setpoint_applies():
    """Test that turbine powers equal power setpoint when setpoint is very low."""
    wind_sim = Wind_MesoToPowerPrecomFloris(h_dict_wind_precom_floris)

    # Set very low power setpoint values that should definitely limit power output
    step_h_dict = {"step": 1}
    step_h_dict["wind_farm"] = {
        "turbine_power_setpoints": np.array([100.0, 200.0, 300.0]),  # Very low setpoints
    }

    result = wind_sim.step(step_h_dict)

    # Verify that turbine powers equal the power setpoint limits
    turbine_powers = result["wind_farm"]["turbine_powers"]
    power_setpoint_values = [100.0, 200.0, 300.0]

    for i, (power, setpoint) in enumerate(zip(turbine_powers, power_setpoint_values)):
        assert (
            power == setpoint
        ), f"Turbine {i} power {power} should equal power setpoint {setpoint}"


def test_wind_meso_to_power_precom_floris_get_initial_conditions_and_meta_data():
    """Test that get_initial_conditions_and_meta_data adds correct metadata to h_dict."""
    wind_sim = Wind_MesoToPowerPrecomFloris(h_dict_wind_precom_floris)

    # Create a copy of the input h_dict to avoid modifying the original
    test_h_dict_copy = copy.deepcopy(h_dict_wind_precom_floris)

    # Call the method
    result = wind_sim.get_initial_conditions_and_meta_data(test_h_dict_copy)

    # Verify that the method returns the modified h_dict
    assert result is test_h_dict_copy

    # Verify that all expected metadata is added to the wind_farm section
    assert "n_turbines" in result["wind_farm"]
    assert "capacity" in result["wind_farm"]
    assert "rated_turbine_power" in result["wind_farm"]
    assert "wind_direction" in result["wind_farm"]
    assert "wind_speed" in result["wind_farm"]
    assert "turbine_powers" in result["wind_farm"]

    # Verify the values match the wind_sim attributes
    assert result["wind_farm"]["n_turbines"] == wind_sim.n_turbines
    assert result["wind_farm"]["capacity"] == wind_sim.capacity
    assert result["wind_farm"]["rated_turbine_power"] == wind_sim.rated_turbine_power
    assert result["wind_farm"]["wind_direction"] == wind_sim.wd_mat_mean[0]
    assert result["wind_farm"]["wind_speed"] == wind_sim.ws_mat_mean[0]

    # Verify turbine_powers is a numpy array with correct length
    assert isinstance(result["wind_farm"]["turbine_powers"], np.ndarray)
    assert len(result["wind_farm"]["turbine_powers"]) == wind_sim.n_turbines
    np.testing.assert_array_equal(result["wind_farm"]["turbine_powers"], wind_sim.turbine_powers)

    # Verify that the original h_dict structure is preserved
    assert "dt" in result
    assert "starttime" in result
    assert "endtime" in result
    assert "plant" in result


def test_wind_meso_to_power_precom_floris_precomputed_wake_deficits():
    """Test that wake deficits are precomputed and stored correctly."""
    wind_sim = Wind_MesoToPowerPrecomFloris(h_dict_wind_precom_floris)

    # Verify that precomputed wake velocities exist
    assert hasattr(wind_sim, "waked_velocities_all")
    assert isinstance(wind_sim.waked_velocities_all, np.ndarray)

    # Check shape: should be (n_time_steps, n_turbines)
    expected_shape = (wind_sim.n_steps, wind_sim.n_turbines)
    assert wind_sim.waked_velocities_all.shape == expected_shape

    # Verify that initial wake deficits are calculated
    assert hasattr(wind_sim, "floris_wake_deficits")
    assert isinstance(wind_sim.floris_wake_deficits, np.ndarray)
    assert len(wind_sim.floris_wake_deficits) == wind_sim.n_turbines

    # Wake deficits should be non-negative (upwind turbines should have zero deficit)
    assert np.all(wind_sim.floris_wake_deficits >= 0.0)


def test_wind_meso_to_power_precom_floris_velocities_update_correctly():
    """Test that velocities are updated correctly from precomputed arrays during simulation."""
    # Create a temporary wind input file with varying conditions
    wind_data = {
        "time": [0, 1, 2, 3],
        "wd_mean": [270.0, 275.0, 280.0, 285.0],  # Varying wind direction
        "ws_000": [8.0, 9.0, 10.0, 11.0],  # Varying wind speed turbine 0
        "ws_001": [8.5, 9.5, 10.5, 11.5],  # Varying wind speed turbine 1
        "ws_002": [9.0, 10.0, 11.0, 12.0],  # Varying wind speed turbine 2
    }

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df = pd.DataFrame(wind_data)
        df.to_csv(f.name, index=False)
        temp_wind_file = f.name

    try:
        # Create test h_dict with the temporary wind file
        test_h_dict = copy.deepcopy(h_dict_wind_precom_floris)
        test_h_dict["wind_farm"]["wind_input_filename"] = temp_wind_file
        test_h_dict["starttime"] = 0.0
        test_h_dict["endtime"] = 4.0
        test_h_dict["dt"] = 1.0

        # Initialize wind simulation
        wind_sim = Wind_MesoToPowerPrecomFloris(test_h_dict)

        # Store initial velocities
        initial_unwaked = wind_sim.unwaked_velocities.copy()
        initial_waked = wind_sim.waked_velocities.copy()

        # Run a step
        step_h_dict = {"step": 1}
        step_h_dict["wind_farm"] = {
            "turbine_power_setpoints": np.array([5000.0, 5000.0, 5000.0]),
        }

        wind_sim.step(step_h_dict)

        # Verify that velocities have been updated
        assert not np.array_equal(
            wind_sim.unwaked_velocities, initial_unwaked
        ), "Unwaked velocities should have been updated"
        assert not np.array_equal(
            wind_sim.waked_velocities, initial_waked
        ), "Waked velocities should have been updated"

        # Verify the velocities match the expected values from the input data
        expected_unwaked = np.array([9.0, 9.5, 10.0])  # ws values for step 1
        np.testing.assert_array_equal(wind_sim.unwaked_velocities, expected_unwaked)

        # Verify that wake deficits are recalculated
        expected_wake_deficits = wind_sim.unwaked_velocities - wind_sim.waked_velocities
        np.testing.assert_array_equal(wind_sim.floris_wake_deficits, expected_wake_deficits)

    finally:
        # Clean up temporary file
        if os.path.exists(temp_wind_file):
            os.unlink(temp_wind_file)


def test_wind_meso_to_power_precom_floris_time_utc_reconstruction():
    """Test that time_utc reconstruction works correctly from zero_time_utc metadata
    and both time_utc fields are properly set."""
    # Create wind input data with time_utc columns
    wind_data = {
        "time": [0, 1, 2, 3],
        "time_utc": [
            "2023-01-01T00:00:00Z",
            "2023-01-01T00:00:01Z",
            "2023-01-01T00:00:02Z",
            "2023-01-01T00:00:03Z",
        ],
        "wd_mean": [270.0, 275.0, 280.0, 285.0],
        "ws_000": [8.0, 9.0, 10.0, 11.0],
        "ws_001": [8.5, 9.5, 10.5, 11.5],
        "ws_002": [9.0, 10.0, 11.0, 12.0],
    }

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df = pd.DataFrame(wind_data)
        df.to_csv(f.name, index=False)
        temp_wind_file = f.name

    try:
        # Create test h_dict with the temporary wind file
        test_h_dict = copy.deepcopy(h_dict_wind_precom_floris)
        test_h_dict["wind_farm"]["wind_input_filename"] = temp_wind_file
        test_h_dict["starttime"] = 0.0
        test_h_dict["endtime"] = 4.0
        test_h_dict["dt"] = 1.0

        # Initialize wind simulation
        wind_sim = Wind_MesoToPowerPrecomFloris(test_h_dict)

        # Verify that both zero_time_utc and start_time_utc are set correctly
        assert hasattr(wind_sim, "zero_time_utc"), "zero_time_utc should be set"
        assert hasattr(wind_sim, "start_time_utc"), "start_time_utc should be set"

        expected_zero_time = pd.to_datetime("2023-01-01T00:00:00Z", utc=True)
        expected_start_time = pd.to_datetime(
            "2023-01-01T00:00:00Z", utc=True
        )  # starttime=0, so same as zero_time

        # Convert numpy datetime64 to pandas Timestamp for comparison
        actual_zero_time = pd.Timestamp(wind_sim.zero_time_utc)
        actual_start_time = pd.Timestamp(wind_sim.start_time_utc)

        # Compare datetime values (ignoring timezone for this test)
        assert actual_zero_time.replace(tzinfo=None) == expected_zero_time.replace(
            tzinfo=None
        ), f"zero_time_utc mismatch: expected {expected_zero_time}, got {actual_zero_time}"
        assert actual_start_time.replace(tzinfo=None) == expected_start_time.replace(
            tzinfo=None
        ), f"start_time_utc mismatch: expected {expected_start_time}, got {actual_start_time}"

        # Test that both time_utc fields are added to h_dict when getting initial conditions
        result = wind_sim.get_initial_conditions_and_meta_data(test_h_dict)
        assert (
            "zero_time_utc" in result["wind_farm"]
        ), "zero_time_utc should be in wind_farm metadata"
        assert (
            "start_time_utc" in result["wind_farm"]
        ), "start_time_utc should be in wind_farm metadata"

        # Convert numpy datetime64 to pandas Timestamp for comparison
        actual_zero_time = pd.Timestamp(result["wind_farm"]["zero_time_utc"])
        actual_start_time = pd.Timestamp(result["wind_farm"]["start_time_utc"])

        # Compare datetime values (ignoring timezone for this test)
        assert actual_zero_time.replace(tzinfo=None) == expected_zero_time.replace(tzinfo=None), (
            f"zero_time_utc in metadata mismatch: expected {expected_zero_time}, "
            f"got {actual_zero_time}"
        )
        assert actual_start_time.replace(tzinfo=None) == expected_start_time.replace(tzinfo=None), (
            f"start_time_utc in metadata mismatch: expected {expected_start_time}, "
            f"got {actual_start_time}"
        )

        # Test time_utc reconstruction using utilities
        # Create a temporary HDF5 file to test reconstruction
        import h5py
        from hercules.utilities import read_hercules_hdf5

        with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
            temp_h5_file = f.name

        try:
            # Create a minimal HDF5 file with the structure needed for reconstruction
            with h5py.File(temp_h5_file, "w") as f:
                # Create metadata group
                metadata = f.create_group("metadata")
                metadata.attrs["zero_time_utc"] = expected_start_time.timestamp()

                # Create data group with time array
                data = f.create_group("data")
                time_data = np.array([0.0, 1.0, 2.0, 3.0])
                data.create_dataset("time", data=time_data)

                # Create step dataset
                step_data = np.array([0, 1, 2, 3], dtype=np.int32)
                data.create_dataset("step", data=step_data)

                # Create a minimal plant_power dataset
                plant_power = np.array([1000.0, 1100.0, 1200.0, 1300.0])
                data.create_dataset("plant_power", data=plant_power)

                # Create plant_locally_generated_power dataset
                plant_locally_generated_power = np.array([1000.0, 1100.0, 1200.0, 1300.0])
                data.create_dataset(
                    "plant_locally_generated_power", data=plant_locally_generated_power
                )

                # Create components group
                data.create_group("components")

            # Test reconstruction
            df = read_hercules_hdf5(temp_h5_file)

            # Verify that time_utc column is reconstructed
            assert "time_utc" in df.columns

            # Verify the reconstructed timestamps are correct
            expected_timestamps = [
                "2023-01-01 00:00:00+00:00",
                "2023-01-01 00:00:01+00:00",
                "2023-01-01 00:00:02+00:00",
                "2023-01-01 00:00:03+00:00",
            ]

            for i, expected in enumerate(expected_timestamps):
                actual = str(df["time_utc"].iloc[i])
                assert actual == expected, f"Timestamp {i}: expected {expected}, got {actual}"

        finally:
            # Clean up temporary HDF5 file
            if os.path.exists(temp_h5_file):
                os.unlink(temp_h5_file)

    finally:
        # Clean up temporary wind file
        if os.path.exists(temp_wind_file):
            os.unlink(temp_wind_file)


def test_wind_meso_to_power_precom_floris_time_utc_different_starttime():
    """Test that zero_time_utc and start_time_utc are correctly distinguished when
    starttime != 0."""
    # Create wind input data with time_utc columns
    wind_data = {
        "time": [0, 1, 2, 3, 4, 5],
        "time_utc": [
            "2023-01-01T00:00:00Z",
            "2023-01-01T00:00:01Z",
            "2023-01-01T00:00:02Z",
            "2023-01-01T00:00:03Z",
            "2023-01-01T00:00:04Z",
            "2023-01-01T00:00:05Z",
        ],
        "wd_mean": [270.0, 275.0, 280.0, 285.0, 290.0, 295.0],
        "ws_000": [8.0, 9.0, 10.0, 11.0, 12.0, 13.0],
        "ws_001": [8.5, 9.5, 10.5, 11.5, 12.5, 13.5],
        "ws_002": [9.0, 10.0, 11.0, 12.0, 13.0, 14.0],
    }

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df = pd.DataFrame(wind_data)
        df.to_csv(f.name, index=False)
        temp_wind_file = f.name

    try:
        # Create test h_dict with the temporary wind file
        test_h_dict = copy.deepcopy(h_dict_wind_precom_floris)
        test_h_dict["wind_farm"]["wind_input_filename"] = temp_wind_file
        test_h_dict["starttime"] = 2.0  # Start at time=2, not time=0
        test_h_dict["endtime"] = 6.0
        test_h_dict["dt"] = 1.0

        # Initialize wind simulation
        wind_sim = Wind_MesoToPowerPrecomFloris(test_h_dict)

        # Verify that both zero_time_utc and start_time_utc are set correctly
        assert hasattr(wind_sim, "zero_time_utc"), "zero_time_utc should be set"
        assert hasattr(wind_sim, "start_time_utc"), "start_time_utc should be set"

        expected_zero_time = pd.to_datetime("2023-01-01T00:00:00Z", utc=True)  # time=0
        expected_start_time = pd.to_datetime("2023-01-01T00:00:02Z", utc=True)  # time=2 (starttime)

        # Convert numpy datetime64 to pandas Timestamp for comparison
        actual_zero_time = pd.Timestamp(wind_sim.zero_time_utc)
        actual_start_time = pd.Timestamp(wind_sim.start_time_utc)

        # Compare datetime values (ignoring timezone for this test)
        assert actual_zero_time.replace(tzinfo=None) == expected_zero_time.replace(
            tzinfo=None
        ), f"zero_time_utc mismatch: expected {expected_zero_time}, got {actual_zero_time}"
        assert actual_start_time.replace(tzinfo=None) == expected_start_time.replace(
            tzinfo=None
        ), f"start_time_utc mismatch: expected {expected_start_time}, got {actual_start_time}"

        # Test that both time_utc fields are added to h_dict when getting initial conditions
        result = wind_sim.get_initial_conditions_and_meta_data(test_h_dict)
        assert (
            "zero_time_utc" in result["wind_farm"]
        ), "zero_time_utc should be in wind_farm metadata"
        assert (
            "start_time_utc" in result["wind_farm"]
        ), "start_time_utc should be in wind_farm metadata"

        # Convert numpy datetime64 to pandas Timestamp for comparison
        actual_zero_time = pd.Timestamp(result["wind_farm"]["zero_time_utc"])
        actual_start_time = pd.Timestamp(result["wind_farm"]["start_time_utc"])

        # Compare datetime values (ignoring timezone for this test)
        assert actual_zero_time.replace(tzinfo=None) == expected_zero_time.replace(tzinfo=None), (
            f"zero_time_utc in metadata mismatch: expected {expected_zero_time}, "
            f"got {actual_zero_time}"
        )
        assert actual_start_time.replace(tzinfo=None) == expected_start_time.replace(tzinfo=None), (
            f"start_time_utc in metadata mismatch: expected {expected_start_time}, "
            f"got {actual_start_time}"
        )

    finally:
        # Clean up temporary wind file
        if os.path.exists(temp_wind_file):
            os.unlink(temp_wind_file)
