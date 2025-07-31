from hercules.emulator import Emulator
from hercules.hybrid_plant import HybridPlant
from hercules.utilities import setup_logging

from .test_inputs.h_dict import h_dict_solar, h_dict_wind


class SimpleController:
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
        # Set deratings for wind turbines if wind farm is present
        if "wind_farm" in h_dict and "n_turbines" in h_dict["wind_farm"]:
            for t_idx in range(h_dict["wind_farm"]["n_turbines"]):
                h_dict["wind_farm"][f"derating_{t_idx:03d}"] = 5000

        return h_dict


def test_Emulator_instantiation():
    """Test that the Emulator can be instantiated with different configurations."""

    # Use h_dict_solar as base for testing
    test_h_dict = h_dict_solar.copy()

    # Set up logger for testing
    logger = setup_logging(console_output=False)

    controller = SimpleController(test_h_dict)
    hybrid_plant = HybridPlant(test_h_dict)

    emulator = Emulator(controller, hybrid_plant, test_h_dict, logger)

    # Check default settings
    assert emulator.output_file == "outputs/hercules_output.csv"
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

    controller = SimpleController(test_h_dict)
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

    actual_keys = set(emulator.h_dict_flat.keys())

    # Verify that all expected keys are present
    assert expected_keys.issubset(
        actual_keys
    ), f"Missing expected keys: {expected_keys - actual_keys}"

    # Verify that the values are correct
    assert emulator.h_dict_flat["time"] == 5.0
    assert emulator.h_dict_flat["step"] == 5
    assert emulator.h_dict_flat["solar_farm.power"] > 0
    assert emulator.h_dict_flat["plant.power"] > 0  # Should be positive
    assert emulator.h_dict_flat["plant.locally_generated_power"] > 0  # Should be positive

    # Verify that clock_time is set
    assert "clock_time" in emulator.h_dict_flat
    assert emulator.h_dict_flat["clock_time"] is not None

    # Verify that we don't have unexpected keys (like the old flattened structure)
    unexpected_keys = [k for k in actual_keys if k.startswith("solar_farm.irradiance")]
    assert len(unexpected_keys) == 0, f"Unexpected keys found: {unexpected_keys}"


def test_log_h_dict_with_wind_farm_arrays():
    """Test that the refactored log_h_dict function handles wind farm array outputs correctly."""

    # Use h_dict_wind as base for testing
    test_h_dict = h_dict_wind.copy()

    # Set up logger for testing
    logger = setup_logging(console_output=False)

    controller = SimpleController(test_h_dict)
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

    actual_keys = set(emulator.h_dict_flat.keys())

    # Verify that all expected keys are present
    assert expected_keys.issubset(
        actual_keys
    ), f"Missing expected keys: {expected_keys - actual_keys}"

    # Verify that the values are correct
    assert emulator.h_dict_flat["time"] == 5.0
    assert emulator.h_dict_flat["step"] == 5
    assert emulator.h_dict_flat["wind_farm.power"] > 0
    assert emulator.h_dict_flat["plant.power"] > 0  # Should be positive
    assert emulator.h_dict_flat["plant.locally_generated_power"] > 0  # Should be positive

    # Verify that turbine_powers array is flattened correctly
    assert emulator.h_dict_flat["wind_farm.turbine_powers.000"] > 0
    assert emulator.h_dict_flat["wind_farm.turbine_powers.001"] > 0
    assert emulator.h_dict_flat["wind_farm.turbine_powers.002"] > 0

    # Verify that clock_time is set
    assert "clock_time" in emulator.h_dict_flat
    assert emulator.h_dict_flat["clock_time"] is not None
