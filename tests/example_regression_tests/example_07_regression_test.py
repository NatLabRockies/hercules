import shutil
import tempfile
from copy import deepcopy
from pathlib import Path

import hercules
from hercules.hercules_model import HerculesModel
from hercules.utilities import load_yaml

HERCULES_EXAMPLE_DIR = Path(hercules.__file__).parent.parent / "examples"


class ControllerOCGT:
    """Controller implementing the OCGT schedule described in the module docstring."""

    def __init__(self, h_dict):
        """Initialize the controller.

        Args:
            h_dict (dict): The hercules input dictionary.

        """
        self.capacity_rated = h_dict["open_cycle_gas_turbine"]["capacity_rated"]

    def step(self, h_dict):
        """Execute one control step.

        Args:
            h_dict (dict): The hercules input dictionary.

        Returns:
            dict: The updated hercules input dictionary.

        """
        current_time = h_dict["time"]

        # Determine power setpoint based on time
        if current_time < 10 * 60:  # 10 minutes in seconds
            # Before 10 minutes: run at full capacity
            power_setpoint = self.capacity_rated
        elif current_time < 40 * 60:  # 40 minutes in seconds
            # Between 10 and 40 minutes: shut down
            power_setpoint = 0.0
        elif current_time < 120 * 60:  # 120 minutes in seconds
            # Between 40 and 120 minutes: signal to run at full capacity
            power_setpoint = self.capacity_rated
        elif current_time < 180 * 60:  # 180 minutes in seconds
            # Between 120 and 180 minutes: reduce power to 50% of rated capacity
            power_setpoint = 0.5 * self.capacity_rated
        elif current_time < 210 * 60:  # 210 minutes in seconds
            # Between 180 and 210 minutes: reduce power to 10% of rated capacity
            power_setpoint = 0.1 * self.capacity_rated
        elif current_time < 240 * 60:  # 240 minutes in seconds
            # Between 210 and 240 minutes: increase power to 100% of rated capacity
            power_setpoint = self.capacity_rated
        else:
            # After 240 minutes: shut down
            power_setpoint = 0.0

        h_dict["open_cycle_gas_turbine"]["power_setpoint"] = power_setpoint

        return h_dict


def run_hercules_example(hercules_dict):

    # Initialize the Hercules model
    hmodel = HerculesModel(hercules_dict)

    # Instantiate the controller and assign to the Hercules model
    hmodel.assign_controller(ControllerOCGT(hmodel.h_dict))

    # Run the simulation
    hmodel.run()

    hmodel.logger.info("Process completed successfully")

    return hmodel


def test_specified_output_dir():
    test_n = "01"
    # what happens with non-default output dir and all default logging logic

    output_dir = HERCULES_EXAMPLE_DIR / "07_thermal_plants" / f"outputs_test{test_n}"
    logger_dir = HERCULES_EXAMPLE_DIR / "07_thermal_plants" / f"outputs_test{test_n}"

    hercules_fpath = (
        HERCULES_EXAMPLE_DIR / "07_thermal_plants" / "input_files" / "hercules_input_ocgt.yaml"
    )
    hercules_dict = load_yaml(hercules_fpath)
    hercules_dict["output_dir"] = output_dir
    hercules_dict["output_filename"] = f"hercules_output_test{test_n}.h5"
    hercules_dict["logging"] = {}

    run_hercules_example(hercules_dict)

    expected_output_h5_fpath = output_dir / f"hercules_output_test{test_n}.h5"
    expected_output_main_log_fpath = logger_dir / "log_hercules.log"
    expected_component_log_fpath = logger_dir / "log_open_cycle_gas_turbine.log"

    assert expected_output_h5_fpath.is_file(), "h5 file"
    assert expected_output_main_log_fpath.is_file(), "main log file"
    assert expected_component_log_fpath.is_file(), "component log file"

    shutil.rmtree(output_dir)
    assert not output_dir.is_dir()


def test_specified_main_logger_dir():
    test_n = "02"
    # what happens with non-default output dir and a different logging dir

    output_dir = HERCULES_EXAMPLE_DIR / "07_thermal_plants" / f"outputs_test{test_n}"
    logger_dir = HERCULES_EXAMPLE_DIR / "07_thermal_plants" / f"loggers_{test_n}"

    hercules_fpath = (
        HERCULES_EXAMPLE_DIR / "07_thermal_plants" / "input_files" / "hercules_input_ocgt.yaml"
    )
    hercules_dict = load_yaml(hercules_fpath)
    hercules_dict["output_dir"] = output_dir
    hercules_dict["output_filename"] = f"hercules_output_test{test_n}.h5"
    hercules_dict["logging"] = {
        "logging_dir": logger_dir,
        "log_filename": f"log_hercules_test{test_n}.log",
    }

    run_hercules_example(hercules_dict)

    expected_output_h5_fpath = output_dir / f"hercules_output_test{test_n}.h5"
    expected_output_main_log_fpath = logger_dir / f"log_hercules_test{test_n}.log"
    expected_component_log_fpath = logger_dir / "log_open_cycle_gas_turbine.log"

    assert expected_output_h5_fpath.is_file(), "h5 file"
    assert expected_output_main_log_fpath.is_file(), "main log file"
    assert expected_component_log_fpath.is_file(), "component log file"

    shutil.rmtree(output_dir)
    assert not output_dir.is_dir()

    shutil.rmtree(logger_dir)
    assert not logger_dir.is_dir()


def test_auto_increment_output_filename():
    test_n = "03"

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir, "outputs")
        logger_dir = Path(tmpdir, "loggers")

        hercules_fpath = (
            HERCULES_EXAMPLE_DIR / "07_thermal_plants" / "input_files" / "hercules_input_ocgt.yaml"
        )
        hercules_dict = load_yaml(hercules_fpath)
        hercules_dict["output_dir"] = output_dir
        hercules_dict["output_filename"] = f"hercules_output_test{test_n}.h5"
        hercules_dict["auto_increment_filenames"] = True
        hercules_dict["logging"] = {
            "logging_dir": logger_dir,
            "log_filename": f"log_hercules_test{test_n}.log",
        }

        # The first run uses the requested output filename. (AI)
        run_hercules_example(deepcopy(hercules_dict))

        expected_output_h5_fpath = output_dir / f"hercules_output_test{test_n}.h5"
        expected_output_main_log_fpath = logger_dir / f"log_hercules_test{test_n}.log"
        expected_component_log_fpath = logger_dir / "log_open_cycle_gas_turbine.log"

        assert expected_output_h5_fpath.is_file(), "run 1, h5 file"
        assert expected_output_main_log_fpath.is_file(), "run 1, main log file"
        assert expected_component_log_fpath.is_file(), "run 1, component log file"

        # A collision increments the filename without changing the output directory. (AI)
        run_hercules_example(deepcopy(hercules_dict))

        expected_output_h5_fpath = output_dir / f"hercules_output_test{test_n}0.h5"

        assert expected_output_h5_fpath.is_file(), "run 2, h5 file"
        assert expected_output_main_log_fpath.is_file(), "run 2, main log file"
        assert expected_component_log_fpath.is_file(), "run 2, component log file"

        # Further collisions increment to the next available suffix. (AI)
        run_hercules_example(deepcopy(hercules_dict))

        expected_output_h5_fpath = output_dir / f"hercules_output_test{test_n}1.h5"

        assert expected_output_h5_fpath.is_file(), "run 3, h5 file"
        assert expected_output_main_log_fpath.is_file(), "run 3, main log file"
        assert expected_component_log_fpath.is_file(), "run 3, component log file"
