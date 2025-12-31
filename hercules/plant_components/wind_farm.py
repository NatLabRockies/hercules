# Unified wind farm model for Hercules supporting multiple wake modeling strategies.

import numpy as np
import pandas as pd
from floris import ApproxFlorisModel, FlorisModel
from floris.core import average_velocity
from floris.uncertain_floris_model import map_turbine_powers_uncertain
from hercules.plant_components.component_base import ComponentBase
from hercules.utilities import (
    hercules_float_type,
    interpolate_df,
    load_yaml,
)
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import minimize_scalar
from scipy.stats import circmean

RPM2RADperSec = 2 * np.pi / 60.0
RAD2DEG = 180.0 / np.pi


class WindFarm(ComponentBase):
    """Unified wind farm model with configurable wake modeling strategies.

    This model simulates wind farm performance by applying wind speed time signals
    to turbine models. It supports three wake modeling strategies:

    1. **dynamic**: Real-time FLORIS wake calculations at each time step or interval.
       Use when turbines may have individual setpoints or non-uniform operation.

    2. **precomputed**: Pre-computed FLORIS wake deficits for all conditions.
       Use when all turbines operate uniformly (all on, all off, or uniform curtailment).
       More efficient but less flexible than dynamic.

    3. **no_added_wakes**: No wake modeling - wind speeds are used directly.
       Use when wake effects are already included in the input data or when
       wake modeling is not needed.

    All three strategies support detailed turbine dynamics (filter_model or dof1_model).
    """

    def __init__(self, h_dict):
        """Initialize the WindFarm class.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Raises:
            ValueError: If wake_method is invalid or required parameters are missing.
        """
        # Store the name of this component
        self.component_name = "wind_farm"

        # Get the wake_method from h_dict
        wake_method = h_dict[self.component_name].get("wake_method", "dynamic")

        # Validate wake_method
        if wake_method not in ["dynamic", "precomputed", "no_added_wakes"]:
            raise ValueError(
                f"wake_method must be 'dynamic', 'precomputed', or "
                f"'no_added_wakes', got '{wake_method}'"
            )

        self.wake_method = wake_method

        # Store the type of this component (for backward compatibility)
        component_type = h_dict[self.component_name].get("component_type", "WindFarm")
        self.component_type = component_type

        # Call the base class init
        super().__init__(h_dict, self.component_name)

        self.logger.info(f"Initializing WindFarm with wake_method='{self.wake_method}'")

        # Track the number of FLORIS calculations
        self.num_floris_calcs = 0

        # Read in the input file names
        self.floris_input_file = h_dict[self.component_name]["floris_input_file"]
        self.wind_input_filename = h_dict[self.component_name]["wind_input_filename"]
        self.turbine_file_name = h_dict[self.component_name]["turbine_file_name"]

        # Require floris_update_time_s for interface consistency
        # TODO: Why is there a minimum of 1 second?
        # TODO: Consider adding option (e.g. floris_update_time_s = -1) to
        # compute FLORIS at every time step (i.e. floris_update_time_s = dt)
        if wake_method in ["dynamic", "precomputed"]:
            if "floris_update_time_s" not in h_dict[self.component_name]:
                raise ValueError(
                    f"floris_update_time_s must be specified for wake_method='{self.wake_method}'"
                )
            elif h_dict[self.component_name]["floris_update_time_s"] < 1:
                raise ValueError("FLORIS update time must be at least 1 second")
            else:
                self.floris_update_time_s = h_dict[self.component_name]["floris_update_time_s"]
        else:
            self.floris_update_time_s = None

        self.logger.info("Reading in wind input file...")

        # Read in the weather file data
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
        # Convert numeric columns to float32 for memory efficiency
        for col in df_wi.columns:
            if col not in ["time", "time_utc"] and pd.api.types.is_numeric_dtype(df_wi[col]):
                df_wi[col] = df_wi[col].astype(hercules_float_type)

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
        if not isinstance(df_wi["time_utc"].dtype, pd.DatetimeTZDtype):
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

        # Set starttime_utc
        self.starttime_utc = starttime_utc

        # Determine the dt implied by the weather file
        self.dt_wi = df_wi["time"].iloc[1] - df_wi["time"].iloc[0]

        # Log the values
        if self.verbose:
            self.logger.info(f"dt_wi = {self.dt_wi}")
            self.logger.info(f"dt = {self.dt}")

        self.logger.info("Interpolating wind input file...")

        # Interpolate df_wi on to the time steps
        time_steps_all = np.arange(self.starttime, self.endtime, self.dt)
        df_wi = interpolate_df(df_wi, time_steps_all)

        # INITIALIZE FLORIS BASED ON WAKE MODEL
        if self.wake_method == "precomputed":
            self._init_floris_precomputed(df_wi)
        elif self.wake_method == "dynamic":
            self._init_floris_dynamic(df_wi)
        else:  # wake_method == "no_added_wakes"
            self._init_floris_none(df_wi)

        # Common post-FLORIS initialization
        self.logger.info("Initializing turbines...")

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
            raise ValueError("Turbine model type should be either filter_model or dof1_model")

        # Initialize the power array to the initial wind speeds
        if self.use_vectorized_turbines:
            self.turbine_powers = self.turbine_array.prev_powers.copy()
        else:
            self.turbine_powers = np.array(
                [self.turbine_array[t_idx].prev_power for t_idx in range(self.n_turbines)],
                dtype=hercules_float_type,
            )

        # Get the rated power of the turbines
        if self.use_vectorized_turbines:
            self.rated_turbine_power = self.turbine_array.get_rated_power()
        else:
            self.rated_turbine_power = self.turbine_array[0].get_rated_power()

        # Get the capacity of the farm
        self.capacity = self.n_turbines * self.rated_turbine_power

        # Update the user
        self.logger.info(
            f"Initialized WindFarm with {self.n_turbines} turbines "
            f"(wake_method='{self.wake_method}')"
        )

    def _init_floris_precomputed(self, df_wi):
        """Initialize FLORIS with precomputed wake deficits.

        Args:
            df_wi (pd.DataFrame): Interpolated wind input dataframe.
        """
        self.logger.info("Initializing FLORIS (precomputed mode)...")

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

        # Convert the wind directions and wind speeds and ti to numpy matrices
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

        # Derived step count
        self.floris_update_steps = max(1, int(self.floris_update_time_s / self.dt))

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
        # floris_velocities = self.fmodel.turbine_average_velocities

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

    def _init_floris_dynamic(self, df_wi):
        """Initialize FLORIS for dynamic wake calculation.

        Args:
            df_wi (pd.DataFrame): Interpolated wind input dataframe.
        """
        self.logger.info("Initializing FLORIS (dynamic mode)...")

        # Initialize the FLORIS model
        self.fmodel = FlorisModel(self.floris_input_file)

        # Change to the mixed operation model
        self.fmodel.set_operation_model("mixed")

        # Get the layout and number of turbines from FLORIS
        self.layout_x = self.fmodel.layout_x
        self.layout_y = self.fmodel.layout_y
        self.n_turbines = self.fmodel.n_turbines

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

        # Convert the wind directions and wind speeds and ti to numpy matrices
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

        # Compute the initial floris wind direction
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

        # Get the initial background wind speeds
        self.wind_speeds_background = self.ws_mat[0, :]

        # Compute the initial waked wind speeds
        self.update_wake_deficits(step=0)

        # Compute withwakes wind speeds
        self.wind_speeds_withwakes = self.ws_mat[0, :] - self.floris_wake_deficits

    def _init_floris_none(self, df_wi):
        """Initialize without wake modeling.

        Args:
            df_wi (pd.DataFrame): Interpolated wind input dataframe.
        """
        self.logger.info("Initializing FLORIS (no wake modeling)...")

        # Initialize the FLORIS model (still needed for turbine power curve)
        self.fmodel = FlorisModel(self.floris_input_file)

        # Get the layout and number of turbines from FLORIS
        self.layout_x = self.fmodel.layout_x
        self.layout_y = self.fmodel.layout_y
        self.n_turbines = self.fmodel.n_turbines

        # floris_update_steps not used but set for consistency
        # self.floris_update_steps = max(1, int(self.floris_update_time_s / self.dt))

        # Convert the wind directions and wind speeds and ti to numpy matrices
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

        # No wake deficits
        self.floris_wake_deficits = np.zeros(self.n_turbines, dtype=hercules_float_type)

        # Initialize the turbine powers to nan
        self.turbine_powers = np.zeros(self.n_turbines, dtype=hercules_float_type) * np.nan

        # Get the initial background wind speeds
        self.wind_speeds_background = self.ws_mat[0, :]

        # No wakes: withwakes == background
        self.wind_speeds_withwakes = self.wind_speeds_background.copy()

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

    def update_wake_deficits(self, step):
        """Update the wake deficits in the FLORIS model (dynamic mode only).

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

    def _update_power_setpoints_buffer(self, turbine_power_setpoints):
        """Update the power_setpoints buffer (dynamic mode only).

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

        Updates wake deficits (if applicable), computes waked velocities, calculates
        turbine powers, and updates the simulation dictionary with results.

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

        # Grab the instantaneous turbine power setpoint signal
        turbine_power_setpoints = h_dict[self.component_name]["turbine_power_setpoints"]

        # Update wind speeds based on wake model
        if self.wake_method == "dynamic":
            # Update power setpoints buffer
            self._update_power_setpoints_buffer(turbine_power_setpoints)

            # Get the background wind speeds
            self.wind_speeds_background = self.ws_mat[step, :]

            # Check if it is time to update the withwakes wind speeds
            if step % self.floris_update_steps == 0:
                self.update_wake_deficits(step)

            # Compute withwakes wind speeds
            self.wind_speeds_withwakes = self.ws_mat[step, :] - self.floris_wake_deficits

        elif self.wake_method == "precomputed":
            # Update all the wind speeds
            self.wind_speeds_background = self.ws_mat[step, :]
            self.wind_speeds_withwakes = self.wind_speeds_withwakes_all[step, :]
            self.floris_wake_deficits = self.wind_speeds_background - self.wind_speeds_withwakes

        else:  # wake_method == "no_added_wakes"
            # No wake modeling - use background speeds directly
            self.wind_speeds_background = self.ws_mat[step, :]
            self.wind_speeds_withwakes = self.wind_speeds_background.copy()
            self.floris_wake_deficits = np.zeros(self.n_turbines, dtype=hercules_float_type)

        # Update the turbine powers (common for all wake models)
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

        # Obtain required data from turbine_dict
        self.rotor_inertia = self.turbine_dict["dof1_model"]["rotor_inertia"]
        self.rated_rotor_speed = self.turbine_dict["dof1_model"]["rated_rotor_speed"]
        self.rated_torque = self.turbine_dict["dof1_model"]["rated_torque"]
        self.perffile = turbine_dict["dof1_model"]["cq_table_file"]

        # Set default values of optional parameters
        self.rho = self.turbine_dict["dof1_model"].get("rho", 1.225)
        self.filterfreq_rotor_speed = self.turbine_dict["dof1_model"].get(
            "filterfreq_rotor_speed", 1.5708
        )
        self.gearbox_ratio = self.turbine_dict["dof1_model"].get("gearbox_ratio", 1.0)
        self.initial_rpm = self.turbine_dict["dof1_model"].get("initial_rpm", 10)
        self.gen_efficiency = self.turbine_dict["dof1_model"].get("gen_efficiency", 1.0)
        self.max_pitch_rate = self.turbine_dict["dof1_model"].get("max_pitch_rate", np.inf)
        self.max_torque_rate = self.turbine_dict["dof1_model"].get("max_torque_rate", np.inf)

        # Calculate rated power
        self.rated_power = (
            self.rated_torque * self.rated_rotor_speed * self.gearbox_ratio * self.gen_efficiency
        )

        # Set filter parameter for rotor speed
        self.filteralpha = np.exp(
            -self.dt * self.turbine_dict["dof1_model"]["filterfreq_rotor_speed"]
        )

        # Initialize the integrated controller error to 0
        self.omegaferror_integrated = 0.0

        # Obtain more data from floris
        turbine_type = fmodel.core.farm.turbine_definitions[0]
        self.rotor_radius = turbine_type["rotor_diameter"] / 2
        self.rotor_area = np.pi * self.rotor_radius**2

        # Save performance data functions
        perffile = turbine_dict["dof1_model"]["cq_table_file"]
        self.perffuncs = self.load_perffile(perffile)

        self.rho = self.turbine_dict["dof1_model"]["rho"]
        self.max_pitch_rate = self.turbine_dict["dof1_model"]["max_pitch_rate"]
        self.max_torque_rate = self.turbine_dict["dof1_model"]["max_torque_rate"]
        omega0 = self.turbine_dict["dof1_model"]["initial_rpm"] * RPM2RADperSec
        pitch, gentq = self.simplecontroller(omega0)
        tsr = self.rotor_radius * omega0 / initial_wind_speed
        prev_power = (
            self.perffuncs["Cp"]([tsr, pitch])
            * 0.5
            * self.rho
            * self.rotor_area
            * initial_wind_speed**3
            * self.gen_efficiency
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
            * self.perffuncs["Cq"]([tsr, pitch])[0]
        )
        self.prev_gentq = gentq
        self.prev_pitch = pitch

    def get_rated_power(self):
        """Get the rated power of the turbine.

        Returns:
            float: The rated power of the turbine in kW.
        """
        return self.rated_power / 1000

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
            + (self.prev_aerotq - self.prev_gentq * self.gearbox_ratio)
            * self.dt
            / self.rotor_inertia
        )
        omegaf = (1 - self.filteralpha) * omega + self.filteralpha * (self.prev_omegaf)
        pitch, gentq = self.simplecontroller(omegaf)
        tsr = float(omegaf * self.rotor_radius / wind_speed)
        desiredcp = 0
        if power_setpoint < self.rated_power / 1000:
            desiredcp = (
                power_setpoint
                * 1000
                / self.gen_efficiency
                / (0.5 * self.rho * self.rotor_area * wind_speed**3)
            )
            pitch = self.perffuncs["pitch"]([desiredcp, tsr])[0]
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
            * self.perffuncs["Cq"]([tsr, pitch])[0]
        )

        power = gentq * omega * self.gearbox_ratio * self.gen_efficiency

        self.prev_omega = omega
        self.prev_aerotq = aerotq
        self.prev_gentq = gentq
        self.prev_pitch = pitch
        self.prev_omegaf = omegaf
        self.prev_power = power / 1000.0

        return self.prev_power

    def simplecontroller(self, omegaf):
        """Simple controller to command pitch and generator torque.

        Region-2 controller:
        - sets blade pitch to 0
        - sets generator torque using a K$\\omega^2$ controller
        region-3 controller:
        - sets blade pitch based on a PI controller
        - sets generator torque to be inversly proportional to rotor speed.

        Args:
            omegaf (float): Filtered rotor speed in rad/s.

        Returns:
            tuple: (pitch_angle, generator_torque) where pitch is in radians
                and generator torque is in N⋅m.
        """
        omegaf_gen = omegaf * self.gearbox_ratio

        if omegaf >= self.rated_rotor_speed:
            # Region-3
            gentorque = self.rated_torque * self.rated_rotor_speed / omegaf
            self.omegaferror_integrated += omegaf - self.rated_rotor_speed
            pitch_i = (
                self.turbine_dict["dof1_model"]["controller"]["ki_pitch"]
                * self.dt
                * self.omegaferror_integrated
            )
            pitch_p = self.turbine_dict["dof1_model"]["controller"]["kp_pitch"] * (
                omegaf - self.rated_rotor_speed
            )
            pitch = pitch_i + pitch_p
        else:
            # Region-2
            gentorque = self.turbine_dict["dof1_model"]["controller"]["r2_k_torque"] * omegaf_gen**2
            pitch = 0.0
            self.omegaferror_integrated = 0.0
        return pitch, gentorque

    def load_perffile(self, perffile):
        """Load and parse a wind turbine performance file.

        This function reads a performance file containing wind turbine coefficient data
        including power coefficients (Cp), thrust coefficients (Ct), and torque coefficients (Cq)
        as functions of tip speed ratio (TSR) and blade pitch angle.
        It also outputs a function to calculate optimal pitch for a given TSR and reqired Cp
        for faster calculation of derated operations.
        The data is converted into RegularGridInterpolator objects for efficient interpolation
        during simulation.

        Args:
            perffile (str): Path to the performance file containing turbine coefficient data.

        Returns:
            dict: A dictionary containing RegularGridInterpolator objects for 'Cp', 'Ct', and 'Cq'
                coefficients, and optimal pitch for derated cases keyed by coefficient name.
        """
        perffuncs = {}

        with open(perffile) as pfile:
            for line in pfile:
                # Read Blade Pitch Angles (degrees)
                if "Pitch angle" in line:
                    pitch_initial = np.array([float(x) for x in pfile.readline().strip().split()])
                    pitch_initial_rad = pitch_initial / RAD2DEG

                # Read Tip Speed Ratios (rad)
                if "TSR" in line:
                    TSR_initial = np.array([float(x) for x in pfile.readline().strip().split()])

                # Read Power Coefficients
                if "Power" in line:
                    pfile.readline()
                    Cp = np.empty((len(TSR_initial), len(pitch_initial)))
                    for tsr_i in range(len(TSR_initial)):
                        Cp[tsr_i] = np.array([float(x) for x in pfile.readline().strip().split()])
                    perffuncs["Cp"] = RegularGridInterpolator(
                        (TSR_initial, pitch_initial_rad), Cp, bounds_error=False, fill_value=None
                    )

                    # Obtain a lookup table to calculate optimal pitch for derated simulations
                    cpgrid = np.linspace(0, 0.6, 100)
                    optpitchdata = []
                    for cp in cpgrid:
                        optpitchrow = []
                        for tsr in TSR_initial:
                            optpitch = minimize_scalar(
                                lambda p: abs(float(perffuncs["Cp"]([tsr, float(p)])) - cp),
                                method="bounded",
                                bounds=(0, 1.57),
                            )
                            pitch = optpitch.x
                            optpitchrow.append(pitch)
                        optpitchdata.append(optpitchrow)
                    perffuncs["pitch"] = RegularGridInterpolator(
                        (cpgrid, TSR_initial), optpitchdata, bounds_error=False, fill_value=None
                    )

                # Read Thrust Coefficients
                if "Thrust" in line:
                    pfile.readline()
                    Ct = np.empty((len(TSR_initial), len(pitch_initial)))
                    for tsr_i in range(len(TSR_initial)):
                        Ct[tsr_i] = np.array([float(x) for x in pfile.readline().strip().split()])
                    perffuncs["Ct"] = RegularGridInterpolator(
                        (TSR_initial, pitch_initial_rad), Ct, bounds_error=False, fill_value=None
                    )

                # Read Torque Coefficients
                if "Torque" in line:
                    pfile.readline()
                    Cq = np.empty((len(TSR_initial), len(pitch_initial)))
                    for tsr_i in range(len(TSR_initial)):
                        Cq[tsr_i] = np.array([float(x) for x in pfile.readline().strip().split()])
                    perffuncs["Cq"] = RegularGridInterpolator(
                        (TSR_initial, pitch_initial_rad), Cq, bounds_error=False, fill_value=None
                    )

        return perffuncs
