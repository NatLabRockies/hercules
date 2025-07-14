# This script implements a test client to test out the server against
# It is based on code from
# https://github.com/TUDelft-DataDrivenControl/SOWFA/blob/master/exampleCases/example.12.piso.NREL5MW.ADM.zmqSSC.python/ssc/testclient.py

# The basic operation for this script is to pretend to be the wind farm simulator by:
# - First connecting to the front-end server
# - Than in a loop:
# - - Send the measurement values of 4 turbines
# - - Receive the wind speed and wind direction measurements
# - - Update the turbine measurements
# - - Sleep for 1 s

import ast
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from SEAS.federate_agent import FederateAgent

# Set up the logger
# Useful for when running on eagle
Path("outputs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M",
    filename="outputs/log_test_client.log",
    filemode="w",
)
logger = logging.getLogger("amr_wind_standin")

# Perhaps a small hack to also send log to the terminal outout
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

#  Make an announcement
logger.info("Emulator amr_wind_standin (standing in for AMR-Wind) connecting to server")


# Define a function to read the amrwind input file
# Note simply copied from emulator
def read_amr_wind_input(amr_wind_input):
    # Probably want a file not found error instead
    return_dict = {}

    with open(amr_wind_input) as fp:
        Lines = fp.readlines()

        # Get the simulation time step
        for line in Lines:
            if "time.fixed_dt" in line:
                dt = float(line.split()[2])

        # Get the simulation time step
        for line in Lines:
            if "time.fixed_dt" in line:
                dt = float(line.split()[2])

        # Find the actuators
        for line in Lines:
            if "Actuator.labels" in line:
                turbine_labels = line.split()[2:]
                num_turbines = len(turbine_labels)

        # Find the diameter
        for line in Lines:
            if "rotor_diameter" in line:
                D = float(line.split()[-1])

        # Get the turbine locations
        turbine_locations = []
        for label in turbine_labels:
            for line in Lines:
                if "Actuator.%s.base_position" % label in line:
                    locations = tuple([float(f) for f in line.split()[-3:-1]])
                    turbine_locations.append(locations)

        # Get the helics port
        for line in Lines:
            if "helics.broker_port" in line:
                if len(line.split()) < 3:
                    raise ValueError("Broker port couldn't be read. Check the spacing after the =")
                broker_port = int(line.split()[2])

        # Get the stop time
        for line in Lines:
            if "time.stop_time" in line:
                stop_time = float(line.split()[2])

        return_dict = {
            "dt": dt,
            "num_turbines": num_turbines,
            "turbine_labels": turbine_labels,
            "rotor_diameter": D,
            "turbine_locations": turbine_locations,
            "helics_port": broker_port,
            "stop_time": stop_time,
        }

    return return_dict


class AMRWindStandin(FederateAgent):
    def __init__(self, config_dict, amr_wind_input, amr_standin_data_file=None, helics_port=None):

        super(AMRWindStandin, self).__init__(
            name=config_dict["name"],
            feeder_num=0,
            starttime=config_dict["starttime"],
            endtime=config_dict["stoptime"],
            agent_num=0,
            config_dict=config_dict,
        )

        self.config_dict = config_dict

        # Read the amrwind input file
        self.amr_wind_input = amr_wind_input
        self.amr_wind_input_dict = read_amr_wind_input(self.amr_wind_input)

        # Get the simulation time step
        self.dt = self.amr_wind_input_dict["dt"]
        self.config_dict["helics"]["deltat"] = self.dt

        # Get the number of turbines
        self.num_turbines = self.amr_wind_input_dict["num_turbines"]

        # Print the number of turbines
        logger.info("Number of turbines: {}".format(self.num_turbines))

        if amr_standin_data_file is not None:
            self.standin_data = pd.read_csv(amr_standin_data_file)

    def run(self):
        # Initialize the values
        turbine_powers = np.zeros(self.num_turbines)
        sim_time_s = 0.0  # initialize time to 0
        sim_time_s = self.absolute_helics_time  # initialize time to 0
        amr_wind_speed = 8.0
        amr_wind_direction = 240.0

        # Before starting the main time loop need to do an initial connection to the
        # Control center to get the starting wind speed and wind direction
        # Code the time step as -1 and -1 (to ensure it is an array)
        logger.info("** First communication with control center")
        # message_from_client_array = [0, -1, -1]
        # Send initial message via helics
        # publish on topic: status
        # self.send_via_helics("status", str(message_from_client_array))
        # logger.info("** Initial Message Sent: {}".format(message_from_client_array))

        # Subscribe to helics messages:
        incoming_messages = self.helics_connector.get_all_waiting_messages()
        if incoming_messages != {}:
            try:
                message_from_server = list(ast.literal_eval(incoming_messages))
            except Exception:
                message_from_server = None
        else:
            message_from_server = None

        # Synchronize time bewteen control center and AMRWind
        self.sync_time_helics(self.absolute_helics_time + self.deltat)
        sim_time_s = float(self.absolute_helics_time)

        logger.info("** Initial Received reply: {}".format(message_from_server))

        logger.info("** Intial Wind Speed: {}".format(amr_wind_speed))
        logger.info("** Intial Wind Direction: {}".format(amr_wind_direction))
        logger.info("...STARTING TIME LOOP...")

        self.message_from_server = None

        while self.absolute_helics_time < (self.endtime - self.starttime + 1):
            # while sim_time_s <= (self.endtime - self.starttime):
            # SIMULATE A CALCULATION STEP IN AMR WIND=========================
            sim_time_s = float(self.absolute_helics_time)
            logger.info("Calculating simulation time: %.3f" % sim_time_s)

            # Compute the turbine power using a simple formula
            if self.message_from_server is not None:
                if len(self.message_from_server) >= 3 + self.num_turbines:
                    yaw_angles = self.message_from_server[3:3 + self.num_turbines]
                else:
                    yaw_angles = None
                if len(self.message_from_server) >= 3 + 2*self.num_turbines:
                    power_setpoints = self.message_from_server[
                        3 + self.num_turbines:3 + 2*self.num_turbines
                    ]
                else:
                    power_setpoints = None
            else:
                yaw_angles = None
                power_setpoints = None
            (
                amr_wind_speed,
                amr_wind_direction,
                turbine_powers,
                turbine_wind_directions,
                turbine_wind_speeds,
            ) = self.get_step(sim_time_s, yaw_angles, power_setpoints)

            # ================================================================
            # Communicate with control center
            # Send the turbine powers for this time step and get wind speed and wind direction for
            # the next time step
            logger.info("Time step: %0.3f" % sim_time_s)
            logger.info("** Communicating with control center")
            message_from_client_array = (
                [
                    sim_time_s,
                    amr_wind_speed,
                    amr_wind_direction,
                ]
                + turbine_powers
                + turbine_wind_directions
                + turbine_wind_speeds
            )

            # Cast all elements as native python float so they can be read in emulator
            message_from_client_array = [float(num) for num in message_from_client_array]

            # Send helics message to Control Center
            # publish on topic: status

            self.send_via_helics("status", str(message_from_client_array))
            logger.info("** Message Sent: {}".format(message_from_client_array))

            # Subscribe to helics messages from control center:
            incoming_messages = self.helics_connector.get_all_waiting_messages()
            if incoming_messages != {}:
                self.message_from_server = list(
                    ast.literal_eval(incoming_messages["control"]["message"])
                )
            else:
                self.message_from_server = None
            #  Now get the wind speed and wind direction back
            if self.message_from_server is not None:
                logger.info("** Received reply {}: {}".format(sim_time_s, self.message_from_server))

                # Note standin doesn't currently use received info for anything

            # Advance simulation time and time step counter
            # sim_time_s += self.dt
            self.sync_time_helics(self.absolute_helics_time + self.deltat)
            print("ABSOLUTE TIME : ", self.absolute_helics_time, self.deltat, self.dt)
            sim_time_s = self.absolute_helics_time

    # TODO cleanup code to move publish and subscribe here.

    def get_step(self, sim_time_s, yaw_angles=None, power_setpoints=None):
        """Retreive or calculate wind speed, direction, and turbine powers

        Input:
        sim_time_s: simulation time step

        Output:
        amr_wind_speed: wind speed at current time step
        amr_wind_direction: wind direction at current time step
        turbine_powers: turbine powers at current time step
        """

        if hasattr(self, "standin_data"):
            amr_wind_speed = np.interp(
                sim_time_s,
                self.standin_data["time"],
                self.standin_data["amr_wind_speed"],
            )
            amr_wind_direction = np.interp(
                sim_time_s,
                self.standin_data["time"],
                self.standin_data["amr_wind_direction"],
            )
            turbine_powers = [
                np.interp(
                    sim_time_s,
                    self.standin_data["time"],
                    self.standin_data[f"turbine_power_{turb}"],
                )
                for turb in range(self.num_turbines)
            ]

            turbine_wind_directions = [0] * self.num_turbines

        else:
            amr_wind_speed = 8.0
            amr_wind_direction = 240.0

            # Compute the turbine power using a simple formula
            turbine_powers = (
                np.ones(self.num_turbines) * amr_wind_speed**3
                + np.random.rand(self.num_turbines) * 50
            )

            # Scale down later turbines as if waked
            turbine_powers[int(self.num_turbines / 2) :] = (
                0.75 * turbine_powers[int(self.num_turbines / 2) :]
            )

            # Convert to a list
            turbine_powers = turbine_powers.tolist()

            turbine_wind_directions = list(
                amr_wind_direction + 5.0 * np.random.randn(self.num_turbines)
            )
            # turbine_wind_directions = [sim_time_s + 0.01, sim_time_s + 0.02]
            turbine_wind_speeds = list(
                amr_wind_speed + 0.5 * np.random.randn(self.num_turbines)
            )

        return (
            amr_wind_speed,
            amr_wind_direction,
            turbine_powers,
            turbine_wind_directions,
            turbine_wind_speeds,
        )

    def process_endpoint_event(self, msg):
        pass

    def process_periodic_endpoint(self):
        pass

    def process_periodic_publication(self):
        # Periodically publish data to the surrpogate
        pass

    def process_subscription_messages(self, msg):
        pass


def launch_amr_wind_standin(amr_input_file, amr_standin_data_file=None, helics_port=None):
    temp = read_amr_wind_input(amr_input_file)

    # Check that helics_port is an integer
    # If helics_port provided update with value
    if helics_port is not None:
        if not isinstance(helics_port, int):
            raise ValueError("helics_port must be an integer.")
        temp["helics_port"] = helics_port


    config = {
        "name": "amr_wind_standin",
        "gridpack": {},
        "helics": {
            "deltat": 0.5,
            "subscription_topics": ["control"],
            "publication_topics": ["status"],
            "endpoints": [],
            "helicsport": temp["helics_port"],
        },
        "publication_interval": 1,
        "endpoint_interval": 1,
        "starttime": 0,
        "stoptime": temp["stop_time"],
        "Agent": "amr_wind_standin",
    }

    if amr_standin_data_file is not None:
        obj = AMRWindStandin(config, amr_input_file, amr_standin_data_file)
    else:
        obj = AMRWindStandin(config, amr_input_file)

    obj.run_helics_setup()
    obj.enter_execution(function_targets=[], function_arguments=[[]])
