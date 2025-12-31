import numpy as np
import pandas as pd
from hercules.hercules_model import HerculesModel

from tests.test_inputs.h_dict import h_dict_battery, h_dict_solar, h_dict_wind


class SimpleControllerWind:
    """A simple controller for testing that just returns the h_dict unchanged."""

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.
        """
        self.h_dict = h_dict

    def step(self, h_dict):
        """Execute one control step.

        Args:
            h_dict (dict): The hercules input dictionary.

        Returns:
            dict: The updated hercules input dictionary.
        """
        # Set power setpoints for wind turbines if wind farm is present
        if "wind_farm" in h_dict and "n_turbines" in h_dict["wind_farm"]:
            h_dict["wind_farm"]["turbine_power_setpoints"] = 5000 * np.ones(
                h_dict["wind_farm"]["n_turbines"]
            )

        # Set power setpoints for battery if present
        if "battery" in h_dict:
            h_dict["battery"]["power_setpoint"] = 0.0

        return h_dict


class SimpleControllerSolar:
    """A simple controller for testing that just returns the h_dict unchanged."""

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.
        """
        self.h_dict = h_dict

    def step(self, h_dict):
        """Execute one control step.

        Args:
            h_dict (dict): The hercules input dictionary.

        Returns:
            dict: The updated hercules input dictionary.
        """

        # Set solar derating to very high to have no impact
        h_dict["solar_farm"]["power_setpoint"] = 1e10

        return h_dict


def test_HerculesModel_instantiation():
    """Test that the HerculesModel can be instantiated with different configurations."""

    # Use h_dict_solar as base for testing
    test_h_dict = h_dict_solar.copy()
    # Enforce new loader policy: remove preset start/end and rely on *_utc
    test_h_dict.pop("starttime", None)
    test_h_dict.pop("endtime", None)
    test_h_dict.pop("time", None)
    test_h_dict.pop("step", None)

    hmodel = HerculesModel(test_h_dict)

    # Check default settings
    assert hmodel.output_file == "outputs/hercules_output.h5"
    assert hmodel.log_every_n == 1
    assert hmodel.external_signals_all == {}

    # Test with external data file and custom output file
    test_h_dict_2 = h_dict_solar.copy()
    test_h_dict_2["external_data_file"] = "tests/test_inputs/external_data.csv"
    test_h_dict_2["output_file"] = "test_output.h5"
    test_h_dict_2["dt"] = 0.5
    # Remove preset start/end and adjust endtime_utc to preserve prior behavior
    test_h_dict_2.pop("starttime", None)
    test_h_dict_2.pop("endtime", None)
    test_h_dict_2.pop("time", None)
    test_h_dict_2.pop("step", None)
    # To achieve endtime = 5.0 and endtime + 2*dt = 6.0, set duration = 4.5s
    test_h_dict_2["endtime_utc"] = test_h_dict_2["starttime_utc"] + pd.to_timedelta(4.5, unit="s")

    hmodel = HerculesModel(test_h_dict_2)

    # Check external data loading
    assert hmodel.external_signals_all["power_reference"][0] == 1000
    # With dt=0.5 and endtime=5.0, we have times: 0.0, 0.5, 1.0, ..., 5.5, 6.0
    # At time 1.0: value is 2000 (from data), but at index 2 (time=1.0), value is interpolated
    # Actually external_signals_all has times from starttime to endtime + 2*dt with step dt
    # So times are: 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0
    assert hmodel.external_signals_all["power_reference"][-1] == 1000  # At time 6.0

    # Check custom output file
    assert hmodel.output_file == "test_output.h5"


def test_log_data_to_hdf5():
    """Test that the new HDF5 logging function works correctly."""

    # Use h_dict_solar as base for testing
    test_h_dict = h_dict_solar.copy()
    test_h_dict.pop("starttime", None)
    test_h_dict.pop("endtime", None)
    test_h_dict.pop("time", None)
    test_h_dict.pop("step", None)

    hmodel = HerculesModel(test_h_dict)
    hmodel.assign_controller(SimpleControllerSolar(test_h_dict))

    # Set up the simulation state
    hmodel.time = 5.0
    hmodel.step = 5
    hmodel.h_dict["time"] = 5.0
    hmodel.h_dict["step"] = 5

    # Run controller and hybrid_plant steps to generate plant-level outputs
    hmodel.h_dict = hmodel.controller.step(hmodel.h_dict)
    hmodel.h_dict = hmodel.hybrid_plant.step(hmodel.h_dict)

    # Call the new HDF5 logging function
    hmodel._log_data_to_hdf5()

    # Check that HDF5 file was initialized
    assert hmodel.output_structure_determined
    assert hmodel.hdf5_file is not None
    assert len(hmodel.hdf5_datasets) > 0

    # Check that expected datasets exist
    expected_datasets = {
        "time",
        "step",
        "plant_power",
        "plant_locally_generated_power",
        "solar_farm.power",
    }

    actual_datasets = set(hmodel.hdf5_datasets.keys())
    missing_datasets = expected_datasets - actual_datasets
    assert expected_datasets.issubset(actual_datasets), (
        f"Missing expected datasets: {missing_datasets}"
    )

    # Flush buffer to write data to HDF5
    if hasattr(hmodel, "data_buffers") and hmodel.data_buffers and hmodel.buffer_row > 0:
        hmodel._flush_buffer_to_hdf5()

    # Check that data was written correctly
    assert hmodel.hdf5_datasets["time"][0] == 5.0
    assert hmodel.hdf5_datasets["step"][0] == 5
    assert hmodel.hdf5_datasets["plant_power"][0] > 0
    assert hmodel.hdf5_datasets["solar_farm.power"][0] > 0

    # Clean up
    hmodel.close()


def test_log_data_to_hdf5_with_external_signals():
    """Test that external signals are logged correctly to HDF5."""

    # Use h_dict_battery as base for testing (no external data requirements)
    test_h_dict = h_dict_battery.copy()
    test_h_dict.pop("starttime", None)
    test_h_dict.pop("endtime", None)
    test_h_dict.pop("time", None)
    test_h_dict.pop("step", None)

    # Add external data file
    test_h_dict["external_data_file"] = "tests/test_inputs/external_data.csv"
    test_h_dict["dt"] = 1.0

    hmodel = HerculesModel(test_h_dict)
    hmodel.assign_controller(SimpleControllerWind(test_h_dict))

    # Set up the simulation state
    hmodel.time = 5.0
    hmodel.step = 5
    hmodel.h_dict["time"] = 5.0
    hmodel.h_dict["step"] = 5

    # Update external signals (simulate what happens in the run loop)
    if hmodel.external_signals_all:
        for k in hmodel.external_signals_all:
            if k == "time":
                continue
            hmodel.h_dict["external_signals"][k] = hmodel.external_signals_all[k][hmodel.step]

    # Run controller and hybrid_plant steps to generate plant-level outputs
    hmodel.h_dict = hmodel.controller.step(hmodel.h_dict)
    hmodel.h_dict = hmodel.hybrid_plant.step(hmodel.h_dict)

    # Call the new HDF5 logging function
    hmodel._log_data_to_hdf5()

    # Check that HDF5 file was initialized
    assert hmodel.output_structure_determined
    assert hmodel.hdf5_file is not None
    assert len(hmodel.hdf5_datasets) > 0

    # Check that external signals dataset exists
    expected_external_dataset = "external_signals.power_reference"
    assert expected_external_dataset in hmodel.hdf5_datasets

    # Flush buffer to write data to HDF5
    if hasattr(hmodel, "data_buffers") and hmodel.data_buffers and hmodel.buffer_row > 0:
        hmodel._flush_buffer_to_hdf5()

    # Check that external signal data was written correctly
    expected_value = hmodel.external_signals_all["power_reference"][5]  # Value at step 5
    assert hmodel.hdf5_datasets[expected_external_dataset][0] == expected_value

    # Clean up
    hmodel.close()


def test_log_data_to_hdf5_with_wind_farm_arrays():
    """Test that the new HDF5 logging function handles wind farm array outputs correctly."""

    # Use h_dict_wind as base for testing
    test_h_dict = h_dict_wind.copy()
    test_h_dict.pop("starttime", None)
    test_h_dict.pop("endtime", None)
    test_h_dict.pop("time", None)
    test_h_dict.pop("step", None)

    hmodel = HerculesModel(test_h_dict)
    hmodel.assign_controller(SimpleControllerWind(test_h_dict))

    # Set up the simulation state
    hmodel.time = 5.0
    hmodel.step = 5
    hmodel.h_dict["time"] = 5.0
    hmodel.h_dict["step"] = 5

    # Run controller and hybrid_plant steps to generate plant-level outputs
    hmodel.h_dict = hmodel.controller.step(hmodel.h_dict)
    hmodel.h_dict = hmodel.hybrid_plant.step(hmodel.h_dict)

    # Call the new HDF5 logging function
    hmodel._log_data_to_hdf5()

    # Check that array outputs are handled correctly
    expected_datasets = {
        "time",
        "step",
        "plant_power",
        "plant_locally_generated_power",
        "wind_farm.power",
        "wind_farm.turbine_powers.000",
        "wind_farm.turbine_powers.001",
        "wind_farm.turbine_powers.002",
    }

    actual_datasets = set(hmodel.hdf5_datasets.keys())

    # Verify that all expected datasets are present
    missing_datasets = expected_datasets - actual_datasets
    assert expected_datasets.issubset(actual_datasets), (
        f"Missing expected datasets: {missing_datasets}"
    )

    # Flush buffer to write data to HDF5
    if hasattr(hmodel, "data_buffers") and hmodel.data_buffers and hmodel.buffer_row > 0:
        hmodel._flush_buffer_to_hdf5()

    # Check that data was written correctly
    assert hmodel.hdf5_datasets["time"][0] == 5.0
    assert hmodel.hdf5_datasets["step"][0] == 5
    assert hmodel.hdf5_datasets["wind_farm.power"][0] > 0
    assert hmodel.hdf5_datasets["plant_power"][0] > 0
    assert hmodel.hdf5_datasets["plant_locally_generated_power"][0] > 0

    # Verify that turbine_powers array is handled correctly
    assert hmodel.hdf5_datasets["wind_farm.turbine_powers.000"][0] > 0
    assert hmodel.hdf5_datasets["wind_farm.turbine_powers.001"][0] > 0
    assert hmodel.hdf5_datasets["wind_farm.turbine_powers.002"][0] > 0

    # Clean up
    hmodel.close()


def test_hdf5_output_configuration():
    """Test HDF5 output configuration options: downsampling and chunking."""
    import os
    import tempfile

    from hercules.utilities import read_hercules_hdf5

    # Use h_dict_solar as base for testing
    test_h_dict = h_dict_solar.copy()

    # Test 1: HDF5 format with downsampling
    with tempfile.TemporaryDirectory() as temp_dir:
        test_h_dict_hdf5 = test_h_dict.copy()
        test_h_dict_hdf5["output_file"] = os.path.join(temp_dir, "test_output.h5")
        test_h_dict_hdf5["dt"] = 1.0
        # Remove preset start/end and set endtime_utc for 5 steps (duration=4s)
        test_h_dict_hdf5.pop("starttime", None)
        test_h_dict_hdf5.pop("endtime", None)
        test_h_dict_hdf5.pop("time", None)
        test_h_dict_hdf5.pop("step", None)
        test_h_dict_hdf5["endtime_utc"] = test_h_dict_hdf5["starttime_utc"] + pd.to_timedelta(
            4.0, unit="s"
        )

        hmodel = HerculesModel(test_h_dict_hdf5)
        hmodel.assign_controller(SimpleControllerSolar(test_h_dict_hdf5))

        # Run simulation and write output
        for step in range(5):  # 5 steps (0-4) for dt=1.0, endtime=5.0, starttime=0.0
            hmodel.step = step
            hmodel.time = step * hmodel.dt
            hmodel.h_dict["time"] = hmodel.time
            hmodel.h_dict["step"] = step
            hmodel.h_dict = hmodel.controller.step(hmodel.h_dict)
            hmodel.h_dict = hmodel.hybrid_plant.step(hmodel.h_dict)
            hmodel._log_data_to_hdf5()

        hmodel.close()

        # Verify file exists and is readable
        assert os.path.exists(hmodel.output_file)
        df_hdf5 = read_hercules_hdf5(hmodel.output_file)
        # 5 steps with default log_every_n=1 should give 5 rows
        assert len(df_hdf5) == 5
        assert df_hdf5["time"].iloc[0] == 0.0
        assert df_hdf5["time"].iloc[1] == 1.0
        assert df_hdf5["time"].iloc[2] == 2.0
        assert df_hdf5["time"].iloc[3] == 3.0
        assert df_hdf5["time"].iloc[4] == 4.0

    # Test 2: HDF5 format with custom chunk size
    with tempfile.TemporaryDirectory() as temp_dir:
        test_h_dict_hdf5_2 = test_h_dict.copy()
        test_h_dict_hdf5_2["output_file"] = os.path.join(temp_dir, "test_output.h5")
        test_h_dict_hdf5_2["output_buffer_size"] = 500  # Custom chunk size
        test_h_dict_hdf5_2["dt"] = 1.0
        test_h_dict_hdf5_2.pop("starttime", None)
        test_h_dict_hdf5_2.pop("endtime", None)
        test_h_dict_hdf5_2.pop("time", None)
        test_h_dict_hdf5_2.pop("step", None)
        test_h_dict_hdf5_2["endtime_utc"] = test_h_dict_hdf5_2["starttime_utc"] + pd.to_timedelta(
            4.0, unit="s"
        )

        hmodel = HerculesModel(test_h_dict_hdf5_2)
        hmodel.assign_controller(SimpleControllerSolar(test_h_dict_hdf5_2))

        # Check configuration
        assert hmodel.buffer_size == 500

        # Run simulation and write output
        for step in range(5):  # 5 steps to match the array size
            hmodel.step = step
            hmodel.time = step * hmodel.dt
            hmodel.h_dict["time"] = hmodel.time
            hmodel.h_dict["step"] = step
            hmodel.h_dict = hmodel.controller.step(hmodel.h_dict)
            hmodel.h_dict = hmodel.hybrid_plant.step(hmodel.h_dict)
            hmodel._log_data_to_hdf5()

        hmodel.close()

        # Verify file exists and is readable
        assert os.path.exists(hmodel.output_file)
        df_hdf5 = read_hercules_hdf5(hmodel.output_file)
        assert len(df_hdf5) == 5


def test_log_every_n_option():
    """Test that the log_every_n option works correctly."""
    import os
    import tempfile

    from hercules.utilities import read_hercules_hdf5

    # Use h_dict_solar as base for testing
    test_h_dict = h_dict_solar.copy()

    # Test with log_every_n = 2
    with tempfile.TemporaryDirectory() as temp_dir:
        test_h_dict_log = test_h_dict.copy()
        test_h_dict_log["output_file"] = os.path.join(temp_dir, "test_output.h5")
        test_h_dict_log["log_every_n"] = 2  # Log every 2 steps
        test_h_dict_log["dt"] = 1.0
        test_h_dict_log.pop("starttime", None)
        test_h_dict_log.pop("endtime", None)
        test_h_dict_log.pop("time", None)
        test_h_dict_log.pop("step", None)
        # For 6 steps total, duration=5s
        test_h_dict_log["endtime_utc"] = test_h_dict_log["starttime_utc"] + pd.to_timedelta(
            5.0, unit="s"
        )

        hmodel = HerculesModel(test_h_dict_log)
        hmodel.assign_controller(SimpleControllerSolar(test_h_dict_log))

        # Check configuration
        assert hmodel.log_every_n == 2
        assert hmodel.dt_log == 2.0

        # Run simulation and write output
        for step in range(6):  # 6 steps (0-5) for dt=1.0, endtime=6.0, starttime=0.0
            hmodel.step = step
            hmodel.time = step * hmodel.dt
            hmodel.h_dict["time"] = hmodel.time
            hmodel.h_dict["step"] = step
            hmodel.h_dict = hmodel.controller.step(hmodel.h_dict)
            hmodel.h_dict = hmodel.hybrid_plant.step(hmodel.h_dict)
            hmodel._log_data_to_hdf5()

        hmodel.close()

        # Verify file exists and is readable
        assert os.path.exists(hmodel.output_file)
        df_hdf5 = read_hercules_hdf5(hmodel.output_file)
        # 6 steps with log_every_n=2 should give 3 rows (0, 2, 4)
        assert len(df_hdf5) == 3
        assert df_hdf5["time"].iloc[0] == 0.0
        assert df_hdf5["time"].iloc[1] == 2.0
        assert df_hdf5["time"].iloc[2] == 4.0
        assert df_hdf5["step"].iloc[0] == 0
        assert df_hdf5["step"].iloc[1] == 2
        assert df_hdf5["step"].iloc[2] == 4

    # Test with log_every_n = 3
    with tempfile.TemporaryDirectory() as temp_dir:
        test_h_dict_log2 = test_h_dict.copy()
        test_h_dict_log2["output_file"] = os.path.join(temp_dir, "test_output.h5")
        test_h_dict_log2["log_every_n"] = 3  # Log every 3 steps
        test_h_dict_log2["dt"] = 1.0
        test_h_dict_log2.pop("starttime", None)
        test_h_dict_log2.pop("endtime", None)
        test_h_dict_log2.pop("time", None)
        test_h_dict_log2.pop("step", None)
        # For 7 steps total, duration=6s
        test_h_dict_log2["endtime_utc"] = test_h_dict_log2["starttime_utc"] + pd.to_timedelta(
            6.0, unit="s"
        )

        hmodel = HerculesModel(test_h_dict_log2)
        hmodel.assign_controller(SimpleControllerSolar(test_h_dict_log2))

        # Check configuration
        assert hmodel.log_every_n == 3
        assert hmodel.dt_log == 3.0

        # Run simulation and write output
        for step in range(7):  # 7 steps (0-6)
            hmodel.step = step
            hmodel.time = step * hmodel.dt
            hmodel.h_dict["time"] = hmodel.time
            hmodel.h_dict["step"] = step
            hmodel.h_dict = hmodel.controller.step(hmodel.h_dict)
            hmodel.h_dict = hmodel.hybrid_plant.step(hmodel.h_dict)
            hmodel._log_data_to_hdf5()

        hmodel.close()

        # Verify file exists and is readable
        assert os.path.exists(hmodel.output_file)
        df_hdf5 = read_hercules_hdf5(hmodel.output_file)
        # 7 steps with log_every_n=3 should give 3 rows (0, 3, 6)
        assert len(df_hdf5) == 3
        assert df_hdf5["time"].iloc[0] == 0.0
        assert df_hdf5["time"].iloc[1] == 3.0
        assert df_hdf5["time"].iloc[2] == 6.0
        assert df_hdf5["step"].iloc[0] == 0
        assert df_hdf5["step"].iloc[1] == 3
        assert df_hdf5["step"].iloc[2] == 6


def test_log_selective_array_element():
    """Test that selective array element logging (e.g., turbine_powers.001) works correctly.

    This test verifies that when log_channels specifies a specific array element
    (e.g., turbine_powers.001), only that element is logged and not other elements.
    """
    import copy

    # Use h_dict_wind as base for testing
    test_h_dict = copy.deepcopy(h_dict_wind)
    test_h_dict.pop("starttime", None)
    test_h_dict.pop("endtime", None)
    test_h_dict.pop("time", None)
    test_h_dict.pop("step", None)

    # Modify log_channels to only include turbine_powers.001 (not the full array)
    test_h_dict["wind_farm"]["log_channels"] = ["power", "turbine_powers.001"]

    hmodel = HerculesModel(test_h_dict)
    hmodel.assign_controller(SimpleControllerWind(test_h_dict))

    # Set up the simulation state
    hmodel.time = 5.0
    hmodel.step = 5
    hmodel.h_dict["time"] = 5.0
    hmodel.h_dict["step"] = 5

    # Run controller and hybrid_plant steps to generate plant-level outputs
    hmodel.h_dict = hmodel.controller.step(hmodel.h_dict)
    hmodel.h_dict = hmodel.hybrid_plant.step(hmodel.h_dict)

    # Call the new HDF5 logging function
    hmodel._log_data_to_hdf5()

    # Check that ONLY turbine_powers.001 is logged (not .000 or .002)
    actual_datasets = set(hmodel.hdf5_datasets.keys())

    # turbine_powers.001 SHOULD be present
    assert "wind_farm.turbine_powers.001" in actual_datasets, (
        "Expected wind_farm.turbine_powers.001 to be logged"
    )

    # turbine_powers.000 should NOT be present
    assert "wind_farm.turbine_powers.000" not in actual_datasets, (
        "wind_farm.turbine_powers.000 should NOT be logged when only .001 is specified"
    )

    # turbine_powers.002 should NOT be present
    assert "wind_farm.turbine_powers.002" not in actual_datasets, (
        "wind_farm.turbine_powers.002 should NOT be logged when only .001 is specified"
    )

    # Verify that basic datasets are still present
    assert "time" in actual_datasets
    assert "step" in actual_datasets
    assert "wind_farm.power" in actual_datasets

    # Flush buffer to write data to HDF5
    if hasattr(hmodel, "data_buffers") and hmodel.data_buffers and hmodel.buffer_row > 0:
        hmodel._flush_buffer_to_hdf5()

    # Verify that turbine_powers.001 has a valid value
    assert hmodel.hdf5_datasets["wind_farm.turbine_powers.001"][0] > 0

    # Clean up
    hmodel.close()


def test_external_data_new_format_with_log_channels():
    """Test new external_data format with selective log_channels."""
    # Create test dict with new external_data format
    test_h_dict = h_dict_battery.copy()
    test_h_dict.pop("starttime", None)
    test_h_dict.pop("endtime", None)
    test_h_dict.pop("time", None)
    test_h_dict.pop("step", None)

    # Use new format with log_channels
    test_h_dict["external_data"] = {
        "external_data_file": "tests/test_inputs/external_data.csv",
        "log_channels": ["power_reference"],  # Only log one channel
    }
    test_h_dict["dt"] = 1.0

    hmodel = HerculesModel(test_h_dict)

    # Verify that external_data_log_channels was set
    assert hmodel.external_data_log_channels == ["power_reference"]

    # Verify that all external data was loaded into external_signals_all
    assert "power_reference" in hmodel.external_signals_all
    assert len(hmodel.external_signals_all["power_reference"]) > 0

    # Clean up
    hmodel.close()


def test_external_data_backward_compatibility():
    """Test backward compatibility with old external_data_file format."""
    import warnings

    # Create test dict with old format
    test_h_dict = h_dict_battery.copy()
    test_h_dict.pop("starttime", None)
    test_h_dict.pop("endtime", None)
    test_h_dict.pop("time", None)
    test_h_dict.pop("step", None)

    # Use old format (top-level external_data_file)
    test_h_dict["external_data_file"] = "tests/test_inputs/external_data.csv"
    test_h_dict["dt"] = 1.0

    # Should trigger a deprecation warning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        hmodel = HerculesModel(test_h_dict)

        # Verify that a deprecation warning was issued
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message).lower()

    # Verify that external_data_log_channels is None (log all)
    assert hmodel.external_data_log_channels is None

    # Verify that data was loaded
    assert "power_reference" in hmodel.external_signals_all

    # Clean up
    hmodel.close()


def test_external_signals_all_channels_in_h_dict():
    """Test that all external data channels are available in h_dict regardless of log_channels."""
    # Create a CSV with multiple channels
    import os

    import pandas as pd

    csv_path = "tests/test_inputs/multi_channel_external_data.csv"
    df = pd.DataFrame(
        {
            "time_utc": pd.date_range("2018-05-10 12:31:00", periods=10, freq="1s"),
            "channel_1": [1.0] * 10,
            "channel_2": [2.0] * 10,
            "channel_3": [3.0] * 10,
        }
    )
    df.to_csv(csv_path, index=False)

    try:
        # Create test dict with only channel_1 in log_channels
        test_h_dict = h_dict_battery.copy()
        test_h_dict.pop("starttime", None)
        test_h_dict.pop("endtime", None)
        test_h_dict.pop("time", None)
        test_h_dict.pop("step", None)

        test_h_dict["external_data"] = {
            "external_data_file": csv_path,
            "log_channels": ["channel_1"],  # Only log channel_1
        }
        test_h_dict["dt"] = 1.0

        hmodel = HerculesModel(test_h_dict)
        hmodel.assign_controller(SimpleControllerWind(test_h_dict))

        # Set up simulation state
        hmodel.time = 5.0
        hmodel.step = 5
        hmodel.h_dict["time"] = 5.0
        hmodel.h_dict["step"] = 5

        # Populate external signals (as done in run loop)
        if hmodel.external_signals_all:
            for k in hmodel.external_signals_all:
                if k == "time":
                    continue
                hmodel.h_dict["external_signals"][k] = hmodel.external_signals_all[k][hmodel.step]

        # Verify ALL channels are in h_dict["external_signals"]
        assert "channel_1" in hmodel.h_dict["external_signals"]
        assert "channel_2" in hmodel.h_dict["external_signals"]
        assert "channel_3" in hmodel.h_dict["external_signals"]

        # Run controller and hybrid_plant steps
        hmodel.h_dict = hmodel.controller.step(hmodel.h_dict)
        hmodel.h_dict = hmodel.hybrid_plant.step(hmodel.h_dict)

        # Log data to HDF5
        hmodel._log_data_to_hdf5()

        # Verify only channel_1 was logged to HDF5
        assert "external_signals.channel_1" in hmodel.hdf5_datasets
        assert "external_signals.channel_2" not in hmodel.hdf5_datasets
        assert "external_signals.channel_3" not in hmodel.hdf5_datasets

        # Clean up
        hmodel.close()
    finally:
        # Remove temporary CSV file
        if os.path.exists(csv_path):
            os.remove(csv_path)


def test_external_data_log_all_when_no_log_channels():
    """Test that all channels are logged when log_channels is not specified."""
    import os

    import pandas as pd

    csv_path = "tests/test_inputs/multi_channel_external_data_2.csv"
    df = pd.DataFrame(
        {
            "time_utc": pd.date_range("2018-05-10 12:31:00", periods=10, freq="1s"),
            "channel_a": [10.0] * 10,
            "channel_b": [20.0] * 10,
        }
    )
    df.to_csv(csv_path, index=False)

    try:
        # Create test dict without log_channels
        test_h_dict = h_dict_battery.copy()
        test_h_dict.pop("starttime", None)
        test_h_dict.pop("endtime", None)
        test_h_dict.pop("time", None)
        test_h_dict.pop("step", None)

        test_h_dict["external_data"] = {
            "external_data_file": csv_path,
            # No log_channels specified - should log all
        }
        test_h_dict["dt"] = 1.0

        hmodel = HerculesModel(test_h_dict)
        hmodel.assign_controller(SimpleControllerWind(test_h_dict))

        # Verify log_channels is None
        assert hmodel.external_data_log_channels is None

        # Set up simulation state
        hmodel.time = 5.0
        hmodel.step = 5
        hmodel.h_dict["time"] = 5.0
        hmodel.h_dict["step"] = 5

        # Populate external signals
        if hmodel.external_signals_all:
            for k in hmodel.external_signals_all:
                if k == "time":
                    continue
                hmodel.h_dict["external_signals"][k] = hmodel.external_signals_all[k][hmodel.step]

        # Run controller and hybrid_plant steps
        hmodel.h_dict = hmodel.controller.step(hmodel.h_dict)
        hmodel.h_dict = hmodel.hybrid_plant.step(hmodel.h_dict)

        # Log data to HDF5
        hmodel._log_data_to_hdf5()

        # Verify ALL channels were logged to HDF5
        assert "external_signals.channel_a" in hmodel.hdf5_datasets
        assert "external_signals.channel_b" in hmodel.hdf5_datasets

        # Clean up
        hmodel.close()
    finally:
        # Remove temporary CSV file
        if os.path.exists(csv_path):
            os.remove(csv_path)


def test_external_data_log_none_with_empty_list():
    """Test that no channels are logged when log_channels is an empty list."""
    import os

    import pandas as pd

    csv_path = "tests/test_inputs/multi_channel_external_data_3.csv"
    df = pd.DataFrame(
        {
            "time_utc": pd.date_range("2018-05-10 12:31:00", periods=10, freq="1s"),
            "channel_x": [100.0] * 10,
            "channel_y": [200.0] * 10,
        }
    )
    df.to_csv(csv_path, index=False)

    try:
        # Create test dict with empty log_channels list
        test_h_dict = h_dict_battery.copy()
        test_h_dict.pop("starttime", None)
        test_h_dict.pop("endtime", None)
        test_h_dict.pop("time", None)
        test_h_dict.pop("step", None)

        test_h_dict["external_data"] = {
            "external_data_file": csv_path,
            "log_channels": [],  # Empty list - should log nothing
        }
        test_h_dict["dt"] = 1.0

        hmodel = HerculesModel(test_h_dict)
        hmodel.assign_controller(SimpleControllerWind(test_h_dict))

        # Verify log_channels is an empty list
        assert hmodel.external_data_log_channels == []

        # Set up simulation state
        hmodel.time = 5.0
        hmodel.step = 5
        hmodel.h_dict["time"] = 5.0
        hmodel.h_dict["step"] = 5

        # Populate external signals (all channels should be available)
        if hmodel.external_signals_all:
            for k in hmodel.external_signals_all:
                if k == "time":
                    continue
                hmodel.h_dict["external_signals"][k] = hmodel.external_signals_all[k][hmodel.step]

        # Verify ALL channels are in h_dict["external_signals"] (available to controller)
        assert "channel_x" in hmodel.h_dict["external_signals"]
        assert "channel_y" in hmodel.h_dict["external_signals"]

        # Run controller and hybrid_plant steps
        hmodel.h_dict = hmodel.controller.step(hmodel.h_dict)
        hmodel.h_dict = hmodel.hybrid_plant.step(hmodel.h_dict)

        # Log data to HDF5
        hmodel._log_data_to_hdf5()

        # Verify NO external signal channels were logged to HDF5
        assert "external_signals.channel_x" not in hmodel.hdf5_datasets
        assert "external_signals.channel_y" not in hmodel.hdf5_datasets

        # Clean up
        hmodel.close()
    finally:
        # Remove temporary CSV file
        if os.path.exists(csv_path):
            os.remove(csv_path)
