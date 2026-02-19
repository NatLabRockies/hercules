"""Base class for PySAM-based solar simulators."""

import numpy as np
import pandas as pd
from hercules.plant_components.component_base import ComponentBase
from hercules.utilities import (
    hercules_float_type,
    interpolate_df,
)


class SolarPySAMBase(ComponentBase):
    """Base class for PySAM-based solar simulators.

    This class provides common functionality for both PVSam and PVWatts models,
    including weather data processing, solar resource assignment, and control logic.

    Note PVSam is no longer supported in Hercules.
    """

    def __init__(self, h_dict):
        """Initialize the base solar PySAM simulator.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
        """
        # Store the name of this component
        self.component_name = "solar_farm"

        # Call the base class init
        super().__init__(h_dict, self.component_name)

        # Load and process solar data
        self._load_solar_data(h_dict)

        # Save the system capacity (in kW - PVWatts DC system capacity)
        self.system_capacity = h_dict[self.component_name]["system_capacity"]

        # Save the target dc/ac ratio (Force to 1.0)
        self.target_dc_ac_ratio = 1.0

        # Save the initial condition
        self.power = h_dict[self.component_name]["initial_conditions"]["power"]
        self.dc_power = h_dict[self.component_name]["initial_conditions"]["power"]
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

        # Interpolate df_solar on to the time steps
        time_steps_all = np.arange(self.starttime, self.endtime, self.dt, dtype=hercules_float_type)
        df_solar = interpolate_df(df_solar, time_steps_all)

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
        h_dict["solar_farm"]["capacity"] = self.system_capacity
        h_dict["solar_farm"]["power"] = self.power
        h_dict["solar_farm"]["dc_power"] = self.dc_power
        h_dict["solar_farm"]["dni"] = self.dni
        h_dict["solar_farm"]["poa"] = self.poa
        h_dict["solar_farm"]["aoi"] = self.aoi

        # Log the start time UTC if available
        if hasattr(self, "starttime_utc"):
            h_dict["solar_farm"]["starttime_utc"] = self.starttime_utc

        return h_dict

    def control(self, power_setpoint):
        """Controls the PV plant power output to meet a specified setpoint.

        This low-level controller enforces power setpoints for the PV plant by
        applying uniform curtailment across the entire plant. Note that DC power
        output is not controlled as it is not utilized elsewhere in the code.

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

        Args:
            h_dict (dict): Dictionary containing simulation state.
        """
        # Update the h_dict with outputs
        h_dict[self.component_name]["power"] = self.power
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

        This is the common step implementation that works for both PVWatts and PVSAM.
        Subclasses only need to implement _precompute_power_array() and _get_step_outputs().

        Args:
            h_dict (dict): Dictionary containing current simulation state.

        Returns:
            dict: Updated simulation dictionary.
        """
        # Get the current step
        step = h_dict["step"]
        if self.verbose:
            self.logger.info(f"step = {step} (of {self.n_steps})")

        # Get the pre-computed uncurtailed power for this step (already in kW)
        self.power = self.power_uncurtailed[step]

        # Apply control
        self.control(h_dict[self.component_name]["power_setpoint"])

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
