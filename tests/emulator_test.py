import numpy as np
from hercules.emulator import Emulator
from hercules.hybrid_plant import HybridPlant
from hercules.utilities import setup_logging

from tests.test_inputs.h_dict import h_dict_battery, h_dict_solar, h_dict_wind


class SimpleControllerWind:
    """A simple controller for testing that just returns the h_dict unchanged."""

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.
        """
        pass

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
        pass

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


def test_Emulator_instantiation():
    """Test that the Emulator can be instantiated with different configurations."""

    # Use h_dict_solar as base for testing
    test_h_dict = h_dict_solar.copy()

    # Set up logger for testing
    logger = setup_logging(console_output=False)

    controller = SimpleControllerSolar(test_h_dict)
    hybrid_plant = HybridPlant(test_h_dict)

    emulator = Emulator(controller, hybrid_plant, test_h_dict, logger)

    # Check default settings
    assert emulator.output_file == "outputs/hercules_output.h5"
    assert emulator.log_every_n == 1
    assert emulator.external_data_all == {}

    # Test with external data file and custom output file
    test_h_dict_2 = test_h_dict.copy()
    test_h_dict_2["external_data_file"] = "tests/test_inputs/external_data.csv"
    test_h_dict_2["output_file"] = "test_output.h5"
    test_h_dict_2["dt"] = 0.5
    test_h_dict_2["starttime"] = 0.0
    test_h_dict_2["endtime"] = 10.0

    emulator = Emulator(controller, hybrid_plant, test_h_dict_2, logger)

    # Check external data loading
    assert emulator.external_data_all["power_reference"][0] == 1000
    assert emulator.external_data_all["power_reference"][1] == 1500
    assert emulator.external_data_all["power_reference"][2] == 2000
    assert emulator.external_data_all["power_reference"][-1] == 3000

    # Check custom output file
    assert emulator.output_file == "test_output.h5"


def test_log_data_to_hdf5():
    """Test that the new HDF5 logging function works correctly."""

    # Use h_dict_solar as base for testing
    test_h_dict = h_dict_solar.copy()

    # Set up logger for testing
    logger = setup_logging(console_output=False)

    controller = SimpleControllerSolar(test_h_dict)
    hybrid_plant = HybridPlant(test_h_dict)

    emulator = Emulator(controller, hybrid_plant, test_h_dict, logger)

    # Set up the simulation state
    emulator.time = 5.0
    emulator.step = 5
    emulator.h_dict["time"] = 5.0
    emulator.h_dict["step"] = 5

    # Run controller and hybrid_plant steps to generate plant-level outputs
    emulator.h_dict = controller.step(emulator.h_dict)
    emulator.h_dict = hybrid_plant.step(emulator.h_dict)

    # Call the new HDF5 logging function
    emulator._log_data_to_hdf5()

    # Check that HDF5 file was initialized
    assert emulator.output_structure_determined
    assert emulator.hdf5_file is not None
    assert len(emulator.hdf5_datasets) > 0

    # Check that expected datasets exist
    expected_datasets = {
        "time",
        "step",
        "plant_power",
        "plant_locally_generated_power",
        "solar_farm.power",
    }

    actual_datasets = set(emulator.hdf5_datasets.keys())
    missing_datasets = expected_datasets - actual_datasets
    assert expected_datasets.issubset(
        actual_datasets
    ), f"Missing expected datasets: {missing_datasets}"

    # Flush buffer to write data to HDF5
    if hasattr(emulator, "data_buffers") and emulator.data_buffers and emulator.buffer_row > 0:
        emulator._flush_buffer_to_hdf5()

    # Check that data was written correctly
    assert emulator.hdf5_datasets["time"][0] == 5.0
    assert emulator.hdf5_datasets["step"][0] == 5
    assert emulator.hdf5_datasets["plant_power"][0] > 0
    assert emulator.hdf5_datasets["solar_farm.power"][0] > 0

    # Clean up
    emulator.close()


def test_log_data_to_hdf5_with_external_signals():
    """Test that external signals are logged correctly to HDF5."""

    # Use h_dict_battery as base for testing (no external data requirements)
    test_h_dict = h_dict_battery.copy()

    # Add external data file
    test_h_dict["external_data_file"] = "tests/test_inputs/external_data.csv"
    test_h_dict["dt"] = 1.0
    test_h_dict["starttime"] = 0.0
    test_h_dict["endtime"] = 10.0

    # Set up logger for testing
    logger = setup_logging(console_output=False)

    controller = SimpleControllerWind(test_h_dict)  # Use wind controller (works with any config)
    hybrid_plant = HybridPlant(test_h_dict)

    emulator = Emulator(controller, hybrid_plant, test_h_dict, logger)

    # Set up the simulation state
    emulator.time = 5.0
    emulator.step = 5
    emulator.h_dict["time"] = 5.0
    emulator.h_dict["step"] = 5

    # Update external signals (simulate what happens in the run loop)
    if emulator.external_data_all:
        for k in emulator.external_data_all:
            if k == "time":
                continue
            emulator.h_dict["external_signals"][k] = emulator.external_data_all[k][emulator.step]

    # Run controller and hybrid_plant steps to generate plant-level outputs
    emulator.h_dict = controller.step(emulator.h_dict)
    emulator.h_dict = hybrid_plant.step(emulator.h_dict)

    # Call the new HDF5 logging function
    emulator._log_data_to_hdf5()

    # Check that HDF5 file was initialized
    assert emulator.output_structure_determined
    assert emulator.hdf5_file is not None
    assert len(emulator.hdf5_datasets) > 0

    # Check that external signals dataset exists
    expected_external_dataset = "external_signals.power_reference"
    assert expected_external_dataset in emulator.hdf5_datasets

    # Flush buffer to write data to HDF5
    if hasattr(emulator, "data_buffers") and emulator.data_buffers and emulator.buffer_row > 0:
        emulator._flush_buffer_to_hdf5()

    # Check that external signal data was written correctly
    expected_value = emulator.external_data_all["power_reference"][5]  # Value at step 5
    assert emulator.hdf5_datasets[expected_external_dataset][0] == expected_value

    # Clean up
    emulator.close()


def test_log_data_to_hdf5_with_wind_farm_arrays():
    """Test that the new HDF5 logging function handles wind farm array outputs correctly."""

    # Use h_dict_wind as base for testing
    test_h_dict = h_dict_wind.copy()

    # Set up logger for testing
    logger = setup_logging(console_output=False)

    controller = SimpleControllerWind(test_h_dict)
    hybrid_plant = HybridPlant(test_h_dict)

    emulator = Emulator(controller, hybrid_plant, test_h_dict, logger)

    # Set up the simulation state
    emulator.time = 5.0
    emulator.step = 5
    emulator.h_dict["time"] = 5.0
    emulator.h_dict["step"] = 5

    # Run controller and hybrid_plant steps to generate plant-level outputs
    emulator.h_dict = controller.step(emulator.h_dict)
    emulator.h_dict = hybrid_plant.step(emulator.h_dict)

    # Call the new HDF5 logging function
    emulator._log_data_to_hdf5()

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

    actual_datasets = set(emulator.hdf5_datasets.keys())

    # Verify that all expected datasets are present
    missing_datasets = expected_datasets - actual_datasets
    assert expected_datasets.issubset(
        actual_datasets
    ), f"Missing expected datasets: {missing_datasets}"

    # Flush buffer to write data to HDF5
    if hasattr(emulator, "data_buffers") and emulator.data_buffers and emulator.buffer_row > 0:
        emulator._flush_buffer_to_hdf5()

    # Check that data was written correctly
    assert emulator.hdf5_datasets["time"][0] == 5.0
    assert emulator.hdf5_datasets["step"][0] == 5
    assert emulator.hdf5_datasets["wind_farm.power"][0] > 0
    assert emulator.hdf5_datasets["plant_power"][0] > 0
    assert emulator.hdf5_datasets["plant_locally_generated_power"][0] > 0

    # Verify that turbine_powers array is handled correctly
    assert emulator.hdf5_datasets["wind_farm.turbine_powers.000"][0] > 0
    assert emulator.hdf5_datasets["wind_farm.turbine_powers.001"][0] > 0
    assert emulator.hdf5_datasets["wind_farm.turbine_powers.002"][0] > 0

    # Clean up
    emulator.close()


def test_hdf5_output_configuration():
    """Test HDF5 output configuration options: downsampling and chunking."""
    import os
    import tempfile

    from hercules.utilities import read_hercules_hdf5

    # Use h_dict_solar as base for testing
    test_h_dict = h_dict_solar.copy()

    # Set up logger for testing
    logger = setup_logging(console_output=False)

    # Test 1: HDF5 format with downsampling
    with tempfile.TemporaryDirectory() as temp_dir:
        test_h_dict_hdf5 = test_h_dict.copy()
        test_h_dict_hdf5["output_file"] = os.path.join(temp_dir, "test_output.h5")
        test_h_dict_hdf5["dt"] = 1.0
        test_h_dict_hdf5["starttime"] = 0.0
        test_h_dict_hdf5["endtime"] = 5.0

        controller = SimpleControllerSolar(test_h_dict_hdf5)
        hybrid_plant = HybridPlant(test_h_dict_hdf5)
        emulator = Emulator(controller, hybrid_plant, test_h_dict_hdf5, logger)

        # Run simulation and write output
        for step in range(5):  # 5 steps (0-4) for dt=1.0, endtime=5.0, starttime=0.0
            emulator.step = step
            emulator.time = step * emulator.dt
            emulator.h_dict["time"] = emulator.time
            emulator.h_dict["step"] = step
            emulator.h_dict = controller.step(emulator.h_dict)
            emulator.h_dict = hybrid_plant.step(emulator.h_dict)
            emulator._log_data_to_hdf5()

        emulator.close()

        # Verify file exists and is readable
        assert os.path.exists(emulator.output_file)
        df_hdf5 = read_hercules_hdf5(emulator.output_file)
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
        test_h_dict_hdf5_2["starttime"] = 0.0
        test_h_dict_hdf5_2["endtime"] = 5.0

        controller = SimpleControllerSolar(test_h_dict_hdf5_2)
        hybrid_plant = HybridPlant(test_h_dict_hdf5_2)
        emulator = Emulator(controller, hybrid_plant, test_h_dict_hdf5_2, logger)

        # Check configuration
        assert emulator.buffer_size == 500

        # Run simulation and write output
        for step in range(5):  # 5 steps to match the array size
            emulator.step = step
            emulator.time = step * emulator.dt
            emulator.h_dict["time"] = emulator.time
            emulator.h_dict["step"] = step
            emulator.h_dict = controller.step(emulator.h_dict)
            emulator.h_dict = hybrid_plant.step(emulator.h_dict)
            emulator._log_data_to_hdf5()

        emulator.close()

        # Verify file exists and is readable
        assert os.path.exists(emulator.output_file)
        df_hdf5 = read_hercules_hdf5(emulator.output_file)
        assert len(df_hdf5) == 5


def test_log_every_n_option():
    """Test that the log_every_n option works correctly."""
    import os
    import tempfile

    from hercules.utilities import read_hercules_hdf5

    # Use h_dict_solar as base for testing
    test_h_dict = h_dict_solar.copy()

    # Set up logger for testing
    logger = setup_logging(console_output=False)

    # Test with log_every_n = 2
    with tempfile.TemporaryDirectory() as temp_dir:
        test_h_dict_log = test_h_dict.copy()
        test_h_dict_log["output_file"] = os.path.join(temp_dir, "test_output.h5")
        test_h_dict_log["log_every_n"] = 2  # Log every 2 steps
        test_h_dict_log["dt"] = 1.0
        test_h_dict_log["starttime"] = 0.0
        test_h_dict_log["endtime"] = 6.0  # 6 steps total

        controller = SimpleControllerSolar(test_h_dict_log)
        hybrid_plant = HybridPlant(test_h_dict_log)
        emulator = Emulator(controller, hybrid_plant, test_h_dict_log, logger)

        # Check configuration
        assert emulator.log_every_n == 2
        assert emulator.dt_log == 2.0

        # Run simulation and write output
        for step in range(6):  # 6 steps (0-5) for dt=1.0, endtime=6.0, starttime=0.0
            emulator.step = step
            emulator.time = step * emulator.dt
            emulator.h_dict["time"] = emulator.time
            emulator.h_dict["step"] = step
            emulator.h_dict = controller.step(emulator.h_dict)
            emulator.h_dict = hybrid_plant.step(emulator.h_dict)
            emulator._log_data_to_hdf5()

        emulator.close()

        # Verify file exists and is readable
        assert os.path.exists(emulator.output_file)
        df_hdf5 = read_hercules_hdf5(emulator.output_file)
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
        test_h_dict_log2["starttime"] = 0.0
        test_h_dict_log2["endtime"] = 7.0  # 7 steps total

        controller = SimpleControllerSolar(test_h_dict_log2)
        hybrid_plant = HybridPlant(test_h_dict_log2)
        emulator = Emulator(controller, hybrid_plant, test_h_dict_log2, logger)

        # Check configuration
        assert emulator.log_every_n == 3
        assert emulator.dt_log == 3.0

        # Run simulation and write output
        for step in range(7):  # 7 steps (0-6)
            emulator.step = step
            emulator.time = step * emulator.dt
            emulator.h_dict["time"] = emulator.time
            emulator.h_dict["step"] = step
            emulator.h_dict = controller.step(emulator.h_dict)
            emulator.h_dict = hybrid_plant.step(emulator.h_dict)
            emulator._log_data_to_hdf5()

        emulator.close()

        # Verify file exists and is readable
        assert os.path.exists(emulator.output_file)
        df_hdf5 = read_hercules_hdf5(emulator.output_file)
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

    # Modify log_channels to only include turbine_powers.001 (not the full array)
    test_h_dict["wind_farm"]["log_channels"] = ["power", "turbine_powers.001"]

    # Set up logger for testing
    logger = setup_logging(console_output=False)

    controller = SimpleControllerWind(test_h_dict)
    hybrid_plant = HybridPlant(test_h_dict)

    emulator = Emulator(controller, hybrid_plant, test_h_dict, logger)

    # Set up the simulation state
    emulator.time = 5.0
    emulator.step = 5
    emulator.h_dict["time"] = 5.0
    emulator.h_dict["step"] = 5

    # Run controller and hybrid_plant steps to generate plant-level outputs
    emulator.h_dict = controller.step(emulator.h_dict)
    emulator.h_dict = hybrid_plant.step(emulator.h_dict)

    # Call the new HDF5 logging function
    emulator._log_data_to_hdf5()

    # Check that ONLY turbine_powers.001 is logged (not .000 or .002)
    actual_datasets = set(emulator.hdf5_datasets.keys())

    # turbine_powers.001 SHOULD be present
    assert (
        "wind_farm.turbine_powers.001" in actual_datasets
    ), "Expected wind_farm.turbine_powers.001 to be logged"

    # turbine_powers.000 should NOT be present
    assert (
        "wind_farm.turbine_powers.000" not in actual_datasets
    ), "wind_farm.turbine_powers.000 should NOT be logged when only .001 is specified"

    # turbine_powers.002 should NOT be present
    assert (
        "wind_farm.turbine_powers.002" not in actual_datasets
    ), "wind_farm.turbine_powers.002 should NOT be logged when only .001 is specified"

    # Verify that basic datasets are still present
    assert "time" in actual_datasets
    assert "step" in actual_datasets
    assert "wind_farm.power" in actual_datasets

    # Flush buffer to write data to HDF5
    if hasattr(emulator, "data_buffers") and emulator.data_buffers and emulator.buffer_row > 0:
        emulator._flush_buffer_to_hdf5()

    # Verify that turbine_powers.001 has a valid value
    assert emulator.hdf5_datasets["wind_farm.turbine_powers.001"][0] > 0

    # Clean up
    emulator.close()
