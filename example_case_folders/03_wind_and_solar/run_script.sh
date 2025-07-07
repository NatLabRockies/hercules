#!/bin/bash

# Locate the scripts folder
SCRIPTS_DIR="../../scripts"



# Run the activate CONDA script within the scripts folder
# to ensure the Hercules environment is active
source $SCRIPTS_DIR/activate_conda.sh

# Pull the wind input from example 12
if [ ! -f inputs/wind_input.p ]; then
    # Check if the file exists in the example 10 folder
    if [ -f ../12_WindSimLongTerm_RealisticInflow/inputs/wind_input.p ]; then
        echo "Copying wind input from example 12"
        cp ../12_WindSimLongTerm_RealisticInflow/inputs/wind_input.p inputs/
    else
        echo "Wind input file not found in example 12 folder. Please generate it first."
        exit 1
    fi
fi

# Clean up existing outputs
if [ -d outputs ]; then rm -r outputs; fi
mkdir -p outputs


# Run Hercules
python hercules_runscript.py hercules_input_000.yaml >> outputs/log_bash.log 2>&1 # Start the controller center and pass in input file

# Clean up helics output if there
# Search for a file that begins with the current year
# And ends with csv
# If the file exists, move to outputs folder
current_year=$(date +"%Y")
for file in ${current_year}*.csv; do
    if [ -f "$file" ]; then
        mv "$file" outputs/
    fi
done

# If everything is successful
echo "Finished running hercules"
echo "Plotting simulation results"
python plot_outputs.py
exit 0

