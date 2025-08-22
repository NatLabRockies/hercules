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
    assert emulator.output_file == "outputs/hercules_output.feather"
    assert emulator.output_format == "feather"
    assert emulator.output_downsample_factor == 1
    assert emulator.external_data_all == {}

    # Test with external data file and custom output file
    test_h_dict_2 = test_h_dict.copy()
    test_h_dict_2["external_data_file"] = "tests/test_inputs/external_data.csv"
    test_h_dict_2["output_file"] = "test_output.csv"
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
    assert emulator.output_file == "test_output.csv"


def test_log_h_dict_refactored():
    """Test that the refactored log_h_dict function only logs specific fields."""

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

    # Call the refactored log_h_dict function
    emulator.log_h_dict()

    # Check that only the expected fields are logged
    expected_keys = {
        "time",
        "step",
        "clock_time",
        "plant.power",
        "plant.locally_generated_power",
        "solar_farm.power",  # From solar_farm's log_outputs
    }

    actual_keys = set(emulator.output_columns)

    # Verify that all expected keys are present
    assert expected_keys.issubset(actual_keys), (
        f"Missing expected keys: {expected_keys - actual_keys}"
    )

    # Verify that the values are correct (data stored in output_data array)
    time_idx = emulator.output_columns.index("time")
    step_idx = emulator.output_columns.index("step")
    solar_power_idx = emulator.output_columns.index("solar_farm.power")

    # Since we use a buffered approach, access the current buffer position
    buffer_pos = emulator.buffer_position - 1  # Last written position
    assert emulator.output_buffer[buffer_pos, time_idx] == 5.0
    assert emulator.output_buffer[buffer_pos, step_idx] == 5
    assert emulator.output_buffer[buffer_pos, solar_power_idx] > 0

    # Verify plant power values
    plant_power_idx = emulator.output_columns.index("plant.power")
    locally_gen_power_idx = emulator.output_columns.index("plant.locally_generated_power")
    assert emulator.output_buffer[buffer_pos, plant_power_idx] > 0  # Should be positive
    assert emulator.output_buffer[buffer_pos, locally_gen_power_idx] > 0  # Should be positive

    # Verify that clock_time is set
    assert "clock_time" in emulator.output_columns
    clock_time_idx = emulator.output_columns.index("clock_time")
    assert emulator.output_buffer[buffer_pos, clock_time_idx] is not None

    # Verify that we don't have unexpected keys (like the old flattened structure)
    unexpected_keys = [k for k in actual_keys if k.startswith("solar_farm.irradiance")]
    assert len(unexpected_keys) == 0, f"Unexpected keys found: {unexpected_keys}"


def test_log_h_dict_with_wind_farm_arrays():
    """Test that the refactored log_h_dict function handles wind farm array outputs correctly."""

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

    # Call the refactored log_h_dict function
    emulator.log_h_dict()

    # Check that array outputs are flattened correctly
    expected_keys = {
        "time",
        "step",
        "clock_time",
        "plant.power",
        "plant.locally_generated_power",
        "wind_farm.power",
        "wind_farm.turbine_powers.000",
        "wind_farm.turbine_powers.001",
        "wind_farm.turbine_powers.002",
    }

    actual_keys = set(emulator.output_columns)

    # Verify that all expected keys are present
    assert expected_keys.issubset(actual_keys), (
        f"Missing expected keys: {expected_keys - actual_keys}"
    )

    # Verify that the values are correct (data stored in output_data array)
    time_idx = emulator.output_columns.index("time")
    step_idx = emulator.output_columns.index("step")
    wind_power_idx = emulator.output_columns.index("wind_farm.power")
    plant_power_idx = emulator.output_columns.index("plant.power")
    locally_gen_power_idx = emulator.output_columns.index("plant.locally_generated_power")

    # Since we use a buffered approach, access the current buffer position
    buffer_pos = emulator.buffer_position - 1  # Last written position
    assert emulator.output_buffer[buffer_pos, time_idx] == 5.0
    assert emulator.output_buffer[buffer_pos, step_idx] == 5
    assert emulator.output_buffer[buffer_pos, wind_power_idx] > 0
    assert emulator.output_buffer[buffer_pos, plant_power_idx] > 0  # Should be positive
    assert emulator.output_buffer[buffer_pos, locally_gen_power_idx] > 0  # Should be positive

    # Verify that turbine_powers array is flattened correctly
    turbine_power_0_idx = emulator.output_columns.index("wind_farm.turbine_powers.000")
    turbine_power_1_idx = emulator.output_columns.index("wind_farm.turbine_powers.001")
    turbine_power_2_idx = emulator.output_columns.index("wind_farm.turbine_powers.002")

    assert emulator.output_buffer[buffer_pos, turbine_power_0_idx] > 0
    assert emulator.output_buffer[buffer_pos, turbine_power_1_idx] > 0
    assert emulator.output_buffer[buffer_pos, turbine_power_2_idx] > 0

    # Verify that clock_time is set
    assert "clock_time" in emulator.output_columns
    clock_time_idx = emulator.output_columns.index("clock_time")
    assert emulator.output_buffer[buffer_pos, clock_time_idx] is not None


def test_output_configuration_options():
    """Test new output configuration options: format, downsampling, and precision."""
    import os
    import tempfile

    import pandas as pd

    # Use h_dict_solar as base for testing
    test_h_dict = h_dict_solar.copy()

    # Set up logger for testing
    logger = setup_logging(console_output=False)

    # Test 1: Feather format with downsampling
    with tempfile.TemporaryDirectory() as temp_dir:
        test_h_dict_feather = test_h_dict.copy()
        test_h_dict_feather["output_file"] = os.path.join(temp_dir, "test_output.feather")
        test_h_dict_feather["output_format"] = "feather"
        test_h_dict_feather["output_time_step"] = 2.0  # 2x downsampling
        test_h_dict_feather["dt"] = 1.0
        test_h_dict_feather["starttime"] = 0.0
        test_h_dict_feather["endtime"] = 5.0

        controller = SimpleControllerSolar(test_h_dict_feather)
        hybrid_plant = HybridPlant(test_h_dict_feather)
        emulator = Emulator(controller, hybrid_plant, test_h_dict_feather, logger)

        # Check configuration
        assert emulator.output_format == "feather"
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
            emulator.log_h_dict()

        emulator.close_output_file()

        # Verify file exists and is readable
        assert os.path.exists(emulator.output_file)
        df_feather = pd.read_feather(emulator.output_file)
        # 5 steps downsampled by factor 2 should give 3 rows (0, 2, 4)
        # Let's check for non-null rows since downsampling may leave some NaN rows
        non_null_rows = df_feather.dropna().shape[0]
        assert non_null_rows == 3

    # Test 2: Parquet format
    with tempfile.TemporaryDirectory() as temp_dir:
        test_h_dict_parquet = test_h_dict.copy()
        test_h_dict_parquet["output_file"] = os.path.join(temp_dir, "test_output.parquet")
        test_h_dict_parquet["output_format"] = "parquet"
        test_h_dict_parquet["dt"] = 1.0
        test_h_dict_parquet["starttime"] = 0.0
        test_h_dict_parquet["endtime"] = 5.0

        controller = SimpleControllerSolar(test_h_dict_parquet)
        hybrid_plant = HybridPlant(test_h_dict_parquet)
        emulator = Emulator(controller, hybrid_plant, test_h_dict_parquet, logger)

        # Run simulation and write output
        for step in range(5):  # 5 steps to match the array size
            emulator.step = step
            emulator.time = step * emulator.dt
            emulator.h_dict["time"] = emulator.time
            emulator.h_dict["step"] = step
            emulator.h_dict = controller.step(emulator.h_dict)
            emulator.h_dict = hybrid_plant.step(emulator.h_dict)
            emulator.log_h_dict()

        emulator.close_output_file()

        # Verify file exists and is readable
        assert os.path.exists(emulator.output_file)
        df_parquet = pd.read_parquet(emulator.output_file)
        # No downsampling, so should have all 5 rows
        assert len(df_parquet) == 5

    # Test 3: CSV format (backward compatibility)
    with tempfile.TemporaryDirectory() as temp_dir:
        test_h_dict_csv = test_h_dict.copy()
        test_h_dict_csv["output_file"] = os.path.join(temp_dir, "test_output.csv")
        test_h_dict_csv["output_format"] = "csv"
        test_h_dict_csv["dt"] = 1.0
        test_h_dict_csv["starttime"] = 0.0
        test_h_dict_csv["endtime"] = 5.0

        controller = SimpleControllerSolar(test_h_dict_csv)
        hybrid_plant = HybridPlant(test_h_dict_csv)
        emulator = Emulator(controller, hybrid_plant, test_h_dict_csv, logger)

        # Run simulation and write output
        for step in range(5):  # 5 steps to match the array size
            emulator.step = step
            emulator.time = step * emulator.dt
            emulator.h_dict["time"] = emulator.time
            emulator.h_dict["step"] = step
            emulator.h_dict = controller.step(emulator.h_dict)
            emulator.h_dict = hybrid_plant.step(emulator.h_dict)
            emulator.log_h_dict()

        emulator.close_output_file()

        # Verify file exists and is readable
        assert os.path.exists(emulator.output_file)
        df_csv = pd.read_csv(emulator.output_file)
        # No downsampling, so should have all 5 rows
        assert len(df_csv) == 5
