import sys

from hercules.controller_standin_no_helics import ControllerStandinNoHelics
from hercules.emulator_no_helics import EmulatorNoHelics
from hercules.py_sims import PySims
from hercules.utilities import load_yaml, setup_logging

# Get the logger
logger = setup_logging()

# Check that command line arguments are provided
if len(sys.argv) != 2:
    raise Exception("Usage: python hercules_runscript.py <hercules_input_file>")

input_dict = load_yaml(sys.argv[1])

# Initialize logging
logger.info(f"Starting with input file: {sys.argv[1]}")


# For debugging
# input_dict = load_yaml("hercules_input_000.yaml")


controller = ControllerStandinNoHelics(input_dict)


py_sims = PySims(input_dict)


emulator = EmulatorNoHelics(controller, py_sims, input_dict,logger)

emulator.enter_execution(function_targets=[], function_arguments=[[]])

logger.info("Process completed successfully")