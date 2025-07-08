#!/bin/bash

# Locate the scripts folder
SCRIPTS_DIR="../../scripts"



# Run the activate CONDA script within the scripts folder
# to ensure the Hercules environment is active
source $SCRIPTS_DIR/activate_conda.sh

# Pull the wind input from example 02
if [ ! -f inputs/wind_input.p ]; then
    # Check if the file exists in the example 10 folder
    if [ -f ../12_WindSimLongTerm_RealisticInflow/inputs/wind_input.p ]; then
        echo "Copying wind input from example 02"
        cp ../02_wind_farm_realistic_inflow/inputs/wind_input.p inputs/
    else
        echo "Wind input file not found in example 02 folder. Please generate it first."
        exit 1
    fi
fi


# Run Hercules
python hercules_runscript.py hercules_input.yaml >> outputs/log_bash.log 2>&1 # Start the controller center and pass in input file


# If everything is successful
echo "Finished running hercules"
echo "Plotting simulation results"
python plot_outputs.py
exit 0

