#!/bin/bash

# Locate the scripts folder
SCRIPTS_DIR="../../scripts"

# Run the activate CONDA script within the scripts folder
# to ensure the Hercules environment is active
source $SCRIPTS_DIR/activate_conda.sh


# Clean up existing outputs
if [ -d outputs ]; then rm -r outputs; fi
mkdir -p outputs

# If inputs/wind_input.csv does not yet exist, generate it by running generate_wind_history.ipynb from the command line
if [ ! -f inputs/wind_input.csv ]; then
    echo "Generating wind history since it does not exist yet"
    echo "(Running jupyter notebook generate_wind_history.ipynb)"
    echo "(...This may take a few minutes)"
    jupyter nbconvert --to notebook --execute generate_wind_history.ipynb
    echo "Finished generating wind history"
fi


# Run Hercules
echo "Starting Hercules"
python hercules_runscript.py hercules_input.yaml >> outputs/log_bash.log 2>&1 # Start the controller center and pass in input file


# If everything is successful
echo "Finished running hercules"
exit 0

