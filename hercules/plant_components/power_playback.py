# PowerPlayback is based on WindFarmSCADAPower but models a generic power source
# Note it is limited to playing back the prerecorded power,
# there is no option to control.

import numpy as np
import pandas as pd
from hercules.plant_components.component_base import ComponentBase
from hercules.utilities import (
    hercules_float_type,
    interpolate_df,
)


class PowerPlayback(ComponentBase):
    """Power playback model that plays back pre-recorded power data.
    Note it is limited to playing back the prerecorded power,
    there is no option to control.
    """

    component_category = "generator"

    def __init__(self, h_dict, component_name):
        """Initialize the PowerPlayback class.


        Args:
            h_dict (dict): Dictionary containing simulation parameters.
            component_name (str): Unique name for this instance (the YAML top-level key).
        """
        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)

        self.logger.info("Initializing PowerPlayback")

        # Read in the input file names
        self.scada_filename = h_dict[self.component_name]["scada_filename"]

        self.logger.info("Reading in SCADA power data...")

        # Read in the scada file
        if self.scada_filename.endswith(".csv"):
            df_scada = pd.read_csv(self.scada_filename)
        elif self.scada_filename.endswith((".p", ".pkl")):
            df_scada = pd.read_pickle(self.scada_filename)
        elif self.scada_filename.endswith((".f", ".ftr")):
            df_scada = pd.read_feather(self.scada_filename)
        else:
            raise ValueError("SCADA file must be a .csv, .p, .pkl, .f, or .ftr file")

        self.logger.info("Checking SCADA file...")

        # Make sure the df_scada contains a column called "time_utc"
        if "time_utc" not in df_scada.columns:
            raise ValueError("SCADA file must contain a column called 'time_utc'")

        # Check key columns for Nan values
        nan_check_cols = ["time_utc", "power"]
        if df_scada[nan_check_cols].isna().any().any():
            raise ValueError("SCADA file contains NaN values in required columns (time_utc, power)")

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
        time_steps_all = np.arange(self.starttime, self.endtime, self.dt, dtype=hercules_float_type)
        df_scada = interpolate_df(df_scada, time_steps_all)

        # Confirm that there is a column called "power"
        if "power" not in df_scada.columns:
            raise ValueError("SCADA file must contain a column called 'power'")

        # Collect the scada power
        self.scada_power = df_scada["power"].to_numpy(dtype=hercules_float_type)

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Add any initial conditions or meta data to the h_dict.

        Meta data is data not explicitly in the input yaml but still useful for other
        modules.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Dictionary containing simulation parameters with initial conditions and meta data.
        """
        h_dict[self.component_name]["power"] = self.scada_power[0]

        # Log the start time UTC if available
        if hasattr(self, "starttime_utc"):
            h_dict[self.component_name]["starttime_utc"] = self.starttime_utc

        return h_dict

    def step(self, h_dict):
        """Execute one simulation step for the power playback component.

        Updates power based on the pre-recorded power data.

        Args:
            h_dict (dict): Dictionary containing current simulation state including
                step number

        Returns:
            dict: Updated simulation dictionary with power output.
        """
        # Get the current step
        step = h_dict["step"]
        if self.verbose:
            self.logger.info(f"step = {step} (of {self.n_steps})")

        # Update the power
        self.power = self.scada_power[step]

        # Update the h_dict with outputs
        h_dict[self.component_name]["power"] = self.power

        return h_dict
