import sys

from hercules.floris_standin import launch_floris

# Check that command line arguments are provided
if len(sys.argv) != 3:
    raise Exception("Usage: python floris_runscript.py <amr_input_file> <helics_port>")

# # Get the first command line argument
# This is the name of the file to read
amr_input_file = sys.argv[1]
helics_port = int(sys.argv[2])
print(f"Running FLORIS standin with input file: {amr_input_file} and helics_port: {helics_port}")

# Launch FLORIS
launch_floris(amr_input_file, helics_port=helics_port)
