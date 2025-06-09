import sys

from hercules.emulator import Emulator
from hercules.py_sims import PySims
from hercules.utilities import load_yaml
from whoc.controllers import (
    BatteryController,
    HybridSupervisoryControllerBaseline,
    SolarPassthroughController,
    WindFarmPowerTrackingController,
)
from whoc.interfaces import HerculesHybridADInterface

# Check that command line arguments are provided
if len(sys.argv) != 3:
    raise Exception("Usage: python hercules_runscript.py <hercules_input_file> <helics_port>")


# User options
include_solar = False
include_battery = True

# Load all inputs, remove solar and/or battery as desired
input_dict = load_yaml(sys.argv[1])

print("Establishing simulators.")
py_sims = PySims(input_dict)

# Establish controllers based on options
interface = HerculesHybridADInterface(input_dict)
print("Setting up controller.")
wind_controller = WindFarmPowerTrackingController(interface, input_dict)
solar_controller = (
    SolarPassthroughController(interface, input_dict) if include_solar
    else None
)
battery_controller = (
    BatteryController(interface, input_dict) if include_battery
    else None
)
controller = HybridSupervisoryControllerBaseline(
    interface,
    input_dict,
    wind_controller=wind_controller,
    solar_controller=None,
    battery_controller=battery_controller
)

# Set the helics port
helics_port = int(sys.argv[2])
input_dict["hercules_comms"]["helics"]["config"]["helics"]["helicsport"] = helics_port
print(f"Running Hercules with helics_port {helics_port}")

emulator = Emulator(controller, py_sims, input_dict)
emulator.run_helics_setup()
emulator.enter_execution(function_targets=[], function_arguments=[[]])
