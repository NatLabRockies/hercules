import shutil
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
        self.rated_capacity = h_dict["open_cycle_gas_turbine"]["rated_capacity"]

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
            power_setpoint = self.rated_capacity
        elif current_time < 40 * 60:  # 40 minutes in seconds
            # Between 10 and 40 minutes: shut down
            power_setpoint = 0.0
        elif current_time < 120 * 60:  # 120 minutes in seconds
            # Between 40 and 120 minutes: signal to run at full capacity
            power_setpoint = self.rated_capacity
        elif current_time < 180 * 60:  # 180 minutes in seconds
            # Between 120 and 180 minutes: reduce power to 50% of rated capacity
            power_setpoint = 0.5 * self.rated_capacity
        elif current_time < 210 * 60:  # 210 minutes in seconds
            # Between 180 and 210 minutes: reduce power to 10% of rated capacity
            power_setpoint = 0.1 * self.rated_capacity
        elif current_time < 240 * 60:  # 240 minutes in seconds
            # Between 210 and 240 minutes: increase power to 100% of rated capacity
            power_setpoint = self.rated_capacity
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
    # what happens with non-default output dir

    output_dir = HERCULES_EXAMPLE_DIR / "07_open_cycle_gas_turbine" / f"outputs_test{test_n}"
    logger_dir = HERCULES_EXAMPLE_DIR / "07_open_cycle_gas_turbine" / f"outputs_test{test_n}"

    hercules_fpath = HERCULES_EXAMPLE_DIR / "07_open_cycle_gas_turbine" / "hercules_input.yaml"
    hercules_dict = load_yaml(hercules_fpath)
    hercules_dict["output_dir"] = output_dir
    hercules_dict["output_file"] = f"hercules_output_test{test_n}.h5"
    hercules_dict["overwrite_outputs"] = True
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
    # what happens with non-default output dir

    output_dir = HERCULES_EXAMPLE_DIR / "07_open_cycle_gas_turbine" / f"outputs_test{test_n}"
    logger_dir = HERCULES_EXAMPLE_DIR / "07_open_cycle_gas_turbine" / f"loggers_{test_n}"

    hercules_fpath = HERCULES_EXAMPLE_DIR / "07_open_cycle_gas_turbine" / "hercules_input.yaml"
    hercules_dict = load_yaml(hercules_fpath)
    hercules_dict["output_dir"] = output_dir
    hercules_dict["output_file"] = f"hercules_output_test{test_n}.h5"
    hercules_dict["overwrite_outputs"] = True
    hercules_dict["logging"] = {
        "use_outputs_dir": True,
        "outputs_dir": logger_dir,
        "log_file": f"log_hercules_test{test_n}.log",
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


def test_dont_use_outputs_dir_logging():
    test_n = "03"
    # what happens with non-default output dir
    cwd = Path.cwd().absolute()

    output_dir = HERCULES_EXAMPLE_DIR / "07_open_cycle_gas_turbine" / f"outputs_test{test_n}"
    logger_dir = HERCULES_EXAMPLE_DIR / "07_open_cycle_gas_turbine" / f"loggers_{test_n}"

    hercules_fpath = HERCULES_EXAMPLE_DIR / "07_open_cycle_gas_turbine" / "hercules_input.yaml"
    hercules_dict = load_yaml(hercules_fpath)
    hercules_dict["output_dir"] = output_dir
    hercules_dict["output_file"] = f"hercules_output_test{test_n}.h5"
    hercules_dict["overwrite_outputs"] = True
    hercules_dict["logging"] = {
        "use_outputs_dir": False,
        "outputs_dir": logger_dir,
        "log_file": f"log_hercules_test{test_n}.log",
    }

    run_hercules_example(hercules_dict)

    expected_output_h5_fpath = output_dir / f"hercules_output_test{test_n}.h5"
    expected_output_main_log_fpath = cwd / f"log_hercules_test{test_n}.log"
    expected_component_log_fpath = cwd / "log_open_cycle_gas_turbine.log"

    assert expected_output_h5_fpath.is_file(), "h5 file"
    assert expected_output_main_log_fpath.is_file(), "main log file"
    assert expected_component_log_fpath.is_file(), "component log file"

    shutil.rmtree(output_dir)
    assert not output_dir.is_dir()

    expected_component_log_fpath.unlink()
    expected_output_main_log_fpath.unlink()

    assert not expected_component_log_fpath.is_file()
    assert not expected_output_main_log_fpath.is_file()
