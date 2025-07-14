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

import logging
import sys
import warnings
from pathlib import Path

import numpy as np
from floris import FlorisModel
from floris.turbine_library import build_cosine_loss_turbine_dict
from scipy.interpolate import interp1d

from hercules.amr_wind_standin import AMRWindStandin, read_amr_wind_input

# Set up the logger
# Useful for when running on eagle
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
def construct_floris_from_amr_input(amr_wind_input):
    # Probably want a file not found error instead

    with open(amr_wind_input) as fp:
        Lines = fp.readlines()

        # Get the turbine locations
        layout_x = []
        layout_y = []
        for line in Lines:
            if ".base_position" in line:
                loc = [float(d) for d in line.split()[2:]]
                layout_x.append(loc[0])
                layout_y.append(loc[1])

        # Check that uniform disk is specified
        for line in Lines:
            if "Actuator.type" in line:
                acuator_type = line.split()[2]
                if acuator_type == "UniformCtDisk":
                    pass
                else:
                    raise NotImplementedError("FLORIS standin requires UniformCtDisk actuators.")

        # Get the turine parameters
        for line in Lines:
            if acuator_type + ".rotor_diameter" in line:
                rotor_diameter = float(line.split()[2])
        for line in Lines:
            if acuator_type + ".hub_height" in line:
                hub_height = float(line.split()[2])
        for line in Lines:
            if acuator_type + ".density" in line:
                ref_air_density = float(line.split()[2])

        # construct turbine thrust and power curves
        for line in Lines:
            if acuator_type + ".thrust_coeff" in line:
                thrust_coefficient = [float(d) for d in line.split()[2:]]
        for line in Lines:
            if acuator_type + ".wind_speed" in line:
                wind_speed = [float(d) for d in line.split()[2:]]
        # The power curve needs to be constructed from available data
        thrust_coefficient = np.array(thrust_coefficient)
        if (thrust_coefficient < 0).any() or (thrust_coefficient > 1).any():
            print("Clipping thrust_coefficient to (0, 1) interval.")
            thrust_coefficient = np.clip(thrust_coefficient, 0.0, 1.0)
        ai = (1 - np.sqrt(1 - np.array(thrust_coefficient))) / 2
        power_coefficient = 4 * ai * (1 - ai) ** 2
        turbine_data_dict = {
            "wind_speed": wind_speed,
            "thrust_coefficient": thrust_coefficient,
            "power_coefficient": list(power_coefficient),
        }

        # Build the turbine dictionary as expected by FLORIS
        turb_dict = build_cosine_loss_turbine_dict(
            turbine_data_dict=turbine_data_dict,
            turbine_name="FLORIS-standin-turbine",
            hub_height=hub_height,
            rotor_diameter=rotor_diameter,
            ref_air_density=ref_air_density,
            generator_efficiency=1.0,
        )
        turb_dict["operation_model"] = "mixed"

        # load a default model
        fmodel = FlorisModel(default_floris_dict)
        fmodel.set(
            layout_x=layout_x, layout_y=layout_y, turbine_type=[turb_dict] * len(layout_x)
        )

    return fmodel


class FlorisStandin(AMRWindStandin):
    """
    FlorisStandin class, which stands in for AMR-Wind. 
    Arguments:
    config_dict: dictionary of configuration parameters
    amr_input_file: path to the AMR-Wind input file
    amr_standin_data_file [optional]: path to the AMR-Wind standin data file.
        Defaults to None
    smoothing_coefficient [optional]: smoothing coefficient for turbine power
        output. Must be in [0, 1). If 0, no smoothing is applied; if near 1,
        the output is heavily smoothed. Defaults to 0.5.
    """
    def __init__(
            self,
            config_dict,
            amr_input_file,
            amr_standin_data_file=None,
            smoothing_coefficient=0.5
        ):
        """
        Constructor for the FlorisStandin class
        """
        # Ensure outputs folder exists
        Path("outputs").mkdir(parents=True, exist_ok=True)

        super(FlorisStandin, self).__init__(
            config_dict=config_dict,
            amr_wind_input=amr_input_file,
            amr_standin_data_file=amr_standin_data_file,
        )

        # Construct the floris object
        self.fmodel = construct_floris_from_amr_input(amr_input_file)

        # Get the number of turbines
        self.num_turbines = len(self.fmodel.layout_x)

        # Print the number of turbines
        logger.info("Number of turbines: {}".format(self.num_turbines))

        # Initialize storage
        self.yaw_angles_stored = [0.0] * self.num_turbines
        self.turbine_powers_prev = np.zeros(self.num_turbines)

        # Check and save smoothing coefficient
        if smoothing_coefficient < 0 or smoothing_coefficient >= 1:
            raise ValueError("Smoothing coefficient must be in [0, 1).")
        self.smoothing_coefficient = smoothing_coefficient

    def get_step(self, sim_time_s, yaw_angles=None, power_setpoints=None):
        """Retreive or calculate wind speed, direction, and turbine powers

        Input:
        sim_time_s: simulation time step
        yaw_angles: absolute yaw positions for each turbine (deg). Defaults to None.
        power_setpoints: power setpoints for each turbine (W). Defaults to None.

        Output:
        amr_wind_speed: wind speed at current time step [m/s]
        amr_wind_direction: wind direction at current time step [deg]
        turbine_powers: turbine powers at current time step [kW]
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

            if "heterogeneous_inflow_config" in self.standin_data.columns:
                if sim_time_s < self.standin_data["time"].iloc[-1]:
                    next_idx = (
                        self.standin_data["time"][self.standin_data["time"] > sim_time_s].idxmin()
                    )
                else:
                    next_idx = len(self.standin_data) - 1
                prev_idx = next_idx - 1

                prev_dict = eval(self.standin_data["heterogeneous_inflow_config"].iloc[prev_idx])
                next_dict = eval(self.standin_data["heterogeneous_inflow_config"].iloc[next_idx])
                
                heterogeneous_inflow_config = self.interpolate_heterogeneous_inflow_config(
                    prev_dict,
                    next_dict,
                    self.standin_data["time"].iloc[prev_idx],
                    self.standin_data["time"].iloc[next_idx],
                    sim_time_s
                )
            else: # No heterogeneous data supplied
                heterogeneous_inflow_config = None

        else:
            amr_wind_speed = 8.0
            amr_wind_direction = 240.0
            heterogeneous_inflow_config = None

        turbine_wind_directions = [amr_wind_direction] * self.num_turbines

        if power_setpoints is None or yaw_angles is None:
            pass # No conflict with yaw angles
        elif (
            (((np.array(power_setpoints) == 1e9)
              | (np.array([ps is None for ps in power_setpoints])))
            | ((np.array(yaw_angles) == -1000) | (np.array([ya is None for ya in yaw_angles])) |
               (np.array(yaw_angles) == amr_wind_direction))
            ).all()
        ):
            pass # No conflict with yaw angles
        else:
            # Cannot currently handle both power setpoints and nonzero yaw angles. 
            # If power setpoints are provided, overwrite any yaw angles.
            logger.warning((
                "Received combination of power_setpoints and nonzero yaw_angles for some turbines, "
                +"which can not currently be handled by the FlorisStandin. Setting yaw_angles to "
                +"None."
            ))
            yaw_angles = None

        if yaw_angles is None or (np.array(yaw_angles) == -1000).any():
            # Note: -1000 is the "no value" flag for yaw_angles (NaNs not handled well)
            yaw_misalignments = None # Floris will remember the previous yaw angles
        else:
            yaw_misalignments = (amr_wind_direction - np.array(yaw_angles))[
                None, :
            ]  # TODO: remove 2

            if (np.abs(yaw_misalignments) > 45).any():  # Bad yaw angles
                print(
                    (
                        "Large yaw misalignment detected. "
                        + "Wind direction: {0:.2f} deg, ".format(amr_wind_direction)
                        + "Yaw angles: "
                    ),
                    yaw_angles,
                    "Using previous yaw angles.",
                )
                yaw_misalignments = None # Floris will remember the previous yaw angles

        if power_setpoints is not None:
            power_setpoints = np.array(power_setpoints)[None, :]
            # Set invalid power setpoints to a large value
            power_setpoints[power_setpoints == np.full(power_setpoints.shape, None)] = 1e9
            power_setpoints[power_setpoints < 0] = 1e9
            # Note conversion from Watts (used in Floris) and back to kW (used in Hercules)
            power_setpoints = power_setpoints * 1000 # in W

        # Set up and solve FLORIS
        self.fmodel.set(
            wind_speeds=[amr_wind_speed],
            wind_directions=[amr_wind_direction],
            heterogeneous_inflow_config=heterogeneous_inflow_config,
            yaw_angles=yaw_misalignments,
            power_setpoints=power_setpoints
        )
        self.fmodel.run()
        turbine_powers_floris = (self.fmodel.get_turbine_powers() / 1000).flatten()  # in kW
        turbine_wind_speeds = self.fmodel.turbine_average_velocities.flatten()
        turbine_wind_speeds = turbine_wind_speeds.tolist()

        # Smooth output
        turbine_powers = (
            self.smoothing_coefficient*self.turbine_powers_prev
            + (1-self.smoothing_coefficient)*turbine_powers_floris
        )
        self.turbine_powers_prev = turbine_powers
        turbine_powers = turbine_powers.tolist()

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
        # Periodically publish data to the surrogate
        pass

    def process_subscription_messages(self, msg):
        pass

    @staticmethod
    def interpolate_heterogeneous_inflow_config(dict_0, dict_1, time_0, time_1, time):
        # Check for valid keys; if not there, raise warning and return None
        default_dist = 1.0e6
        default_heterogeneous_inflow_config = {
            "x": np.array([-default_dist, -default_dist, default_dist, default_dist]),
            "y": np.array([-default_dist, default_dist, -default_dist, default_dist]),
            "speed_multipliers": np.array([[1.0, 1.0, 1.0, 1.0]]),
        }
        for k in ["x", "y", "speed_multipliers"]:
            if (k not in dict_0.keys()) or (k not in dict_1.keys()):
                warnings.warn((
                    f"Needed key '{k}' missing from heterogeneous_inflow_config."+
                    " Proceeding with homogeneous inflow."
                ))
                return default_heterogeneous_inflow_config
        
        # Check that x and y are the same between time stamps
        # (changing x, y not currently supported)
        if (dict_0["x"] != dict_1["x"]) or (dict_0["y"] != dict_1["y"]):
            warnings.warn((
                "Changing x, y between time stamps not currently supported."+
                " Proceeding with homogeneous inflow."
            ))
            return default_heterogeneous_inflow_config
        
        # Interpolate speed multipliers
        sm_interpolator = interp1d(
            [time_0, time_1],
            [dict_0["speed_multipliers"][0], dict_1["speed_multipliers"][0]],
            axis=0,
        )
        speed_multipliers = sm_interpolator(time)

        # Create return dictionary
        return {
            "x": np.array(dict_0["x"]),
            "y": np.array(dict_0["y"]),
            "speed_multipliers": np.array([speed_multipliers])
        }


def launch_floris(amr_input_file, amr_standin_data_file=None, helics_port=None):
    temp = read_amr_wind_input(amr_input_file)

    # Check amr_standin_data_file is not a number
    if amr_standin_data_file is not None:
        if isinstance(amr_standin_data_file, (int, float)):
            raise ValueError("amr_standin_data_file must be a string or path.")
        
    # Check that helics_port is an integer
    # If helics_port provided update with value
    if helics_port is not None:
        if not isinstance(helics_port, int):
            raise ValueError("helics_port must be an integer.")
        temp["helics_port"] = helics_port

    config = {
        "name": "floris_standin",
        "gridpack": {},
        "helics": {
            "deltat": temp["dt"],
            "subscription_topics": ["control"],
            "publication_topics": ["status"],
            "endpoints": [],
            "helicsport": temp["helics_port"],
        },
        "publication_interval": 1,
        "endpoint_interval": 1,
        "starttime": 0,
        "stoptime": temp["stop_time"],
        "Agent": "floris_standin",
    }

    obj = FlorisStandin(config, amr_input_file, amr_standin_data_file)

    obj.run_helics_setup()
    obj.enter_execution(function_targets=[], function_arguments=[[]])


default_floris_dict = {
    "logging": {
        "console": {"enable": True, "level": "WARNING"},
        "file": {"enable": False, "level": "WARNING"},
    },
    "solver": {"type": "turbine_grid", "turbine_grid_points": 3},
    "wake": {
        "model_strings": {
            "combination_model": "sosfs",
            "deflection_model": "gauss",
            "turbulence_model": "crespo_hernandez",
            "velocity_model": "gauss",
        },
        "enable_secondary_steering": True,
        "enable_yaw_added_recovery": True,
        "enable_transverse_velocities": True,
        "enable_active_wake_mixing": False,
        "wake_deflection_parameters": {
            "gauss": {
                "ad": 0.0,
                "alpha": 0.58,
                "bd": 0.0,
                "beta": 0.077,
                "dm": 1.0,
                "ka": 0.38,
                "kb": 0.004,
            },
            "jimenez": {"ad": 0.0, "bd": 0.0, "kd": 0.05},
        },
        "wake_turbulence_parameters": {
            "crespo_hernandez": {"initial": 0.1, "constant": 0.5, "ai": 0.8, "downstream": -0.32}
        },
        "wake_velocity_parameters": {
            "gauss": {"alpha": 0.58, "beta": 0.077, "ka": 0.38, "kb": 0.004},
            "jensen": {"we": 0.05},
        },
    },
    "farm": {
        "layout_x": [0.0],
        "layout_y": [0.0],
        "turbine_type": ["nrel_5MW"],
    },
    "flow_field": {
        "wind_speeds": [8.0],
        "wind_directions": [270.0],
        "wind_veer": 0.0,
        "wind_shear": 0.12,
        "air_density": 1.225,
        "turbulence_intensities": [0.06],
        "reference_wind_height": 90.0,
    },
    "name": "GCH_for_FlorisStandin",
    "description": "FLORIS Gauss Curl Hybrid model standing in for AMR-Wind",
    "floris_version": "v4.x",
}
