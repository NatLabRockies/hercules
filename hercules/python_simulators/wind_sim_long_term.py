# Implements the long run wind model for Hercules.

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from floris import FlorisModel
from hercules.utilities import interpolate_df, load_perffile, load_yaml
from scipy.interpolate import interp1d
from scipy.optimize import minimize_scalar
from scipy.stats import circmean

RPM2RADperSec = 2 * np.pi / 60.0


class WindSimLongTerm:
    def __init__(self, input_dict, dt, starttime, endtime):
        """
        Initializes the WindSimLongTerm class.
        Args:
            input_dict (dict): Dictionary containing input parameters. Must include:
                - "floris_input_file" (str): Path to the FLORIS input file.
                - "wind_input_filename" (str): Path to the wind input file
                    (CSV, pickle, or Feather format).
                - "turbine_file_name" (str): Path to the turbine configuration file.
                Optional keys:
                - "log_file_name" (str): Path to the log file.
                     Defaults to "outputs/log_wind_sim.log".
                - "verbose" (bool): Flag for verbose logging. Defaults to True.
            dt (float): Time step size in seconds.
            starttime (float): Simulation start time.
            endtime (float): Simulation end time.
        """

        # Check if log_file_name is defined in the input_dict
        if "log_file_name" in input_dict:
            self.log_file_name = input_dict["log_file_name"]
        else:
            self.log_file_name = "outputs/log_wind_sim.log"

        # Set up logging
        self.logger = self._setup_logging(self.log_file_name)

        self.logger.info("trying to read in verbose flag")
        if "verbose" in input_dict:
            self.verbose = input_dict["verbose"]
            self.logger.info(f"read in verbose flag = {self.verbose}")
        else:
            self.verbose = True  # default value

        # Define needed inputs as empty dict
        self.needed_inputs = {}

        # Save the time information
        self.dt = dt
        self.starttime = starttime
        self.endtime = endtime

        # Compute the number of time steps
        self.n_steps = int((self.endtime - self.starttime) / self.dt)

        # Track the number of FLORIS calculation
        self.num_floris_calcs = 0

        # Read in the input file names
        self.floris_input_file = input_dict["floris_input_file"]
        self.wind_input_filename = input_dict["wind_input_filename"]
        self.turbine_file_name = input_dict["turbine_file_name"]

        # Read in the weather file data
        # If a csv file is provided, read it in
        if self.wind_input_filename.endswith(".csv"):
            df_wi = pd.read_csv(self.wind_input_filename)
        elif self.wind_input_filename.endswith(".p"):
            df_wi = pd.read_pickle(self.wind_input_filename)
        elif (self.wind_input_filename.endswith(".f")) | (
            self.wind_input_filename.endswith(".ftr")
        ):
            df_wi = pd.read_feather(self.wind_input_filename)
        else:
            raise ValueError("Wind input file must be a .csv or .p file")

        # Make sure the df_wi contains a column called "time"
        if "time" not in df_wi.columns:
            raise ValueError("Wind input file must contain a column called 'time'")

        # Make sure that both starttime and endtime are in the df_wi
        if not (df_wi["time"].min() <= self.starttime <= df_wi["time"].max()):
            raise ValueError(
                f"Start time {self.starttime} is not in the range of the wind input file"
            )
        if not (df_wi["time"].min() <= self.endtime <= df_wi["time"].max()):
            raise ValueError(f"End time {self.endtime} is not in the range of the wind input file")

        # If time_utc is in the file, convert it to a datetime
        if "time_utc" in df_wi.columns:
            df_wi["time_utc"] = pd.to_datetime(df_wi["time_utc"], format="ISO8601", utc=True)

        # Determine the dt implied by the weather file
        self.dt_wi = df_wi["time"][1] - df_wi["time"][0]

        # Log the values
        if self.verbose:
            self.logger.info(f"dt_wi = {self.dt_wi}")
            self.logger.info(f"dt = {self.dt}")

        # Interpolate df_wi on to the time steps
        time_steps_all = np.arange(self.starttime, self.endtime, self.dt)
        df_wi = interpolate_df(df_wi, time_steps_all)

        # FLORIS PREPARATION

        # Initialize the FLORIS model
        self.fmodel = FlorisModel(self.floris_input_file)

        # Change to the simple-derating model turbine
        # (Note this could also be done with the mixed model)
        self.fmodel.set_operation_model("mixed")

        # Get the layout and number of turbines from FLORIS
        self.layout_x = self.fmodel.layout_x
        self.layout_y = self.fmodel.layout_y
        self.n_turbines = self.fmodel.n_turbines

        # TODO Switch this to an input
        self.floris_wd_threshold = 1.0
        self.floris_ws_threshold = 0.5
        self.floris_ti_threshold = 0.01
        self.floris_derating_threshold = 10  # kW

        # TODO Make this settable in the future
        # Establish the width of the FLORIS averaging window
        self.floris_time_window_width_s = 30
        self.floris_time_window_width_steps = int(self.floris_time_window_width_s / self.dt)
        self.floris_time_window_width_steps = max(1, self.floris_time_window_width_steps)

        # How often to update the wake deficits
        self.floris_update_time_s = 10
        self.floris_update_steps = int(self.floris_update_time_s / self.dt)
        self.floris_update_steps = max(1, self.floris_update_steps)

        # Declare the derating buffer to hold previous derating commands
        self.derating_buffer = (
            np.zeros((self.floris_time_window_width_steps, self.n_turbines)) * np.nan
        )
        self.derating_buffer_idx = 0  # Initialize the index to 0

        # Add an initial non-nan value to be over-written on first step
        self.derating_buffer[0, :] = 1e12

        # Convert the wind directions and wind speeds and ti to simply numpy matrices
        # Starting with wind speeds

        self.ws_mat = df_wi[[f"ws_{t_idx:03d}" for t_idx in range(self.n_turbines)]].to_numpy()

        # Compute the turbine averaged wind speeds (axis = 1) using mean
        self.ws_mat_mean = np.mean(self.ws_mat, axis=1)

        self.initial_wind_speeds = self.ws_mat[0, :]
        self.floris_wind_speed = self.ws_mat_mean[0]

        # Now the wind directions
        if "wd_000" in df_wi.columns:
            self.wd_mat = df_wi[[f"wd_{t_idx:03d}" for t_idx in range(self.n_turbines)]].to_numpy()

            # Compute the turbine-averaged wind directions (axis = 1) using circmean
            self.wd_mat_mean = np.apply_along_axis(
                lambda x: circmean(x, high=360.0, low=0.0, nan_policy="omit"),
                axis=1,
                arr=self.wd_mat,
            )

            self.initial_wind_directions = self.wd_mat[0, :]
        elif "wd_mean" in df_wi.columns:
            self.wd_mat_mean = df_wi["wd_mean"].values

        # Compute the initial floris wind direction and wind speed as at the start index
        self.floris_wind_direction = self.wd_mat_mean[0]

        if "ti_000" in df_wi.columns:
            self.ti_mat = df_wi[[f"ti_{t_idx:03d}" for t_idx in range(self.n_turbines)]].to_numpy()

            # Compute the turbine averaged turbulence intensities (axis = 1) using mean
            self.ti_mat_mean = np.mean(self.ti_mat, axis=1)

            self.initial_tis = self.ti_mat[0, :]

            self.floris_ti = self.ti_mat_mean[0]

        else:
            self.ti_mat_mean = 0.08 * np.ones_like(self.ws_mat_mean)
            self.floris_ti = 0.08 * self.ti_mat_mean[0]

        self.floris_derating = np.nanmean(self.derating_buffer, axis=0)

        # Initialize the wake deficits
        self.floris_wake_deficits = np.zeros(self.n_turbines)

        # Get the initial unwaked velocities
        # TODO: This is more a debugging thing, not really necessary
        self.unwaked_velocities = self.ws_mat[0, :]

        # # Compute the initial waked velocities
        self.update_wake_deficits(0)

        # Compute waked velocities
        self.waked_velocities = self.ws_mat[0, :] - self.floris_wake_deficits

        # Get the turbine information
        self.turbine_dict = load_yaml(self.turbine_file_name)
        self.turbine_model_type = self.turbine_dict["turbine_model_type"]

        # Initialize the turbine array
        if self.turbine_model_type == "filter_model":
            self.turbine_array = [
                TurbineFilterModel(
                    self.turbine_dict, self.dt, self.fmodel, self.waked_velocities[t_idx]
                )
                for t_idx in range(self.n_turbines)
            ]
        elif self.turbine_model_type == "dof1_model":
            self.turbine_array = [
                Turbine1dofModel(
                    self.turbine_dict, self.dt, self.fmodel, self.waked_velocities[t_idx]
                )
                for t_idx in range(self.n_turbines)
            ]
        else:
            raise Exception("Turbine model type should be either fileter_model or dof1_model")

        # Initialize the power array to the initial wind speeds
        self.power = np.array(
            [self.turbine_array[t_idx].prev_power for t_idx in range(self.n_turbines)]
        )

        # Update the user
        self.logger.info(f"Initialized WindSimLongTerm with {self.n_turbines} turbines")

    def _setup_logging(self, log_file_name):
        """
        Sets up logging for the wind simulator.

        This method configures a logger named "wind_sim" to log messages to a specified file.
        It ensures the log directory exists, clears any existing handlers to avoid duplicates,
        and formats log messages with timestamps, log levels, and messages.
        Args:
            log_file_name (str): The full path to the log file where log messages will be written.
        Returns:
            logging.Logger: Configured logger instance for the wind simulator.
        """

        # Split the logfile into directory and filename
        log_dir = Path(log_file_name).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Get the logger for wind_sim, note that root logger already in use
        logger = logging.getLogger("wind_sim")
        logger.setLevel(logging.INFO)

        # Clear any existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Add file handler
        file_handler = logging.FileHandler(log_file_name)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(file_handler)

        return logger

    def update_wake_deficits(self, step):
        """
        Updates the wake deficits in the FLORIS model based on the current simulation step.

        This method computes the necessary FLORIS inputs (wind direction, wind speed,
        turbulence intensity, and derating) over a specified time window. If any of these
        inputs have changed beyond their respective thresholds, the FLORIS model is updated,
        and the wake deficits are recalculated.
        Args:
            step (int): The current simulation step.
        """

        # Get the window start
        window_start = max(0, step - self.floris_time_window_width_steps)

        # Compute new values of the floris inputs
        # TODO: CONFIRM THE +1 in the slice is right
        floris_wind_direction = circmean(
            self.wd_mat_mean[window_start : step + 1], high=360.0, low=0.0, nan_policy="omit"
        )
        floris_wind_speed = np.mean(self.ws_mat_mean[window_start : step + 1])
        floris_ti = np.mean(self.ti_mat_mean[window_start : step + 1])

        # Compute the deratings over the same window
        floris_derating = np.nanmean(self.derating_buffer, axis=0)

        # Reshape derating to be 2D with number on axis 1
        floris_derating = floris_derating.reshape(1, -1)

        # If any of the FLORIS inputs have sufficiently changed, update wake deficits
        if (
            np.abs(floris_wind_direction - self.floris_wind_direction) > self.floris_wd_threshold
            or np.abs(floris_wind_speed - self.floris_wind_speed) > self.floris_ws_threshold
            or np.abs(floris_ti - self.floris_ti) > self.floris_ti_threshold
            or np.any(
                np.abs(floris_derating - self.floris_derating) > self.floris_derating_threshold
            )
        ):
            # If verbose
            if self.verbose:
                self.logger.info(
                    "...Updating FLORIS model=========================================="
                )

            # Update the FLORIS inputs
            self.floris_wind_direction = floris_wind_direction
            self.floris_wind_speed = floris_wind_speed
            self.floris_ti = floris_ti
            self.floris_derating = floris_derating

            # Update the FLORIS model
            self.fmodel.set(
                wind_directions=[self.floris_wind_direction],
                wind_speeds=[self.floris_wind_speed],
                turbulence_intensities=[self.floris_ti],
                power_setpoints=1000 * self.floris_derating,
            )
            self.fmodel.run()

            # Compute the deficits
            velocities = self.fmodel.turbine_average_velocities.flatten()
            self.floris_wake_deficits = velocities.max() - velocities

            # Update the number of FLORIS calculations
            self.num_floris_calcs += 1

            if self.verbose:
                self.logger.info(f"Num of FLORIS calculations = {self.num_floris_calcs}")

    def update_derating_buffer(self, derating):
        """
        Updates the derating buffer with the derating values and increments the buffer index.

        This method stores the given derating values in the current position of the derating buffer
        and updates the index to point to the next position in a circular manner.
        Args:
            derating (numpy.ndarray): A 1D array containing the derating values
                 to be stored in the buffer.
        Returns:
            None
        """

        # Update the derating buffer
        self.derating_buffer[self.derating_buffer_idx, :] = derating

        # Increment the index
        self.derating_buffer_idx = (
            self.derating_buffer_idx + 1
        ) % self.floris_time_window_width_steps

    def return_outputs(self):
        return {
            "power": self.power,
            "unwaked_velocity": self.unwaked_velocities,
            "waked_velocity": self.waked_velocities,
            "floris_wind_speed": self.floris_wind_speed,
            "floris_wind_direction": self.floris_wind_direction,
        }

    def step(self, inputs):
        # Get the current  step
        step = inputs["step"]
        if self.verbose:
            self.logger.info(f"step = {step} (of {self.n_steps})")

        # Grab the instantaneous derating signal and update the derating buffer
        derating = np.array(
            [
                inputs["py_sims"]["inputs"][f"derating_{t_idx:03d}"]
                for t_idx in range(self.n_turbines)
            ]
        )
        self.update_derating_buffer(derating)

        # Get the unwaked velocities
        # TODO: This is more a debugging thing, not really necessary
        self.unwaked_velocities = self.ws_mat[step, :]

        # Check if it is time to update the waked velocities
        if step % self.floris_update_steps == 0:
            if self.verbose:
                self.logger.info(".check for floris update...")
            self.update_wake_deficits(step)

        # Compute waked velocities
        self.waked_velocities = self.ws_mat[step, :] - self.floris_wake_deficits

        # Update the turbine powers given the input wind speeds and derating
        self.power = np.array(
            [
                self.turbine_array[t_idx].step(
                    self.waked_velocities[t_idx],
                    derating=derating[t_idx],
                )
                for t_idx in range(self.n_turbines)
            ]
        )

        return self.return_outputs()


class TurbineFilterModel:
    def __init__(self, turbine_dict, dt, fmodel, initial_wind_speed):
        """
        Initializes the turbine filter model
        Args:
            turbine_dict (dict): Dictionary containing turbine configuration,
                including filter model parameters and other turbine-specific data.
            dt (float): Time step for the simulation in seconds.
            fmodel (FLorisModel): FLorisModel of farm
            initial_wind_speed (float): Initial wind speed in m/s to initialize
                the simulation.
        """

        # Save the time step
        self.dt = dt

        # Save the turbine dict
        self.turbine_dict = turbine_dict

        # Save the filter time constant
        self.filter_time_constant = turbine_dict["filter_model"]["time_constant"]

        # Solve for the filter alpha value given dt and the time constant
        self.alpha = self.dt / (self.dt + self.filter_time_constant)

        # Grab the wind speed power curve from the fmodel and define a simple 1D LUT
        turbine_type = fmodel.core.farm.turbine_definitions[0]
        wind_speeds = turbine_type["power_thrust_table"]["wind_speed"]
        powers = turbine_type["power_thrust_table"]["power"]
        self.power_lut = interp1d(
            wind_speeds,
            powers,
            fill_value=0.0,
            bounds_error=False,
        )

        # Initialize the previous power to the initial wind speed
        self.prev_power = self.power_lut(initial_wind_speed)

    def step(self, wind_speed, derating=0.0):
        """
        Simulates a single time step of the wind turbine power output.
        This method calculates the power output of a wind turbine based on the
        given wind speed and an optional derating. The power output is
        smoothed using an exponential moving average to simulate the turbine's
        response to changing wind conditions.
        Args:
            wind_speed (float): The current wind speed in meters per second (m/s).
            derating (float, optional): The maximum allowable power output
        Returns:
            float: The calculated power output of the wind turbine, constrained
            by the derating and smoothed using the exponential moving average.
        """

        # Instantaneous power
        instant_power = self.power_lut(wind_speed)

        # Limit the current power to not be greater then derating
        instant_power = min(instant_power, derating)

        # Limit the instant power to be greater than 0
        instant_power = max(instant_power, 0.0)

        # Update the power
        power = self.alpha * instant_power + (1 - self.alpha) * self.prev_power

        # Limit the power to not be greater then derating
        power = min(power, derating)

        # Limit the power to be greater than 0
        power = max(power, 0.0)

        # Update the previous power
        self.prev_power = power

        # Return the power
        return power


class Turbine1dofModel:
    def __init__(self, turbine_dict, dt, fmodel, initial_wind_speed):
        # Save the time step
        self.dt = dt

        # Save the turbine dict
        self.turbine_dict = turbine_dict

        # Set filter parameter for rotor speed
        self.filteralpha = np.exp(
            -self.dt * self.turbine_dict["dof1_model"]["filterfreq_rotor_speed"]
        )

        # Obtain more data from floris
        turbine_type = fmodel.core.farm.turbine_definitions[0]
        self.rotor_radius = turbine_type["rotor_diameter"] / 2
        self.rotor_area = np.pi * self.rotor_radius**2

        # Save performance data functions
        perffile = turbine_dict["dof1_model"]["cq_table_file"]
        self.perffuncs = load_perffile(perffile)

        self.rho = self.turbine_dict["dof1_model"]["rho"]
        self.max_pitch_rate = self.turbine_dict["dof1_model"]["max_pitch_rate"]
        self.max_torque_rate = self.turbine_dict["dof1_model"]["max_torque_rate"]
        omega0 = self.turbine_dict["dof1_model"]["initial_rpm"] * RPM2RADperSec
        pitch, gentq = self.simplecontroller(initial_wind_speed, omega0)
        tsr = self.rotor_radius * omega0 / initial_wind_speed
        prev_power = (
            self.perffuncs["Cp"]([tsr, pitch])
            * 0.5
            * self.rho
            * self.rotor_area
            * initial_wind_speed**3
        )
        self.prev_power = np.array(prev_power[0] / 1000.0)
        self.prev_omega = omega0
        self.prev_omegaf = omega0
        self.prev_aerotq = (
            0.5
            * self.rho
            * self.rotor_area
            * self.rotor_radius
            * initial_wind_speed**2
            * self.perffuncs["Cq"]([tsr, pitch])
        )
        self.prev_gentq = gentq
        self.prev_pitch = pitch

        pass

    def step(self, wind_speed, derating=0.0):
        omega = (
            self.prev_omega
            + (
                self.prev_aerotq
                - self.prev_gentq * self.turbine_dict["dof1_model"]["gearbox_ratio"]
            )
            * self.dt
            / self.turbine_dict["dof1_model"]["rotor_inertia"]
        )
        omegaf = (1 - self.filteralpha) * omega + self.filteralpha * (self.prev_omegaf)
        # print(omegaf-omega)
        pitch, gentq = self.simplecontroller(wind_speed, omegaf)
        tsr = float(omegaf * self.rotor_radius / wind_speed)
        if derating > 0:
            desiredcp = derating * 1000 / (0.5 * self.rho * self.rotor_area * wind_speed**3)
            optpitch = minimize_scalar(
                lambda p: abs(float(self.perffuncs["Cp"]([tsr, float(p)])) - desiredcp),
                method="bounded",
                bounds=(0, 1.57),
            )
            pitch = optpitch.x

        pitch = np.clip(
            pitch,
            self.prev_pitch - self.max_pitch_rate * self.dt,
            self.prev_pitch + self.max_pitch_rate * self.dt,
        )
        gentq = np.clip(
            gentq,
            self.prev_gentq - self.max_torque_rate * self.dt,
            self.prev_gentq + self.max_torque_rate * self.dt,
        )

        aerotq = (
            0.5
            * self.rho
            * self.rotor_area
            * self.rotor_radius
            * wind_speed**2
            * self.perffuncs["Cq"]([tsr, pitch])
        )

        # power = (
        #     self.perffuncs["Cp"]([tsr, pitch]) * 0.5 * self.rho * self.rotor_area * wind_speed**3
        # )
        power = gentq * omega * self.turbine_dict["dof1_model"]["gearbox_ratio"]

        self.prev_omega = omega
        self.prev_aerotq = aerotq
        self.prev_gentq = gentq
        self.prev_pitch = pitch
        self.prev_omegaf = omegaf
        self.prev_power = power[0] / 1000.0

        return self.prev_power

    def simplecontroller(self, wind_speed, omegaf):
        # if omega <= self.turbine_dict['dof1_model']['rated_wind_speed']:
        pitch = 0.0
        gentorque = self.turbine_dict["dof1_model"]["controller"]["r2_k_torque"] * omegaf**2
        # else
        #     raise Exception("Region-3 controller not implemented yet")
        return pitch, gentorque
