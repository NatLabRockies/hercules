import numpy as np
from hercules.emulator import Emulator
from hercules.hybrid_plant import HybridPlant
from hercules.utilities import setup_logging

from tests.test_inputs.h_dict import h_dict_solar, h_dict_wind


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
    assert emulator.output_downsample_factor == 1
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
        "clock_time",
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
        "clock_time",
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
        test_h_dict_hdf5["output_time_step"] = 2.0  # 2x downsampling
        test_h_dict_hdf5["dt"] = 1.0
        test_h_dict_hdf5["starttime"] = 0.0
        test_h_dict_hdf5["endtime"] = 5.0

        controller = SimpleControllerSolar(test_h_dict_hdf5)
        hybrid_plant = HybridPlant(test_h_dict_hdf5)
        emulator = Emulator(controller, hybrid_plant, test_h_dict_hdf5, logger)

        # Check configuration
        assert emulator.output_time_step == 2.0
        assert emulator.output_downsample_factor == 2

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
        # 5 steps downsampled by factor 2 should give 3 rows (0, 2, 4)
        assert len(df_hdf5) == 3
        assert df_hdf5["time"].iloc[0] == 0.0
        assert df_hdf5["time"].iloc[1] == 2.0
        assert df_hdf5["time"].iloc[2] == 4.0

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
