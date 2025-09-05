# Implements the meso-scale wind model for Hercules.


import numpy as np
import pandas as pd
from floris import FlorisModel
from hercules.plant_components.component_base import ComponentBase
from hercules.utilities import (
    find_time_utc_value,
    hercules_float_type,
    interpolate_df,
    load_perffile,
    load_yaml,
)
from scipy.interpolate import interp1d
from scipy.optimize import minimize_scalar
from scipy.stats import circmean

RPM2RADperSec = 2 * np.pi / 60.0


class Wind_MesoToPower(ComponentBase):
    def __init__(self, h_dict):
        """Initialize the Wind_MesoToPower class.

        This model focuses on meso-scale wind phenomena by applying a separate wind speed
        time signal to each turbine model derived from data. It combines FLORIS wake
        modeling with detailed turbine dynamics for wind farm performance analysis.

        Args:
            h_dict (dict): Dictionary containing values for the simulation.
        """
        # Store the name of this component
        self.component_name = "wind_farm"

        # Store the type of this component
        self.component_type = "Wind_MesoToPower"

        # Call the base class init
        super().__init__(h_dict, self.component_name)

        # Confirm that logging_option is in h_dict[self.component_name]
        if "logging_option" not in h_dict[self.component_name]:
            raise ValueError(f"logging_option must be in the h_dict for {self.component_name}")
        self.logging_option = h_dict[self.component_name]["logging_option"]
        if self.logging_option not in ["base", "turb_subset", "all"]:
            raise ValueError(
                f"logging_option must be one of: base, turb_subset, all for {self.component_name}"
            )

        # Track the number of FLORIS calculations
        self.num_floris_calcs = 0

        # Read in the input file names
        self.floris_input_file = h_dict[self.component_name]["floris_input_file"]
        self.wind_input_filename = h_dict[self.component_name]["wind_input_filename"]
        self.turbine_file_name = h_dict[self.component_name]["turbine_file_name"]

        # Require floris_update_time_s to be in the h_dict
        if "floris_update_time_s" not in h_dict[self.component_name]:
            raise ValueError("floris_update_time_s must be in the h_dict")

        # Save the floris update time and make sure it is at least 1 second
        self.floris_update_time_s = h_dict[self.component_name]["floris_update_time_s"]
        if self.floris_update_time_s < 1:
            raise ValueError("FLORIS update time must be at least 1 second")

        # Read in the weather file data
        # If a csv file is provided, read it in
        if self.wind_input_filename.endswith(".csv"):
            df_wi = pd.read_csv(self.wind_input_filename)
        elif self.wind_input_filename.endswith(".p") | self.wind_input_filename.endswith(".pkl"):
            df_wi = pd.read_pickle(self.wind_input_filename)
        elif (self.wind_input_filename.endswith(".f")) | (
            self.wind_input_filename.endswith(".ftr")
        ):
            df_wi = pd.read_feather(self.wind_input_filename)
        else:
            raise ValueError("Wind input file must be a .csv or .p, .f or .ftr file")

        # Make sure the df_wi contains a column called "time"
        if "time" not in df_wi.columns:
            raise ValueError("Wind input file must contain a column called 'time'")

        # Make sure that both starttime and endtime are in the df_wi
        if not (df_wi["time"].min() <= self.starttime <= df_wi["time"].max()):
            raise ValueError(
                f"Start time {self.starttime} is not in the range of the wind input file"
            )
        if not (df_wi["time"].min() <= self.endtime - self.dt <= df_wi["time"].max()):
            raise ValueError(
                f"End time {self.endtime} - {self.dt} is not in the range of the wind input file"
            )

        # If time_utc is in the file, convert it to a datetime if it's not already
        if "time_utc" in df_wi.columns:
            if not pd.api.types.is_datetime64_any_dtype(df_wi["time_utc"]):
                # Strip whitespace from time_utc values to handle CSV formatting issues
                df_wi["time_utc"] = df_wi["time_utc"].astype(str).str.strip()
                try:
                    df_wi["time_utc"] = pd.to_datetime(
                        df_wi["time_utc"], format="ISO8601", utc=True
                    )
                except (ValueError, TypeError):
                    # If ISO8601 format fails, try parsing without specifying format
                    df_wi["time_utc"] = pd.to_datetime(df_wi["time_utc"], utc=True)

            # Log the value of time_utc that corresponds to time == 0
            self.zero_time_utc = find_time_utc_value(df_wi, 0.0)

            # Log the value of time_utc which corresponds to starttime
            self.start_time_utc = find_time_utc_value(df_wi, self.starttime)

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

        # Set the logging outputs based on the logging_option
        # First add outputs included in every logging option
        self.log_outputs = [
            "power",
            "wind_speed",
            "wind_direction",
            "wind_speed_waked",
        ]

        # If including subset of turbines, add the turbine indices
        if self.logging_option == "turb_subset":
            self.random_turbine_indices = np.random.choice(self.n_turbines, size=3, replace=False)
            self.log_outputs = self.log_outputs + [
                f"waked_velocities_turb_{t_idx:03d}" for t_idx in self.random_turbine_indices
            ]
            self.log_outputs = self.log_outputs + [
                f"turbine_powers_turb_{t_idx:03d}" for t_idx in self.random_turbine_indices
            ]
            self.log_outputs = self.log_outputs + [
                f"turbine_power_setpoints_turb_{t_idx:03d}" for t_idx in self.random_turbine_indices
            ]

        # If including all data add these data points
        elif self.logging_option == "all":
            self.log_outputs = self.log_outputs + [
                "turbine_powers",
                "turbine_power_setpoints",
                "floris_wind_speed",
                "floris_wind_direction",
                "floris_ti",
                "unwaked_velocities",
                "waked_velocities",
            ]

        # How often to update the wake deficits
        self.floris_update_steps = int(self.floris_update_time_s / self.dt)
        self.floris_update_steps = max(1, self.floris_update_steps)

        # Declare the power_setpoint buffer to hold previous power_setpoint commands
        self.turbine_power_setpoints_buffer = (
            np.zeros((self.floris_update_steps, self.n_turbines), dtype=hercules_float_type)
            * np.nan
        )
        self.turbine_power_setpoints_buffer_idx = 0  # Initialize the index to 0

        # Add an initial non-nan value to be over-written on first step
        self.turbine_power_setpoints_buffer[0, :] = 1e12

        # Convert the wind directions and wind speeds and ti to simply numpy matrices
        # Starting with wind speeds

        self.ws_mat = df_wi[[f"ws_{t_idx:03d}" for t_idx in range(self.n_turbines)]].to_numpy(
            dtype=hercules_float_type
        )

        # Compute the turbine averaged wind speeds (axis = 1) using mean
        self.ws_mat_mean = np.mean(self.ws_mat, axis=1, dtype=hercules_float_type)

        self.initial_wind_speeds = self.ws_mat[0, :]
        self.floris_wind_speed = self.ws_mat_mean[0]

        # For now require "wd_mean" to be in the df_wi
        if "wd_mean" not in df_wi.columns:
            raise ValueError("Wind input file must contain a column called 'wd_mean'")
        self.wd_mat_mean = df_wi["wd_mean"].values.astype(hercules_float_type)

        # OLD APPROACH
        # # Now the wind directions
        # if "wd_000" in df_wi.columns:
        #     self.wd_mat = df_wi[
        #         [f"wd_{t_idx:03d}" for t_idx in range(self.n_turbines)]
        #     ].to_numpy()

        #     # Compute the turbine-averaged wind directions (axis = 1) using circmean
        #     self.wd_mat_mean = np.apply_along_axis(
        #         lambda x: circmean(x, high=360.0, low=0.0, nan_policy="omit"),
        #         axis=1,
        #         arr=self.wd_mat,
        #     )

        #     self.initial_wind_directions = self.wd_mat[0, :]
        # elif "wd_mean" in df_wi.columns:
        #     self.wd_mat_mean = df_wi["wd_mean"].values

        # Compute the initial floris wind direction and wind speed as at the start index
        self.floris_wind_direction = self.wd_mat_mean[0]

        if "ti_000" in df_wi.columns:
            self.ti_mat = df_wi[[f"ti_{t_idx:03d}" for t_idx in range(self.n_turbines)]].to_numpy(
                dtype=hercules_float_type
            )

            # Compute the turbine averaged turbulence intensities (axis = 1) using mean
            self.ti_mat_mean = np.mean(self.ti_mat, axis=1, dtype=hercules_float_type)

            self.initial_tis = self.ti_mat[0, :]

            self.floris_ti = self.ti_mat_mean[0]

        else:
            self.ti_mat_mean = 0.08 * np.ones_like(self.ws_mat_mean, dtype=hercules_float_type)
            self.floris_ti = 0.08 * self.ti_mat_mean[0]

        self.floris_turbine_power_setpoints = np.nanmean(
            self.turbine_power_setpoints_buffer, axis=0
        ).astype(hercules_float_type)

        # Initialize the wake deficits
        self.floris_wake_deficits = np.zeros(self.n_turbines, dtype=hercules_float_type)

        # Initialize the turbine powers to nan
        self.turbine_powers = np.zeros(self.n_turbines, dtype=hercules_float_type) * np.nan

        # Get the initial unwaked velocities
        # TODO: This is more a debugging thing, not really necessary
        self.unwaked_velocities = self.ws_mat[0, :]

        # # Compute the initial waked velocities
        self.update_wake_deficits(step=0)

        # Compute waked velocities
        self.waked_velocities = self.ws_mat[0, :] - self.floris_wake_deficits

        # Get the turbine information
        self.turbine_dict = load_yaml(self.turbine_file_name)
        self.turbine_model_type = self.turbine_dict["turbine_model_type"]

        # Initialize the turbine array
        if self.turbine_model_type == "filter_model":
            # Use vectorized implementation for improved performance
            self.turbine_array = TurbineFilterModelVectorized(
                self.turbine_dict, self.dt, self.fmodel, self.waked_velocities
            )
            self.use_vectorized_turbines = True
        elif self.turbine_model_type == "dof1_model":
            self.turbine_array = [
                Turbine1dofModel(
                    self.turbine_dict, self.dt, self.fmodel, self.waked_velocities[t_idx]
                )
                for t_idx in range(self.n_turbines)
            ]
            self.use_vectorized_turbines = False
        else:
            raise Exception("Turbine model type should be either filter_model or dof1_model")

        # Initialize the power array to the initial wind speeds
        if self.use_vectorized_turbines:
            self.turbine_powers = self.turbine_array.prev_powers.copy()
        else:
            self.turbine_powers = np.array(
                [self.turbine_array[t_idx].prev_power for t_idx in range(self.n_turbines)]
            ).astype(hercules_float_type)

        # Get the rated power of the turbines, for now assume all turbines have the same rated power
        if self.use_vectorized_turbines:
            self.rated_turbine_power = self.turbine_array.get_rated_power()
        else:
            self.rated_turbine_power = self.turbine_array[0].get_rated_power()

        # Get the capacity of the farm
        self.capacity = self.n_turbines * self.rated_turbine_power

        # Update the user
        self.logger.info(f"Initialized Wind_MesoToPower with {self.n_turbines} turbines")

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Add any initial conditions or meta data to the h_dict.

        Meta data is data not explicitly in the input yaml but still useful for other
        modules.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Dictionary containing simulation parameters with initial conditions and meta data.
        """
        h_dict["wind_farm"]["n_turbines"] = self.n_turbines
        h_dict["wind_farm"]["capacity"] = self.capacity
        h_dict["wind_farm"]["rated_turbine_power"] = self.rated_turbine_power
        h_dict["wind_farm"]["wind_direction"] = self.wd_mat_mean[0]
        h_dict["wind_farm"]["wind_speed"] = self.ws_mat_mean[0]
        h_dict["wind_farm"]["turbine_powers"] = self.turbine_powers
        h_dict["wind_farm"]["power"] = np.sum(self.turbine_powers)

        # Log the start time UTC if available
        if hasattr(self, "start_time_utc"):
            h_dict["wind_farm"]["start_time_utc"] = self.start_time_utc
        if hasattr(self, "zero_time_utc"):
            h_dict["wind_farm"]["zero_time_utc"] = self.zero_time_utc

        return h_dict

    def update_wake_deficits(self, step):
        """Update the wake deficits in the FLORIS model based on the current simulation step.

        This method computes the necessary FLORIS inputs (wind direction, wind speed,
        turbulence intensity, and power_setpoints) over a specified time window. If any of these
        inputs have changed beyond their respective thresholds, the FLORIS model is updated,
        and the wake deficits are recalculated.

        Args:
            step (int): The current simulation step.
        """
        # Get the window start
        window_start = max(0, step - self.floris_update_steps + 1)

        # Compute new values of the floris inputs
        # TODO: CONFIRM THE +1 in the slice is right
        self.floris_wind_direction = circmean(
            self.wd_mat_mean[window_start : step + 1], high=360.0, low=0.0, nan_policy="omit"
        )
        self.floris_wind_speed = np.mean(
            self.ws_mat_mean[window_start : step + 1], dtype=hercules_float_type
        )
        self.floris_ti = np.mean(
            self.ti_mat_mean[window_start : step + 1], dtype=hercules_float_type
        )

        # Compute the power_setpoints over the same window
        self.floris_turbine_power_setpoints = (
            np.nanmean(self.turbine_power_setpoints_buffer, axis=0)
            .astype(hercules_float_type)
            .reshape(1, -1)
        )

        # Run FLORIS
        self.fmodel.set(
            wind_directions=[self.floris_wind_direction],
            wind_speeds=[self.floris_wind_speed],
            turbulence_intensities=[self.floris_ti],
            power_setpoints=self.floris_turbine_power_setpoints * 1000.0,
        )
        self.fmodel.run()
        velocities = self.fmodel.turbine_average_velocities.flatten()
        self.floris_wake_deficits = velocities.max() - velocities
        self.num_floris_calcs += 1

    def update_power_setpoints_buffer(self, turbine_power_setpoints):
        """Update the power_setpoints buffer with the turbine_power_setpoints values.

        This method stores the given power setpoint values in the current position of the
        power_setpoints buffer and updates the index to point to the next position in a
        circular manner.

        Args:
            turbine_power_setpoints (numpy.ndarray): A 1D array containing the power_setpoint values
                to be stored in the buffer.
        """
        # Update the power_setpoints buffer
        self.turbine_power_setpoints_buffer[self.turbine_power_setpoints_buffer_idx, :] = (
            turbine_power_setpoints
        )

        # Increment the index
        self.turbine_power_setpoints_buffer_idx = (
            self.turbine_power_setpoints_buffer_idx + 1
        ) % self.floris_update_steps

    def step(self, h_dict):
        """Execute one simulation step for the wind farm.

        Updates wake deficits, computes waked velocities, calculates turbine powers,
        and updates the simulation dictionary with results. Handles power_setpoint
        signals and optional extra logging outputs.

        Args:
            h_dict (dict): Dictionary containing current simulation state including
                step number and power_setpoint values for each turbine.

        Returns:
            dict: Updated simulation dictionary with wind farm outputs including
                turbine powers, total power, and optional extra outputs.
        """
        # Get the current step
        step = h_dict["step"]
        if self.verbose:
            self.logger.info(f"step = {step} (of {self.n_steps})")

        # Grab the instantaneous turbine power setpoint signal and update the power_setpoints buffer
        turbine_power_setpoints = h_dict[self.component_name]["turbine_power_setpoints"]
        self.update_power_setpoints_buffer(turbine_power_setpoints)

        # Get the unwaked velocities
        # TODO: This is more a debugging thing, not really necessary
        self.unwaked_velocities = self.ws_mat[step, :]

        # Check if it is time to update the waked velocities
        if step % self.floris_update_steps == 0:
            self.update_wake_deficits(step)

        # Compute waked velocities
        self.waked_velocities = self.ws_mat[step, :] - self.floris_wake_deficits

        # Update the turbine powers
        if self.use_vectorized_turbines:
            # Vectorized calculation for all turbines at once
            self.turbine_powers = self.turbine_array.step(
                self.waked_velocities,
                turbine_power_setpoints,
            )
        else:
            # Original loop-based calculation
            for t_idx in range(self.n_turbines):
                self.turbine_powers[t_idx] = self.turbine_array[t_idx].step(
                    self.waked_velocities[t_idx],
                    power_setpoint=turbine_power_setpoints[t_idx],
                )

        # Update instantaneous wind direction and wind speed
        self.wind_direction = self.wd_mat_mean[step]
        self.wind_speed = self.ws_mat_mean[step]

        # Update the h_dict with outputs
        h_dict[self.component_name]["power"] = np.sum(self.turbine_powers)
        h_dict[self.component_name]["turbine_powers"] = self.turbine_powers
        h_dict[self.component_name]["turbine_power_setpoints"] = turbine_power_setpoints
        h_dict[self.component_name]["wind_direction"] = self.wind_direction
        h_dict[self.component_name]["wind_speed"] = self.wind_speed
        h_dict[self.component_name]["wind_speed_waked"] = np.mean(
            self.waked_velocities, dtype=hercules_float_type
        )

        # If logging_option is "turb_subset", add the turbine indices
        if self.logging_option == "turb_subset":
            for t_idx in self.random_turbine_indices:
                h_dict[self.component_name][f"waked_velocities_turb_{t_idx:03d}"] = (
                    self.waked_velocities[t_idx]
                )
                h_dict[self.component_name][f"turbine_powers_turb_{t_idx:03d}"] = (
                    self.turbine_powers[t_idx]
                )
                h_dict[self.component_name][f"turbine_power_setpoints_turb_{t_idx:03d}"] = (
                    turbine_power_setpoints[t_idx]
                )

        # Else if logging_option is "all", add the turbine powers
        elif self.logging_option == "all":
            h_dict[self.component_name]["floris_wind_speed"] = self.floris_wind_speed
            h_dict[self.component_name]["floris_wind_direction"] = self.floris_wind_direction
            h_dict[self.component_name]["floris_ti"] = self.floris_ti
            h_dict[self.component_name]["floris_turbine_power_setpoints"] = (
                self.floris_turbine_power_setpoints
            )
            h_dict[self.component_name]["unwaked_velocities"] = self.unwaked_velocities
            h_dict[self.component_name]["waked_velocities"] = self.waked_velocities

        return h_dict


class TurbineFilterModel:
    """Simple filter-based wind turbine model for power output simulation.

    This model simulates wind turbine power output using a first-order filter
    to smooth the response to changing wind conditions, providing a simplified
    representation of turbine dynamics.

    NOTE: This class is now unused and kept for backward compatibility.
    The filter_model turbine_model_type now uses TurbineFilterModelVectorized
    for improved performance.
    """

    def __init__(self, turbine_dict, dt, fmodel, initial_wind_speed):
        """Initialize the turbine filter model.

        Args:
            turbine_dict (dict): Dictionary containing turbine configuration,
                including filter model parameters and other turbine-specific data.
            dt (float): Time step for the simulation in seconds.
            fmodel (FlorisModel): FLORIS model of the farm.
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
        self.alpha = 1 - np.exp(-self.dt / self.filter_time_constant)

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

    def get_rated_power(self):
        """Get the rated power of the turbine.

        Returns:
            float: The rated power of the turbine in kW.
        """
        return np.max(self.power_lut(np.arange(0, 25, 1.0, dtype=hercules_float_type)))

    def step(self, wind_speed, power_setpoint):
        """Simulate a single time step of the wind turbine power output.

        This method calculates the power output of a wind turbine based on the
        given wind speed and power_setpoint. The power output is
        smoothed using an exponential moving average to simulate the turbine's
        response to changing wind conditions.

        Args:
            wind_speed (float): The current wind speed in meters per second (m/s).
            power_setpoint (float): The maximum allowable power output in kW.

        Returns:
            float: The calculated power output of the wind turbine, constrained
                by the power_setpoint and smoothed using the exponential moving average.
        """
        # Instantaneous power
        instant_power = self.power_lut(wind_speed)

        # Limit the current power to not be greater than power_setpoint
        instant_power = min(instant_power, power_setpoint)

        # Limit the instant power to be greater than 0
        instant_power = max(instant_power, 0.0)

        # TEMP: why are NaNs occurring?
        if np.isnan(instant_power):
            print(
                f"NaN instant power at wind speed {wind_speed} m/s, "
                f"power setpoint {power_setpoint} kW, prev power {self.prev_power} kW"
            )
            instant_power = self.prev_power

        # Update the power
        power = self.alpha * instant_power + (1 - self.alpha) * self.prev_power

        # Limit the power to not be greater than power_setpoint
        power = min(power, power_setpoint)

        # Limit the power to be greater than 0
        power = max(power, 0.0)

        # Update the previous power
        self.prev_power = power

        # Return the power
        return power


class TurbineFilterModelVectorized:
    """Vectorized filter-based wind turbine model for power output simulation.

    This model simulates wind turbine power output using a first-order filter
    to smooth the response to changing wind conditions, providing a simplified
    representation of turbine dynamics. This vectorized version processes
    all turbines simultaneously for improved performance.
    """

    def __init__(self, turbine_dict, dt, fmodel, initial_wind_speeds):
        """Initialize the vectorized turbine filter model.

        Args:
            turbine_dict (dict): Dictionary containing turbine configuration,
                including filter model parameters and other turbine-specific data.
            dt (float): Time step for the simulation in seconds.
            fmodel (FlorisModel): FLORIS model of the farm.
            initial_wind_speeds (np.ndarray): Initial wind speeds in m/s for all turbines
                to initialize the simulation.
        """
        # Save the time step
        self.dt = dt

        # Save the turbine dict
        self.turbine_dict = turbine_dict

        # Save the filter time constant
        self.filter_time_constant = turbine_dict["filter_model"]["time_constant"]

        # Solve for the filter alpha value given dt and the time constant
        self.alpha = 1 - np.exp(-self.dt / self.filter_time_constant)

        # Grab the wind speed power curve from the fmodel and create lookup tables
        turbine_type = fmodel.core.farm.turbine_definitions[0]
        self.wind_speed_lut = np.array(
            turbine_type["power_thrust_table"]["wind_speed"], dtype=hercules_float_type
        )
        self.power_lut = np.array(
            turbine_type["power_thrust_table"]["power"], dtype=hercules_float_type
        )

        # Number of turbines
        self.n_turbines = len(initial_wind_speeds)

        # Initialize the previous powers for all turbines
        self.prev_powers = np.interp(
            initial_wind_speeds, self.wind_speed_lut, self.power_lut, left=0.0, right=0.0
        ).astype(hercules_float_type)

    def get_rated_power(self):
        """Get the rated power of the turbine.

        Returns:
            float: The rated power of the turbine in kW.
        """
        return np.max(self.power_lut)

    def step(self, wind_speeds, power_setpoints):
        """Simulate a single time step for all wind turbines simultaneously.

        This method calculates the power output of all wind turbines based on the
        given wind speeds and power setpoints. The power outputs are
        smoothed using an exponential moving average to simulate the turbines'
        response to changing wind conditions.

        Args:
            wind_speeds (np.ndarray): Current wind speeds in m/s for all turbines.
            power_setpoints (np.ndarray): Maximum allowable power outputs in kW for all turbines.

        Returns:
            np.ndarray: Calculated power outputs of all wind turbines, constrained
                by the power setpoints and smoothed using the exponential moving average.
        """
        # Vectorized instantaneous power calculation using numpy interpolation
        instant_powers = np.interp(
            wind_speeds, self.wind_speed_lut, self.power_lut, left=0.0, right=0.0
        )

        # Vectorized limiting: current power not greater than power_setpoint
        instant_powers = np.minimum(instant_powers, power_setpoints)

        # Vectorized limiting: instant power not less than 0
        instant_powers = np.maximum(instant_powers, 0.0)

        # Handle NaNs by replacing with previous power values
        nan_mask = np.isnan(instant_powers)
        if np.any(nan_mask):
            # Log warning for NaN values (but don't print every occurrence for performance)
            # Could add logging here if needed
            instant_powers[nan_mask] = self.prev_powers[nan_mask]

        # Vectorized exponential filter update
        powers = self.alpha * instant_powers + (1 - self.alpha) * self.prev_powers

        # Vectorized limiting: power not greater than power_setpoint
        powers = np.minimum(powers, power_setpoints)

        # Vectorized limiting: power not less than 0
        powers = np.maximum(powers, 0.0)

        # Update the previous powers for all turbines
        self.prev_powers = powers.copy()

        # Return the powers
        return powers


class Turbine1dofModel:
    """Single degree-of-freedom wind turbine model with detailed dynamics.

    This model simulates wind turbine behavior using a 1-DOF representation
    that includes rotor dynamics, pitch control, and generator torque control.
    """

    def __init__(self, turbine_dict, dt, fmodel, initial_wind_speed):
        """Initialize the 1-DOF turbine model.

        Args:
            turbine_dict (dict): Dictionary containing turbine configuration and
                DOF model parameters.
            dt (float): Time step for the simulation in seconds.
            fmodel (FlorisModel): FLORIS model of the farm.
            initial_wind_speed (float): Initial wind speed in m/s to initialize
                the simulation.
        """
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
        self.prev_power = np.array(prev_power[0] / 1000.0, dtype=hercules_float_type)
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

    def get_rated_power(self):
        """Get the rated power of the turbine.

        Raises:
            NotImplementedError: 1-DOF turbine model does not have a rated power.
        """
        raise NotImplementedError("1-DOF turbine model does not have a rated power")

    def step(self, wind_speed, power_setpoint):
        """Execute one simulation step for the 1-DOF turbine model.

        Simulates turbine dynamics including rotor speed, pitch angle, and
        generator torque while respecting rate limits and power_setpoint constraints.

        Args:
            wind_speed (float): Current wind speed in m/s.
            power_setpoint (float): Maximum allowable power output in kW.

        Returns:
            float: Calculated turbine power output in kW.
        """
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
        if power_setpoint > 0:
            desiredcp = power_setpoint * 1000 / (0.5 * self.rho * self.rotor_area * wind_speed**3)
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
        """Simple controller for pitch and generator torque.

        Implements a basic Region 2 controller that sets pitch to 0 and
        calculates generator torque based on filtered rotor speed.

        Args:
            wind_speed (float): Current wind speed in m/s.
            omegaf (float): Filtered rotor speed in rad/s.

        Returns:
            tuple: (pitch_angle, generator_torque) where pitch is in radians
                and generator torque is in N⋅m.
        """
        # if omega <= self.turbine_dict['dof1_model']['rated_wind_speed']:
        pitch = 0.0
        gentorque = self.turbine_dict["dof1_model"]["controller"]["r2_k_torque"] * omegaf**2
        # else
        #     raise Exception("Region-3 controller not implemented yet")
        return pitch, gentorque
