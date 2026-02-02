# Unified wind farm model for Hercules supporting multiple wake modeling strategies.

import numpy as np
import pandas as pd
from hercules.plant_components.component_base import ComponentBase
from hercules.utilities import (
    hercules_float_type,
    interpolate_df,
)


class WindFarmSCADAPower(ComponentBase):
    """Wind farm model that uses SCADA power data to simulate wind farm performance."""

    def __init__(self, h_dict):
        """Initialize the WindFarm class.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
        """
        # Store the name of this component
        self.component_name = "wind_farm"

        self.component_type = "WindFarmSCADAPower"

        # Call the base class init
        super().__init__(h_dict, self.component_name)

        self.logger.info("Initializing WindFarmSCADAPower")

        # Track the number of FLORIS calculations
        self.num_floris_calcs = 0

        # Read in the input file names
        self.scada_filename = h_dict[self.component_name]["scada_filename"]

        self.logger.info("Reading in SCADA power data...")

        # Read in the scada file
        if self.scada_filename.endswith(".csv"):
            df_scada = pd.read_csv(self.scada_filename)
        elif self.scada_filename.endswith(".p") | self.scada_filename.endswith(".pkl"):
            df_scada = pd.read_pickle(self.scada_filename)
        elif (self.scada_filename.endswith(".f")) | (self.scada_filename.endswith(".ftr")):
            df_scada = pd.read_feather(self.scada_filename)
        else:
            raise ValueError("SCADA file must be a .csv or .p, .f or .ftr file")

        self.logger.info("Checking SCADA file...")

        # Make sure the df_scada contains a column called "time_utc"
        if "time_utc" not in df_scada.columns:
            raise ValueError("SCADA file must contain a column called 'time_utc'")

        # Convert time_utc to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(df_scada["time_utc"]):
            # Strip whitespace from time_utc values to handle CSV formatting issues
            df_scada["time_utc"] = df_scada["time_utc"].astype(str).str.strip()
            try:
                df_scada["time_utc"] = pd.to_datetime(
                    df_scada["time_utc"], format="ISO8601", utc=True
                )
            except (ValueError, TypeError):
                # If ISO8601 format fails, try parsing without specifying format
                df_scada["time_utc"] = pd.to_datetime(df_scada["time_utc"], utc=True)

        # Ensure time_utc is timezone-aware (UTC)
        if not isinstance(df_scada["time_utc"].dtype, pd.DatetimeTZDtype):
            df_scada["time_utc"] = df_scada["time_utc"].dt.tz_localize("UTC")

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
        df_scada["time"] = (df_scada["time_utc"] - starttime_utc).dt.total_seconds()

        # Validate that starttime_utc and endtime_utc are within the time_utc range
        if df_scada["time_utc"].min() > starttime_utc:
            min_time = df_scada["time_utc"].min()
            raise ValueError(
                f"Start time UTC {starttime_utc} is before the earliest time "
                f"in the SCADA file ({min_time})"
            )
        if df_scada["time_utc"].max() < endtime_utc:
            max_time = df_scada["time_utc"].max()
            raise ValueError(
                f"End time UTC {endtime_utc} is after the latest time "
                f"in the SCADA file ({max_time})"
            )

        # Set starttime_utc
        self.starttime_utc = starttime_utc

        # Determine the dt implied by the weather file
        self.dt_scada = df_scada["time"].iloc[1] - df_scada["time"].iloc[0]

        # Log the values
        if self.verbose:
            self.logger.info(f"dt_scada = {self.dt_scada}")
            self.logger.info(f"dt = {self.dt}")

        self.logger.info("Interpolating SCADA file...")

        # Interpolate df_scada on to the time steps
        time_steps_all = np.arange(self.starttime, self.endtime, self.dt)
        df_scada = interpolate_df(df_scada, time_steps_all)

        # Get a list of power columns and infer number of turbines
        self.power_columns = sorted([col for col in df_scada.columns if col.startswith("pow_")])

        # Infer the number of turbines by the number of power columns
        self.n_turbines = len(self.power_columns)

        self.logger.info(f"Inferred number of turbines: {self.n_turbines}")

        # Collect the turbine powers
        self.scada_powers = df_scada[self.power_columns].to_numpy(dtype=hercules_float_type)

        # Now get the wind speed and directions

        # Convert the wind directions and wind speeds and ti to numpy matrices
        if "ws_mean" in df_scada.columns and "ws_000" not in df_scada.columns:
            self.ws_mat = np.tile(
                df_scada["ws_mean"].values.astype(hercules_float_type)[:, np.newaxis],
                (1, self.n_turbines),
            )
        else:
            self.ws_mat = df_scada[
                [f"ws_{t_idx:03d}" for t_idx in range(self.n_turbines)]
            ].to_numpy(dtype=hercules_float_type)

        # Compute the turbine averaged wind speeds (axis = 1) using mean
        self.ws_mat_mean = np.mean(self.ws_mat, axis=1, dtype=hercules_float_type)

        self.initial_wind_speeds = self.ws_mat[0, :]
        self.wind_speed_mean_background = self.ws_mat_mean[0]

        # Get the initial background wind speeds
        self.wind_speeds_background = self.ws_mat[0, :]

        # No wakes: withwakes == background
        self.wind_speeds_withwakes = self.wind_speeds_background.copy()

        # For now require "wd_mean" to be in the df_scada
        if "wd_mean" in df_scada.columns:
            self.wd_mat_mean = df_scada["wd_mean"].values.astype(hercules_float_type)
        else:
            # Place holder for wind direction mean
            self.wd_mat_mean = np.zeros(len(df_scada), dtype=hercules_float_type)

        if "ti_000" in df_scada.columns:
            self.ti_mat = df_scada[
                [f"ti_{t_idx:03d}" for t_idx in range(self.n_turbines)]
            ].to_numpy(dtype=hercules_float_type)

            # Compute the turbine averaged turbulence intensities (axis = 1) using mean
            self.ti_mat_mean = np.mean(self.ti_mat, axis=1, dtype=hercules_float_type)

            self.initial_tis = self.ti_mat[0, :]

        else:
            self.ti_mat_mean = 0.08 * np.ones_like(self.ws_mat_mean, dtype=hercules_float_type)

        # No wake deficits
        self.floris_wake_deficits = np.zeros(self.n_turbines, dtype=hercules_float_type)

        # Infer the rated power as the 99 percentile of the power column of 0th turbine
        self.rated_turbine_power = np.percentile(df_scada[self.power_columns[0]], 99)

        # Get the capacity of the farm
        self.capacity = self.n_turbines * self.rated_turbine_power

        self.logger.info(f"Inferred rated turbine power: {self.rated_turbine_power}")
        self.logger.info(f"Inferred capacity: {self.capacity / 1e3} MW")

        # Initialize the turbine array
        self.turbine_array = TurbineUpdateModelVectorizedSCADA(self.dt, self.scada_powers[0, :])

        # Initialize the turbine powers to the starting row
        self.turbine_powers = self.turbine_array.prev_powers.copy()

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

        # No wake modeling - use background speeds directly
        self.wind_speeds_background = self.ws_mat[step, :]
        self.wind_speeds_withwakes = self.wind_speeds_background.copy()
        self.floris_wake_deficits = np.zeros(self.n_turbines, dtype=hercules_float_type)

        # Update the turbine powers (common for all wake models)
        # Vectorized calculation for all turbines at once
        self.turbine_powers = self.turbine_array.step(
            self.scada_powers[step, :],
            turbine_power_setpoints,
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


class TurbineUpdateModelVectorizedSCADA:
    """Vectorized wind turbine update model for power output simulation."""

    def __init__(self, dt, initial_scada_powers):
        """Initialize the vectorized turbine model.

        Args:
            dt (float): Time step for the simulation in seconds.
            initial_scada_powers (np.ndarray): Initial SCADA power values in kW for all turbines
                to initialize the simulation.
        """
        # Save the time step
        self.dt = dt

        # Number of turbines
        self.n_turbines = len(initial_scada_powers)

        # Initialize the previous powers for all turbines
        self.prev_powers = initial_scada_powers.copy()

        print("Filtering not yet implemented for SCADA-based turbine model. Use with caution.")

    def step(self, scada_powers, power_setpoints):
        """Simulate a single time step for all wind turbines simultaneously.

        This method calculates the power output of all wind turbines based on the
        given wind speeds and power setpoints.

        Args:
            scada_powers (np.ndarray): Current SCADA powers for all turbines.
            power_setpoints (np.ndarray): Maximum allowable power outputs in kW for all turbines.

        Returns:
            np.ndarray: Calculated power outputs of all wind turbines, constrained
                by the power setpoints.
        """

        # Vectorized limiting: current power not greater than power_setpoint
        instant_powers = np.minimum(scada_powers, power_setpoints)

        # Vectorized limiting: instant power not less than 0
        instant_powers = np.maximum(instant_powers, 0.0)

        # Handle NaNs by replacing with previous power values
        nan_mask = np.isnan(instant_powers)
        if np.any(nan_mask):
            instant_powers[nan_mask] = self.prev_powers[nan_mask]

        # Simple update without any filtering
        powers = instant_powers

        # Vectorized limiting: power not greater than power_setpoint
        powers = np.minimum(powers, power_setpoints)

        # Vectorized limiting: power not less than 0
        powers = np.maximum(powers, 0.0)

        # Update the previous powers for all turbines
        self.prev_powers = powers.copy()

        # Return the powers
        return powers
