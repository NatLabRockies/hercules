# Implements the meso-scale wind model for Hercules.


import numpy as np
import pandas as pd
from floris import ApproxFlorisModel
from floris.core import average_velocity
from floris.uncertain_floris_model import map_turbine_powers_uncertain
from hercules.plant_components.component_base import ComponentBase
from hercules.plant_components.wind_meso_to_power import (
    Turbine1dofModel,
    TurbineFilterModelVectorized,
)
from hercules.utilities import (
    hercules_float_type,
    interpolate_df,
    load_yaml,
)
from scipy.interpolate import interp1d
from scipy.stats import circmean

RPM2RADperSec = 2 * np.pi / 60.0


class Wind_MesoToPowerPrecomFloris(ComponentBase):
    def __init__(self, h_dict):
        """Initialize the Wind_MesoToPowerPrecomFloris class.

        This model focuses on meso-scale wind phenomena by applying a separate wind speed
        time signal to each turbine model derived from data. It combines FLORIS wake
        modeling with detailed turbine dynamics for wind farm performance analysis.

        In contrast to the Wind_MesoToPower class, this class pre-computes the FLORIS wake
        deficits for all wind speeds and wind directions. This is done by running FLORIS
        once for all wind speeds and wind directions (but not for varying power setpoints).
        This is valid
        for cases where the wind farm is operating:
            - all turbines operating normally
            - all turbines off
            - following a wind-farm wide derating level

        It is in practice conservative with respect to the wake deficits, but it is more efficient
        than running FLORIS for each condition.  In cases where turbines are:
            - partially derated below the curtailment level
            - not uniformly curtailed or     some turbines are off

        This is not an appropriate model and the more general Wind_MesoToPower class should be used.

        Args:
            h_dict (dict): Dictionary containing values for the simulation.

        Required keys in `h_dict['wind_farm']`:
            - `floris_input_file` (str): Path to FLORIS configuration file.
            - `wind_input_filename` (str): Path to wind input data file.
            - `turbine_file_name` (str): Path to turbine configuration file.
            - `floris_update_time_s` (float): Update period in seconds. This value
              determines the cadence of the wake precomputation. Wind inputs are
              averaged over the most recent `floris_update_time_s` and FLORIS is
              evaluated at that interval. The resulting wake deficits are then held
              constant until the next FLORIS update.
        """
        # Store the name of this component
        self.component_name = "wind_farm"

        # Store the type of this component
        self.component_type = "Wind_MesoToPowerPrecomFloris"

        # Call the base class init
        super().__init__(h_dict, self.component_name)

        self.logger.info("Completed base class init...")

        # Track the number of FLORIS calculations
        self.num_floris_calcs = 0

        self.logger.info("Reading in FLORIS input files...")

        # Read in the input file names
        self.floris_input_file = h_dict[self.component_name]["floris_input_file"]
        self.wind_input_filename = h_dict[self.component_name]["wind_input_filename"]
        self.turbine_file_name = h_dict[self.component_name]["turbine_file_name"]

        # Require floris_update_time_s for interface consistency, though it is unused
        if "floris_update_time_s" not in h_dict[self.component_name]:
            raise ValueError("floris_update_time_s must be in the h_dict")
        self.floris_update_time_s = h_dict[self.component_name]["floris_update_time_s"]
        if self.floris_update_time_s < 1:
            raise ValueError("FLORIS update time must be at least 1 second")
        # Derived step count (not used by this precomputed model, but kept for parity)
        self.floris_update_steps = max(1, int(self.floris_update_time_s / self.dt))

        self.logger.info("Reading in wind input file...")

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

        self.logger.info("Checking wind input file...")

        # Make sure the df_wi contains a column called "time_utc"
        if "time_utc" not in df_wi.columns:
            raise ValueError("Wind input file must contain a column called 'time_utc'")

        # Convert time_utc to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(df_wi["time_utc"]):
            # Strip whitespace from time_utc values to handle CSV formatting issues
            df_wi["time_utc"] = df_wi["time_utc"].astype(str).str.strip()
            try:
                df_wi["time_utc"] = pd.to_datetime(df_wi["time_utc"], format="ISO8601", utc=True)
            except (ValueError, TypeError):
                # If ISO8601 format fails, try parsing without specifying format
                df_wi["time_utc"] = pd.to_datetime(df_wi["time_utc"], utc=True)

        # Ensure time_utc is timezone-aware (UTC)
        if not pd.api.types.is_datetime64tz_dtype(df_wi["time_utc"]):
            df_wi["time_utc"] = df_wi["time_utc"].dt.tz_localize("UTC")

        # Get starttime_utc and endtime_utc from h_dict
        starttime_utc = h_dict["starttime_utc"]
        endtime_utc = h_dict["endtime_utc"]

        # Ensure starttime_utc is timezone-aware (UTC)
        if not isinstance(starttime_utc, pd.Timestamp):
            starttime_utc = pd.to_datetime(starttime_utc, utc=True)
        elif starttime_utc.tz is None:
            starttime_utc = starttime_utc.tz_localize("UTC")

        # Ensure endtime_utc is timezone-aware (UTC)
        if not isinstance(endtime_utc, pd.Timestamp):
            endtime_utc = pd.to_datetime(endtime_utc, utc=True)
        elif endtime_utc.tz is None:
            endtime_utc = endtime_utc.tz_localize("UTC")

        # Generate time column internally: time = 0 corresponds to starttime_utc
        df_wi["time"] = (df_wi["time_utc"] - starttime_utc).dt.total_seconds()

        # Validate that starttime_utc and endtime_utc are within the time_utc range
        if df_wi["time_utc"].min() > starttime_utc:
            min_time = df_wi["time_utc"].min()
            raise ValueError(
                f"Start time UTC {starttime_utc} is before the earliest time "
                f"in the wind input file ({min_time})"
            )
        if df_wi["time_utc"].max() < endtime_utc:
            max_time = df_wi["time_utc"].max()
            raise ValueError(
                f"End time UTC {endtime_utc} is after the latest time "
                f"in the wind input file ({max_time})"
            )

        # Set starttime_utc (zero_time_utc is redundant since time=0 corresponds to starttime_utc)
        self.starttime_utc = starttime_utc

        # Determine the dt implied by the weather file
        self.dt_wi = df_wi["time"][1] - df_wi["time"][0]

        # Log the values
        if self.verbose:
            self.logger.info(f"dt_wi = {self.dt_wi}")
            self.logger.info(f"dt = {self.dt}")

        self.logger.info("Interpolating wind input file...")

        # Interpolate df_wi on to the time steps
        time_steps_all = np.arange(self.starttime, self.endtime, self.dt)
        df_wi = interpolate_df(df_wi, time_steps_all)

        # FLORIS PRECOMPUTATION

        # Initialize the FLORIS model as an ApproxFlorisModel
        self.fmodel = ApproxFlorisModel(
            self.floris_input_file,
            wd_resolution=1.0,
            ws_resolution=1.0,
        )

        # Get the layout and number of turbines from FLORIS
        self.layout_x = self.fmodel.layout_x
        self.layout_y = self.fmodel.layout_y
        self.n_turbines = self.fmodel.n_turbines

        self.logger.info("Converting wind input file to numpy matrices...")

        # Convert the wind directions and wind speeds and ti to simply numpy matrices
        # Starting with wind speed
        # Apply the Hercules float type to the wind speeds
        if "ws_mean" in df_wi.columns and "ws_000" not in df_wi.columns:
            self.ws_mat = np.tile(
                df_wi["ws_mean"].values.astype(hercules_float_type)[:, np.newaxis],
                (1, self.n_turbines),
            )
        else:
            self.ws_mat = df_wi[[f"ws_{t_idx:03d}" for t_idx in range(self.n_turbines)]].to_numpy(
                dtype=hercules_float_type
            )

        # Compute the turbine averaged wind speeds (axis = 1) using mean
        self.ws_mat_mean = np.mean(self.ws_mat, axis=1, dtype=hercules_float_type)

        self.initial_wind_speeds = self.ws_mat[0, :]
        self.wind_speed_mean_background = self.ws_mat_mean[0]

        # For now require "wd_mean" to be in the df_wi
        if "wd_mean" not in df_wi.columns:
            raise ValueError("Wind input file must contain a column called 'wd_mean'")
        self.wd_mat_mean = df_wi["wd_mean"].values.astype(hercules_float_type)

        if "ti_000" in df_wi.columns:
            self.ti_mat = df_wi[[f"ti_{t_idx:03d}" for t_idx in range(self.n_turbines)]].to_numpy(
                dtype=hercules_float_type
            )

            # Compute the turbine averaged turbulence intensities (axis = 1) using mean
            self.ti_mat_mean = np.mean(self.ti_mat, axis=1, dtype=hercules_float_type)

            self.initial_tis = self.ti_mat[0, :]

        else:
            self.ti_mat_mean = 0.08 * np.ones_like(self.ws_mat_mean, dtype=hercules_float_type)

        # Precompute the wake deficits at the cadence specified by floris_update_time_s
        self.logger.info("Precomputing FLORIS wake deficits...")

        # Determine update step cadence and indices to evaluate FLORIS
        update_steps = self.floris_update_steps
        n_steps = len(self.ws_mat_mean)
        eval_indices = np.arange(update_steps - 1, n_steps, update_steps)
        # Ensure at least the final time is evaluated
        if eval_indices.size == 0:
            eval_indices = np.array([n_steps - 1])
        elif eval_indices[-1] != n_steps - 1:
            eval_indices = np.append(eval_indices, n_steps - 1)

        # Build right-aligned windowed means for ws, wd, ti at the evaluation indices
        def window_mean(arr_1d, idx, win):
            start = max(0, idx - win + 1)
            return np.mean(arr_1d[start : idx + 1], dtype=hercules_float_type)

        def window_circmean(arr_1d, idx, win):
            start = max(0, idx - win + 1)
            return circmean(arr_1d[start : idx + 1], high=360.0, low=0.0, nan_policy="omit")

        ws_eval = np.array(
            [window_mean(self.ws_mat_mean, i, update_steps) for i in eval_indices],
            dtype=hercules_float_type,
        )
        wd_eval = np.array(
            [window_circmean(self.wd_mat_mean, i, update_steps) for i in eval_indices],
            dtype=hercules_float_type,
        )
        if np.isscalar(self.ti_mat_mean):
            ti_eval = self.ti_mat_mean * np.ones_like(ws_eval, dtype=hercules_float_type)
        else:
            ti_eval = np.array(
                [window_mean(self.ti_mat_mean, i, update_steps) for i in eval_indices],
                dtype=hercules_float_type,
            )

        # Evaluate FLORIS at the evaluation cadence
        self.fmodel.set(
            wind_directions=wd_eval,
            wind_speeds=ws_eval,
            turbulence_intensities=ti_eval,
        )
        self.logger.info("Running FLORIS...")
        self.fmodel.run()
        self.num_floris_calcs = 1
        self.logger.info("FLORIS run complete")

        # TODO: THIS CODE WILL WORK IN THE FUTURE
        # https://github.com/NREL/floris/pull/1135
        # floris_velocities = (
        #     self.fmodel.turbine_average_velocities
        # )  # This is a 2D array of shape (len(wind_directions), n_turbines)

        # For now compute in place here (replace later)
        expanded_velocities = average_velocity(
            velocities=self.fmodel.fmodel_expanded.core.flow_field.u,
            method=self.fmodel.fmodel_expanded.core.grid.average_method,
            cubature_weights=self.fmodel.fmodel_expanded.core.grid.cubature_weights,
        )

        floris_velocities = map_turbine_powers_uncertain(
            unique_turbine_powers=expanded_velocities,
            map_to_expanded_inputs=self.fmodel.map_to_expanded_inputs,
            weights=self.fmodel.weights,
            n_unexpanded=self.fmodel.n_unexpanded,
            n_sample_points=self.fmodel.n_sample_points,
            n_turbines=self.fmodel.n_turbines,
        ).astype(hercules_float_type)

        # Determine the free_stream velocities as the maximum velocity in each row
        # of floris velocities.  Make sure to keep shape (len(wind_directions), n_turbines)
        # by repeating the maximum velocity accross each column for each row
        free_stream_velocities = np.tile(
            np.max(floris_velocities, axis=1)[:, np.newaxis], (1, self.n_turbines)
        ).astype(hercules_float_type)

        # Compute wake deficits at evaluation times
        floris_wake_deficits_eval = free_stream_velocities - floris_velocities

        # Expand the wake deficits to all time steps by holding constant within each interval
        deficits_all = np.zeros_like(self.ws_mat, dtype=hercules_float_type)
        # For each block, fill with the corresponding deficits
        prev_end = -1
        for block_idx, end_idx in enumerate(eval_indices):
            start_idx = prev_end + 1
            prev_end = end_idx
            # Use deficits from this evaluation time for the whole block
            deficits_all[start_idx : end_idx + 1, :] = floris_wake_deficits_eval[block_idx, :]

        # Compute all the withwakes wind speeds from background minus deficits
        self.wind_speeds_withwakes_all = self.ws_mat - deficits_all

        # Initialize the turbine powers to nan
        self.turbine_powers = np.zeros(self.n_turbines, dtype=hercules_float_type) * np.nan

        # Get the initial background wind speeds
        self.wind_speeds_background = self.ws_mat[0, :]

        # Compute initial withwakes wind speeds
        self.wind_speeds_withwakes = self.wind_speeds_withwakes_all[0, :]

        # Get the initial FLORIS wake deficits
        self.floris_wake_deficits = self.wind_speeds_background - self.wind_speeds_withwakes

        # Get the turbine information
        self.turbine_dict = load_yaml(self.turbine_file_name)
        self.turbine_model_type = self.turbine_dict["turbine_model_type"]

        # Initialize the turbine array
        if self.turbine_model_type == "filter_model":
            # Use vectorized implementation for improved performance
            self.turbine_array = TurbineFilterModelVectorized(
                self.turbine_dict, self.dt, self.fmodel, self.wind_speeds_withwakes
            )
            self.use_vectorized_turbines = True
        elif self.turbine_model_type == "dof1_model":
            self.turbine_array = [
                Turbine1dofModel(
                    self.turbine_dict, self.dt, self.fmodel, self.wind_speeds_withwakes[t_idx]
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
                [self.turbine_array[t_idx].prev_power for t_idx in range(self.n_turbines)],
                dtype=hercules_float_type,
            )

        # Get the rated power of the turbines, for now assume all turbines have the same rated power
        if self.use_vectorized_turbines:
            self.rated_turbine_power = self.turbine_array.get_rated_power()
        else:
            self.rated_turbine_power = self.turbine_array[0].get_rated_power()

        # Get the capacity of the farm
        self.capacity = self.n_turbines * self.rated_turbine_power

        # Update the user
        self.logger.info(
            f"Initialized Wind_MesoToPowerPrecomFloris with {self.n_turbines} turbines"
        )

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
        h_dict["wind_farm"]["wind_direction_mean"] = self.wd_mat_mean[0]
        h_dict["wind_farm"]["wind_speed_mean_background"] = self.ws_mat_mean[0]
        h_dict["wind_farm"]["turbine_powers"] = self.turbine_powers
        h_dict["wind_farm"]["power"] = np.sum(self.turbine_powers)

        # Log the start time UTC if available
        if hasattr(self, "starttime_utc"):
            h_dict["wind_farm"]["starttime_utc"] = self.starttime_utc

        return h_dict

    def step(self, h_dict):
        """Execute one simulation step for the wind farm.

        Calculates turbine powers,
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

        # Update all the wind speeds
        self.wind_speeds_background = self.ws_mat[step, :]
        self.wind_speeds_withwakes = self.wind_speeds_withwakes_all[step, :]
        self.floris_wake_deficits = self.wind_speeds_background - self.wind_speeds_withwakes

        # Update the turbine powers
        if self.use_vectorized_turbines:
            # Vectorized calculation for all turbines at once
            self.turbine_powers = self.turbine_array.step(
                self.wind_speeds_withwakes,
                turbine_power_setpoints,
            )
        else:
            # Original loop-based calculation
            for t_idx in range(self.n_turbines):
                self.turbine_powers[t_idx] = self.turbine_array[t_idx].step(
                    self.wind_speeds_withwakes[t_idx],
                    power_setpoint=turbine_power_setpoints[t_idx],
                )

        # Update instantaneous wind direction and wind speed
        self.wind_direction_mean = self.wd_mat_mean[step]
        self.wind_speed_mean_background = self.ws_mat_mean[step]

        # Update the h_dict with outputs
        h_dict[self.component_name]["power"] = np.sum(self.turbine_powers)
        h_dict[self.component_name]["turbine_powers"] = self.turbine_powers
        h_dict[self.component_name]["turbine_power_setpoints"] = turbine_power_setpoints
        h_dict[self.component_name]["wind_direction_mean"] = self.wind_direction_mean
        h_dict[self.component_name]["wind_speed_mean_background"] = self.wind_speed_mean_background
        h_dict[self.component_name]["wind_speed_mean_withwakes"] = np.mean(
            self.wind_speeds_withwakes, dtype=hercules_float_type
        )
        h_dict[self.component_name]["wind_speeds_withwakes"] = self.wind_speeds_withwakes
        h_dict[self.component_name]["wind_speeds_background"] = self.wind_speeds_background

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
