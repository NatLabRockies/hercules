"""Base class for PySAM-based solar simulators."""

import numpy as np
import pandas as pd
from hercules.plant_components.component_base import ComponentBase
from hercules.utilities import (
    hercules_float_type,
    interpolate_df,
)


class SolarPySAMBase(ComponentBase):
    """Base class for PySAM-based solar (PV) simulators.

    Subclasses run a PySAM model, load weather, and apply AC power setpoints. Weather
    handling and stepping live here; model-specific precompute is in the subclass.
    """

    component_category = "generator"

    def __init__(self, h_dict, component_name):
        """Initialize the base solar PySAM simulator.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
            component_name (str): Unique name for this instance (the YAML top-level key).
        """
        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)

        # Load and process solar data
        self._load_solar_data(h_dict)

        # Save the system capacity (in kW - PVWatts DC system capacity)
        self.system_capacity = h_dict[self.component_name]["system_capacity"]

        # Save the initial condition
        self.power = h_dict[self.component_name]["initial_conditions"]["power"]
        self.ac_power_available = h_dict[self.component_name]["initial_conditions"]["power"]
        self.dc_power_available = h_dict[self.component_name]["initial_conditions"]["power"]
        self.dni = h_dict[self.component_name]["initial_conditions"]["dni"]
        self.poa = h_dict[self.component_name]["initial_conditions"]["poa"]
        self.aoi = 0

        # Since using UTC, assume tz is always 0
        self.tz = 0

        self.needed_inputs = {}

    def _load_solar_data(self, h_dict):
        """Load and process solar weather data.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
        """
        # Check that solar_input_filename is provided and not None
        if ("solar_input_filename" not in h_dict[self.component_name]) or (
            h_dict[self.component_name]["solar_input_filename"] is None
        ):
            raise ValueError(f"Must provide solar_input_filename in h_dict[{self.component_name}]")

        # Load solar data from file
        solar_input_filename = h_dict[self.component_name]["solar_input_filename"]
        if solar_input_filename.endswith(".csv"):
            df_solar = pd.read_csv(solar_input_filename)
        elif solar_input_filename.endswith(".p"):
            df_solar = pd.read_pickle(solar_input_filename)
        elif (solar_input_filename.endswith(".f")) | (solar_input_filename.endswith(".ftr")):
            df_solar = pd.read_feather(solar_input_filename)
        elif solar_input_filename.endswith(".parquet"):
            df_solar = pd.read_parquet(solar_input_filename)
        else:
            raise ValueError(f"Unsupported file format for solar input: {solar_input_filename}")

        # Make sure the df_solar contains a column called "time_utc"
        if "time_utc" not in df_solar.columns:
            raise ValueError("Solar input file must contain a column called 'time_utc'")

        # Make sure time_utc is a datetime
        if not pd.api.types.is_datetime64_any_dtype(df_solar["time_utc"]):
            df_solar["time_utc"] = pd.to_datetime(df_solar["time_utc"], format="ISO8601", utc=True)

        # Ensure time_utc is timezone-aware (UTC)
        if not isinstance(df_solar["time_utc"].dtype, pd.DatetimeTZDtype):
            df_solar["time_utc"] = df_solar["time_utc"].dt.tz_localize("UTC")

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
        df_solar["time"] = (df_solar["time_utc"] - starttime_utc).dt.total_seconds()

        # Validate that starttime_utc and endtime_utc are within the time_utc range
        if df_solar["time_utc"].min() > starttime_utc:
            min_time = df_solar["time_utc"].min()
            raise ValueError(
                f"Start time UTC {starttime_utc} is before the earliest time "
                f"in the solar input file ({min_time})"
            )
        if df_solar["time_utc"].max() < endtime_utc:
            max_time = df_solar["time_utc"].max()
            raise ValueError(
                f"End time UTC {endtime_utc} is after the latest time "
                f"in the solar input file ({max_time})"
            )

        # Set starttime_utc (zero_time_utc is redundant since time=0 corresponds to starttime_utc)
        self.starttime_utc = starttime_utc

        # Determine the dt implied by the weather file (after sorting to be safe)
        df_solar = df_solar.sort_values("time").reset_index(drop=True)
        if len(df_solar) < 2:
            raise ValueError(
                "Solar input file must contain at least two rows to infer the native solar timestep"
            )
        self.dt_solar = float(df_solar["time"].iloc[1] - df_solar["time"].iloc[0])

        # Read the use_resource_solar_dt option (default True). When True and the
        # solar file is at a coarser dt than Hercules, PySAM is run on the
        # native-resolution grid and its outputs are upsampled to the Hercules
        # grid via ``_upsample_outputs_to_hercules_dt`` (the av_to_instant
        # happens there instead of on the weather inputs).
        self.use_resource_solar_dt = h_dict[self.component_name].get("use_resource_solar_dt", True)

        # Hercules-grid time steps (used by the upsample helper).
        self._hercules_time_steps = np.arange(
            self.starttime, self.endtime, self.dt, dtype=hercules_float_type
        )

        # Decide the compute (PySAM) grid. In the use_resource_solar_dt case runPySAM
        # at the native dt and upsample its outputs; use native weather-file
        # stamps directly (instead of start + n*dt) so start-of-period averages
        # keep their original interval alignment when starttime_utc is offset
        # from the native reporting boundary. Include one point strictly before
        # starttime and one point at/after endtime when available so the
        # downstream ``averaged_to_instantaneous`` upsample has midpoints on
        # both sides of every Hercules time step (no edge clamping). For
        # i_start we use ``side="left"`` so that when ``starttime`` falls
        # exactly on a native stamp we still pick the previous one; this is a
        # no-op for offsets falling strictly between native stamps and is
        # clamped to 0 when ``starttime`` matches the file's first stamp.
        # In the fallback (compute_dt == dt) the compute grid equals the
        # Hercules grid so downstream array lengths match step indexing
        # exactly, preserving the pre-existing behaviour.
        if self.use_resource_solar_dt and self.dt_solar > self.dt:
            self._compute_dt = self.dt_solar
            native_time = df_solar["time"].to_numpy(dtype=hercules_float_type)
            i_start = max(np.searchsorted(native_time, self.starttime, side="left") - 1, 0)
            i_end = min(
                np.searchsorted(native_time, self.endtime, side="left"), len(native_time) - 1
            )
            self._compute_time_steps = native_time[i_start : i_end + 1]
            interpolation_method = "instantaneous_to_instantaneous"
        else:
            # Else compute at the Hercules dt
            self._compute_dt = self.dt
            self._compute_time_steps = self._hercules_time_steps
            interpolation_method = "averaged_to_instantaneous"

        # Interpolate df_solar onto the compute grid. The method is conditional:
        # in the use_resource_solar_dt case (compute_dt > dt) we keep PVWatts-bound weather
        # in the raw start-of-period averaged convention via ``i_to_i`` and
        # defer the av_to_i to the post-PVWatts upsample. In the
        # fallback (compute_dt == dt) we cross the av_to_i boundary here, exactly as
        # the existing PR #249 path does.
        df_solar = interpolate_df(
            df_solar, self._compute_time_steps, interpolation_method=interpolation_method
        )

        # Can now save the input data as simple columns
        self.year_array = df_solar["time_utc"].dt.year.values
        self.month_array = df_solar["time_utc"].dt.month.values
        self.day_array = df_solar["time_utc"].dt.day.values
        self.hour_array = df_solar["time_utc"].dt.hour.values
        self.minute_array = df_solar["time_utc"].dt.minute.values
        self.ghi_array = self._get_solar_data_array(df_solar, "Global Horizontal Irradiance")
        self.dni_array = self._get_solar_data_array(df_solar, "Direct Normal Irradiance")
        self.dhi_array = self._get_solar_data_array(df_solar, "Diffuse Horizontal Irradiance")
        self.temp_array = self._get_solar_data_array(df_solar, "Temperature")
        self.wind_speed_array = self._get_solar_data_array(df_solar, "Wind Speed at")

    def _get_solar_data_array(self, df_, column_substring):
        """Get the values of the first column in the df whose name contains the specified substring.

        Args:
            df_ (pd.DataFrame): The DataFrame to search for the column.
            column_substring (str): The substring to look for in the column names.

        Returns:
            np.ndarray: The values of the matching column as a NumPy array.
        """
        for column in df_.columns:
            if column_substring in column:
                return df_[column].values
        raise ValueError(f"Could not find column with substring {column_substring} in df_solar")

    def _upsample_outputs_to_hercules_dt(self, output_arrays):
        """Upsample model outputs from the compute dt to the Hercules dt.

        PVWatts is convention-preserving: its outputs are start-of-period
        averaged at the compute-grid stamps, so the single PR #249
        ``"averaged_to_instantaneous"`` boundary crossing happens here. When
        the compute and Hercules grids match (feature off or native_dt <= dt),
        this is a no-op.

        Args:
            output_arrays (dict): Mapping of output name to 1-D array on the
                compute grid (length ``len(self._compute_time_steps)``).

        Returns:
            dict: Same keys, arrays resampled onto ``self._hercules_time_steps``
            and cast to ``hercules_float_type``.
        """
        if self._compute_dt == self.dt:
            return output_arrays
        df = pd.DataFrame({"time": self._compute_time_steps, **output_arrays})
        df_up = interpolate_df(
            df,
            self._hercules_time_steps,
            interpolation_method="averaged_to_instantaneous",
        )
        return {k: df_up[k].values.astype(hercules_float_type) for k in output_arrays}

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Add any initial conditions or meta data to the h_dict.

        Meta data is data not explicitly in the input yaml but still useful for other
        modules.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Dictionary containing simulation parameters with initial conditions and meta data.
        """
        # This is a bit of a hack but need this to exist
        h_dict[self.component_name]["capacity"] = self.system_capacity
        h_dict[self.component_name]["power"] = self.power
        h_dict[self.component_name]["ac_power_available"] = self.ac_power_available
        h_dict[self.component_name]["dc_power_available"] = self.dc_power_available
        h_dict[self.component_name]["dni"] = self.dni
        h_dict[self.component_name]["poa"] = self.poa
        h_dict[self.component_name]["aoi"] = self.aoi

        h_dict[self.component_name]["starttime_utc"] = self.starttime_utc

        return h_dict

    def control(self, power_setpoint):
        """Controls the PV plant power output to meet a specified setpoint.

        This low-level controller enforces AC power setpoints by uniform curtailment
        of ``self.power``. The pre-control AC potential remains in
        ``ac_power_available`` and the pre-inverter DC potential remains in
        ``dc_power_available`` (both exposed in ``h_dict`` after each step).

        Args:
            power_setpoint (float, optional): Desired total PV plant output in kW.

        """
        # modify power output based on setpoint
        if self.verbose:
            self.logger.info(f"power_setpoint = {power_setpoint}")
        if self.power > power_setpoint:
            self.power = power_setpoint
            # Keep track of power that could go to charging battery
            self.excess_power = self.power - power_setpoint
        if self.verbose:
            self.logger.info(f"self.power after control = {self.power}")

    def _update_outputs(self, h_dict):
        """Update the h_dict with outputs.

        ``ac_power_available`` is the post-inverter AC potential (kW) and
        ``dc_power_available`` is the pre-inverter DC potential (kW) for the
        current step. Both are reported before any control-based curtailment.
        ``dc_power_available`` is populated when the subclass precomputes
        ``dc_power_available_array``.

        Args:
            h_dict (dict): Dictionary containing simulation state.
        """
        # Update the h_dict with outputs
        h_dict[self.component_name]["power"] = self.power
        h_dict[self.component_name]["ac_power_available"] = self.ac_power_available
        h_dict[self.component_name]["dc_power_available"] = self.dc_power_available
        h_dict[self.component_name]["dni"] = self.dni
        h_dict[self.component_name]["poa"] = self.poa
        h_dict[self.component_name]["aoi"] = self.aoi

    def _precompute_power_array(self):
        """Pre-compute the full power array for all time steps.

        This method must be implemented by subclasses to handle model-specific
        pre-computation logic.
        """
        raise NotImplementedError("Subclasses must implement _precompute_power_array method")

    def _get_step_outputs(self, step):
        """Get the outputs for a specific step from pre-computed arrays.

        This method must be implemented by subclasses to handle model-specific
        output field names.

        Args:
            step (int): Current simulation step.
        """
        raise NotImplementedError("Subclasses must implement _get_step_outputs method")

    def step(self, h_dict):
        """Execute one simulation step.

        Subclasses must implement _precompute_power_array() and _get_step_outputs().

        Args:
            h_dict (dict): Dictionary containing current simulation state.

        Returns:
            dict: Updated simulation dictionary.
        """
        # Get the current step
        step = h_dict["step"]
        if self.verbose:
            self.logger.info(f"step = {step} (of {self.n_steps})")

        # Get the pre-computed available (pre-control) power for this step (already in kW)
        self.ac_power_available = self.ac_power_available_array[step]
        self.power = self.ac_power_available
        if hasattr(self, "dc_power_available_array"):
            self.dc_power_available = self.dc_power_available_array[step]

        # Apply control
        power_setpoint = h_dict[self.component_name]["power_setpoint"]
        if np.isnan(power_setpoint):
            raise ValueError(f"{self.component_name}: power_setpoint is NaN")
        self.control(power_setpoint)

        if self.power < 0.0:
            self.power = 0.0

        if self.verbose:
            self.logger.info(f"self.power = {self.power}")

        # Get model-specific outputs for this step
        self._get_step_outputs(step)

        if self.verbose:
            self.logger.info(f"self.poa = {self.poa}")

        # Update the h_dict with outputs
        self._update_outputs(h_dict)

        return h_dict
