#!/bin/bash

# Locate the scripts folder
SCRIPTS_DIR="../../scripts"

# Kill any active helics jobs by calling the find_and_kill_helics script
# within the scripts folder
source $SCRIPTS_DIR/find_and_kill_helics.sh

# Run the activate CONDA script within the scripts folder
# to ensure the Hercules environment is active
source $SCRIPTS_DIR/activate_conda.sh

# Identify an available port for the HELICS broker.  This should
# be the first in a sequence of 10 available ports
# In case of comms trouble can be useful to change the first port
# to check for availability
first_port=32000
source $SCRIPTS_DIR/get_helics_port.sh $first_port

# Clean up existing outputs
if [ -d outputs ]; then rm -r outputs; fi
mkdir -p outputs

# # Set up the helics broker
# echo "Connecting helics broker to port $HELICS_PORT"
# helics_broker -t zmq  -f 2 --loglevel="debug" --local_port=$HELICS_PORT & 
# #helics_broker -f 2 --consoleloglevel=trace --loglevel=debug --local_port=$HELICS_PORT >> loghelics &

# python hercules_runscript.py hercules_input_000.yaml $HELICS_PORT>> outputs/loghercules.log 2>&1 &
# python floris_runscript.py inputs/amr_input.inp inputs/floris_standin_data_fixedwd.csv $HELICS_PORT >> outputs/logfloris.log 2>&1



# # Set the helics port to use: 
# #make sure you use the same port number in the amr_input.inp and hercules_input_000.yaml files. 
# export HELICS_PORT=32000

# Set up the helics broker and run the simulation
echo "Running agressive battery control simulation."
helics_broker -t zmq -f 2 --loglevel="debug" --local_port=$HELICS_PORT &
python hercules_runscript.py inputs/hercules_input_agressive.yaml $HELICS_PORT>> outputs/loghercules_ag.log 2>&1 &
python floris_runscript.py inputs/amr_input.inp inputs/floris_standin_data_fixedwd-hour.csv $HELICS_PORT>> outputs/logfloris_ag.log 2>&1

# Wait for the open-loop control simulation to finish and then run the closed-loop simulation
echo "Running protective battery control simulation."
helics_broker -t zmq  -f 2 --loglevel="debug" --local_port=$HELICS_PORT & 
python hercules_runscript.py inputs/hercules_input_protective.yaml $HELICS_PORT>> outputs/loghercules_pr.log 2>&1 &
python floris_runscript.py inputs/amr_input.inp inputs/floris_standin_data_fixedwd-hour.csv $HELICS_PORT>> outputs/logfloris_pr.log 2>&1

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

# # Report success and plot results
echo "Finished running simulations. Plotting results."
python plot_outputs.py

# exit 0
