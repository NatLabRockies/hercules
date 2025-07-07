import os
import shutil
import sys

from hercules.controller_standin import ControllerStandin
from hercules.emulator import Emulator
from hercules.py_sims import PySims
from hercules.utilities import load_hercules_input, setup_logging

# If the output folder exists, delete it
if os.path.exists("outputs"):
    shutil.rmtree("outputs")
os.makedirs("outputs")

# Get the logger
logger = setup_logging()

# If more than one argument is provided raise and error
if len(sys.argv) > 2:
    raise Exception(
        "Usage: python hercules_runscript.py [hercules_input_file] or python hercules_runscript.py"
    )

# If one arugument is provided, use it as the input file
if len(sys.argv) == 2:
    input_file = sys.argv[1]
# If no arguments are provided, use the default input file
else:
    input_file = "hercules_input.yaml"

# Initialize logging
logger.info(f"Starting with input file: {input_file}")

# Load the input file
h_dict = load_hercules_input(input_file)

# Initialize the controller
controller = ControllerStandin(h_dict)

# Intiialize the py_sims
py_sims = PySims(h_dict)

# Initialize the emulator
emulator = Emulator(controller, py_sims, h_dict, logger)

# Run the emulator
emulator.enter_execution(function_targets=[], function_arguments=[[]])

logger.info("Process completed successfully")
