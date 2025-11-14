import logging
import os
import re
import warnings
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import polars as pl
import yaml
from scipy.interpolate import interp1d, RegularGridInterpolator

# Hercules float type for consistent precision
hercules_float_type = np.float32


def get_available_component_names():
    """Return available component names.

    Returns:
        list: Available plant component names.
    """
    return [
        "wind_farm",
        "solar_farm",
        "battery",
        "electrolyzer",
    ]


def get_available_generator_names():
    """Return available generator component names.

    Returns power generators (wind_farm, solar_farm), excluding storage and conversion
    components.

    Returns:
        list: Available generator component names.
    """
    return [
        "wind_farm",
        "solar_farm",
    ]


def get_available_component_types():
    """Return available component types by component.

    Returns:
        dict: Component names mapped to available simulation types.
    """
    return {
        "wind_farm": ["Wind_MesoToPower", "Wind_MesoToPowerPrecomFloris"],
        "solar_farm": ["SolarPySAMPVWatts"],
        "battery": ["BatterySimple", "BatteryLithiumIon"],
        "electrolyzer": ["ElectrolyzerPlant"],
    }


class Loader(yaml.SafeLoader):
    """Custom YAML loader supporting !include tags.

    Extends yaml.SafeLoader to include other YAML files within a main YAML file.
    """

    def __init__(self, stream):
        """Initialize Loader with stream.

        Args:
            stream: YAML stream to load from.
        """
        self._root = os.path.split(stream.name)[0]

        super().__init__(stream)

    def include(self, node):
        """Include another YAML file at current location.

        Args:
            node: YAML node containing filename to include.

        Returns:
            dict: Parsed YAML content from included file.
        """
        filename = os.path.join(self._root, self.construct_scalar(node))

        with open(filename, "r") as f:
            return yaml.load(f, self.__class__)


Loader.add_constructor("!include", Loader.include)


def load_yaml(filename, loader=Loader):
    """Load and parse YAML file into dictionary.

    Supports custom YAML tags like !include. If filename is already a dict, returns it unchanged.

    Args:
        filename (Union[str, dict]): Path to YAML file or existing dictionary.
        loader (yaml.Loader, optional): YAML loader class. Defaults to custom Loader.

    Returns:
        dict: Parsed YAML data.
    """
    if isinstance(filename, dict):
        return filename  # filename already yaml dict
    with open(filename) as fid:
        return yaml.load(fid, loader)


def _validate_utc_datetime_string(dt_str, field_name):
    """Validate that a datetime string represents UTC time.

    Accepts:
    - Strings ending with "Z" (explicit UTC in ISO 8601 format)
    - Naive strings with no timezone info (treated as UTC)

    Rejects:
    - Strings with timezone offsets (e.g., "+05:00", "-08:00")

    Args:
        dt_str (str): Datetime string to validate.
        field_name (str): Name of the field being validated (for error messages).

    Returns:
        pd.Timestamp: UTC-aware timestamp.

    Raises:
        ValueError: If string contains timezone offset or is invalid.
    """
    if not isinstance(dt_str, str):
        raise ValueError(f"{field_name} must be a string")

    dt_str_stripped = dt_str.strip()

    # Check for timezone offsets (not allowed since field name implies UTC)
    # Timezone offsets come after 'T' or at the end
    # Pattern matches timezone offsets like +05:00, -08:00, +05:30, etc.
    tz_offset_pattern = r"[+-]\d{2}:\d{2}$|[T][\d:-]*[+-]\d{2}:\d{2}"
    if re.search(tz_offset_pattern, dt_str_stripped):
        raise ValueError(
            f"{field_name} contains a timezone offset (e.g., +05:00, -08:00). "
            f"Since the field is named '{field_name}', it must be UTC time. "
            f"Use 'Z' to explicitly mark UTC (e.g., '2020-01-01T00:00:00Z') "
            f"or use a naive string without timezone info."
        )

    # Parse with utc=True to ensure result is UTC
    try:
        return pd.to_datetime(dt_str, utc=True)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"{field_name} must be a valid UTC datetime string in ISO 8601 format. "
            f"Accepted formats: 'YYYY-MM-DDTHH:MM:SSZ' (with Z) or "
            f"'YYYY-MM-DDTHH:MM:SS' (naive, treated as UTC). Error: {e}"
        )


def local_time_to_utc(local_time, tz):
    """Convert local time to UTC time string in ISO 8601 format with Z suffix.

    This utility helps users who only know their local time convert it to UTC,
    accounting for daylight saving time automatically. Useful for users less
    familiar with timezones who need to provide UTC timestamps for Hercules
    input files.

    Args:
        local_time (str or pd.Timestamp): Local datetime string or pandas Timestamp.
            Accepts formats like "2025-01-01T00:00:00" or "2025-07-01 00:00:00".
        tz (str): Timezone string using IANA timezone names (e.g., "America/Denver",
            "America/New_York", "Europe/London", "Asia/Tokyo"). Required parameter.

    Returns:
        str: UTC datetime string in ISO 8601 format with Z suffix (e.g.,
            "2025-01-01T07:00:00Z").

    Examples:
        >>> # Midnight Jan 1, 2025 in Mountain Time (MST, UTC-7, no DST)
        >>> local_time_to_utc("2025-01-01T00:00:00", tz="America/Denver")
        '2025-01-01T07:00:00Z'
        >>> # Midnight July 1, 2025 in Mountain Time (MDT, UTC-6, DST in effect)
        >>> local_time_to_utc("2025-07-01T00:00:00", tz="America/Denver")
        '2025-07-01T06:00:00Z'
        >>> # Eastern Time example
        >>> local_time_to_utc("2025-01-01T00:00:00", tz="America/New_York")
        '2025-01-01T05:00:00Z'

    Raises:
        ValueError: If local_time cannot be parsed or tz is invalid or missing.

    Note:
        Common timezone names:
        - US: "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"
        - Europe: "Europe/London", "Europe/Paris", "Europe/Berlin"
        - Asia: "Asia/Tokyo", "Asia/Shanghai", "Asia/Dubai"
        - Pacific: "Pacific/Auckland", "Pacific/Honolulu"

        For a complete list of all available IANA timezone names, see:
        - https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
        - Or in Python: `import zoneinfo; zoneinfo.available_timezones()`
    """
    if tz is None:
        raise ValueError(
            "Timezone parameter 'tz' is required. "
            "Use IANA timezone names like 'America/Denver' or 'Europe/London'. "
            "See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for valid names."
        )

    # Parse local_time to pandas Timestamp (naive)
    try:
        dt = pd.to_datetime(local_time)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot parse local_time '{local_time}': {e}")

    # Localize naive datetime to the specified timezone
    try:
        dt_localized = dt.tz_localize(tz)
    except Exception as e:
        raise ValueError(
            f"Invalid timezone '{tz}': {e}. "
            "Use IANA timezone names like 'America/Denver' or 'Europe/London'. "
            "See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for valid names, "
            "or in Python: `import zoneinfo; zoneinfo.available_timezones()`"
        )

    # Convert to UTC
    dt_utc = dt_localized.tz_convert("UTC")

    # Format as ISO 8601 with Z suffix
    # Remove timezone info and add Z manually to match Hercules format
    utc_str = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    return utc_str


def load_hercules_input(filename):
    """Load and validate Hercules input file.

    Loads YAML file and validates input structure, required keys, and data types.

    Args:
        filename (str): Path to Hercules input YAML file.

    Returns:
        dict: Validated Hercules input configuration with computed starttime/endtime.

    Raises:
        ValueError: If required keys missing, invalid data types, or incorrect structure.
    """
    h_dict = load_yaml(filename)

    # Define valid keys
    required_keys = ["dt", "starttime_utc", "endtime_utc", "plant"]
    component_names = get_available_component_names()
    component_types = get_available_component_types()
    other_keys = [
        "name",
        "description",
        "controller",
        "verbose",
        "output_file",
        "log_every_n",
        "external_data_file",
        "external_data",
        "output_use_compression",
        "output_buffer_size",
    ]

    # Validate required keys
    for key in required_keys:
        if key not in h_dict:
            raise ValueError(f"Required key {key} not found in input file {filename}")

    # Validate and convert starttime_utc and endtime_utc to pandas Timestamps
    # If they're already Timestamps (e.g., from test h_dicts), use them directly
    if isinstance(h_dict["starttime_utc"], pd.Timestamp):
        starttime_utc = h_dict["starttime_utc"]
    else:
        starttime_utc = _validate_utc_datetime_string(h_dict["starttime_utc"], "starttime_utc")

    if isinstance(h_dict["endtime_utc"], pd.Timestamp):
        endtime_utc = h_dict["endtime_utc"]
    else:
        endtime_utc = _validate_utc_datetime_string(h_dict["endtime_utc"], "endtime_utc")

    # Validate endtime_utc is after starttime_utc
    if endtime_utc <= starttime_utc:
        raise ValueError(f"endtime_utc must be after starttime_utc in input file {filename}")

    # Store UTC timestamps in h_dict
    h_dict["starttime_utc"] = starttime_utc
    h_dict["endtime_utc"] = endtime_utc

    # Validate plant structure
    if not isinstance(h_dict["plant"], dict):
        raise ValueError(f"Plant must be a dictionary in input file {filename}")

    if "interconnect_limit" not in h_dict["plant"]:
        raise ValueError(f"Plant must contain an interconnect_limit key in input file {filename}")

    if not isinstance(h_dict["plant"]["interconnect_limit"], (float, int)):
        raise ValueError(f"Interconnect limit must be a float in input file {filename}")

    # Validate all keys are valid
    for key in h_dict:
        if key not in required_keys + component_names + other_keys:
            raise ValueError(f'Key "{key}" not a valid key in input file {filename}')

    # Disallow pre-defined start/end; derive from UTC + dt policy
    if ("starttime" in h_dict) or ("endtime" in h_dict):
        raise ValueError("starttime/endtime must not be provided; they are derived from *_utc")

    # Validate component structures
    for key in component_names:
        if key in h_dict:
            if not isinstance(h_dict[key], dict):
                raise ValueError(f"{key} must be a dictionary in input file {filename}")

    # Set verbose default and validate
    if "verbose" not in h_dict:
        h_dict["verbose"] = False
    elif not isinstance(h_dict["verbose"], bool):
        raise ValueError(f"Verbose must be a boolean in input file {filename}")

    # Validate log_every_n if present
    if "log_every_n" in h_dict:
        if not isinstance(h_dict["log_every_n"], int) or h_dict["log_every_n"] <= 0:
            raise ValueError(f"log_every_n must be a positive integer in input file {filename}")

    # Validate no components have verbose key
    for key in component_names:
        if key in h_dict and "verbose" in h_dict[key]:
            raise ValueError(f"{key} cannot include a verbose key in input file {filename}")

    # Validate component types
    for key in component_names:
        if key in h_dict:
            if "component_type" not in h_dict[key]:
                raise ValueError(
                    f"{key} must include a component_type key in input file {filename}"
                )
            if h_dict[key]["component_type"] not in component_types[key]:
                raise ValueError(
                    f"{key} has an invalid component_type {h_dict[key]['component_type']} "
                    f"in input file {filename}"
                )

    # Handle external_data structure normalization

    # First ensure that not both external_data_file and external_data appear
    if "external_data_file" in h_dict and "external_data" in h_dict:
        raise ValueError(
            f"Cannot specify both external_data_file and external_data in input file {filename}. "
            "Preferred is to specify external_data_file within external_data "
            "and specify log_channels within external_data. "
            "The old format is still supported for backward compatibility "
            "but will show a deprecation warning."
        )

    # If old-style external_data_file is used at top level, convert to new structure with warning
    if "external_data_file" in h_dict:
        warnings.warn(
            "Specifying 'external_data_file' at the top level is deprecated. "
            "Please use 'external_data: {external_data_file: ...}' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        h_dict["external_data"] = {
            "external_data_file": h_dict.pop("external_data_file"),
            "log_channels": None,  # None means log all
        }

    # Validate external_data structure if present
    if "external_data" in h_dict:
        if not isinstance(h_dict["external_data"], dict):
            raise ValueError(f"external_data must be a dictionary in input file {filename}")

        # If external_data_file is not specified, treat external_data as blank (remove it)
        if "external_data_file" not in h_dict["external_data"]:
            h_dict.pop("external_data")
        else:
            # Validate and set default for log_channels
            # (only if external_data_file is present)
            if "log_channels" in h_dict["external_data"]:
                log_channels = h_dict["external_data"]["log_channels"]
                # Allow None (from backward compatibility conversion) or list
                if log_channels is not None and not isinstance(log_channels, list):
                    raise ValueError(
                        f"external_data log_channels must be a list or None "
                        f"in input file {filename}"
                    )
                # None means log all, empty list means log nothing,
                # non-empty list means log only those
            else:
                # If not specified, default to None (log all channels)
                h_dict["external_data"]["log_channels"] = None

    return h_dict


def setup_logging(
    logger_name="hercules",
    log_file="log_hercules.log",
    console_output=True,
    console_prefix=None,
    log_level=logging.INFO,
    use_outputs_dir=True,
):
    """Set up logging to file and console with flexible configuration.

    This function provides a unified interface for setting up logging across all
    Hercules components. It supports both simple filenames (with automatic 'outputs'
    directory creation) and full file paths. Console output is optional and can be
    customized with a prefix.

    Args:
        logger_name (str, optional): Name for the logger instance. Defaults to "hercules".
        log_file (str, optional): Log file name or full path. Defaults to "log_hercules.log".
        console_output (bool, optional): Enable console output. Defaults to True.
        console_prefix (str, optional): Prefix for console messages. If None, uses
            logger_name in uppercase. Defaults to None.
        log_level (int, optional): Logging level (e.g., logging.INFO, logging.DEBUG).
            Defaults to logging.INFO.
        use_outputs_dir (bool, optional): If True and log_file is a simple filename
            (no directory separators), automatically places it in 'outputs' directory.
            If False, treats log_file as-is. Defaults to True.

    Returns:
        logging.Logger: Configured logger instance.


    """
    # Determine the log file path
    if use_outputs_dir and (os.sep not in log_file and "/" not in log_file):
        # Simple filename - use outputs directory
        log_dir = os.path.join(os.getcwd(), "outputs")
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, log_file)
    else:
        # Full path or use_outputs_dir=False - use as-is but ensure directory exists
        log_file_path = log_file
        log_dir = Path(log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

    # Get the logger
    logger = logging.getLogger(logger_name)

    # Clear any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    logger.setLevel(log_level)

    # Add file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler()
        # Use provided prefix or default to logger name in uppercase
        prefix = console_prefix if console_prefix is not None else logger_name.upper()
        console_handler.setFormatter(
            logging.Formatter(f"[{prefix}] %(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(console_handler)

    return logger


def close_logging(logger):
    """Close all handlers for logger to prevent resource warnings.

    Args:
        logger (logging.Logger): Logger instance to close.
    """
    if logger:
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


def interpolate_df(df, new_time):
    """Interpolate DataFrame values to match new time axis.

    Uses linear interpolation with Polars backend for better performance and memory efficiency.
    Converts datetime columns to timestamps for interpolation.

    Args:
        df (pd.DataFrame): DataFrame with 'time' column and data columns.
        new_time (array-like): New time points for interpolation.

    Returns:
        pd.DataFrame: DataFrame with new time axis and interpolated data columns.
    """
    # Convert new_time to numpy array for consistency
    new_time = np.asarray(new_time)

    # Separate datetime and non-datetime columns for different processing
    datetime_cols = []
    numeric_cols = []

    for col in df.columns:
        if col != "time":
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                datetime_cols.append(col)
            else:
                numeric_cols.append(col)

    return _interpolate_with_polars(df, new_time, datetime_cols, numeric_cols)


def _interpolate_with_polars(df, new_time, datetime_cols, numeric_cols):
    """Interpolate using Polars backend.

    Args:
        df (pd.DataFrame): Input DataFrame.
        new_time (np.ndarray): New time points.
        datetime_cols (list): Datetime column names.
        numeric_cols (list): Numeric column names.

    Returns:
        pd.DataFrame: Interpolated DataFrame.
    """
    # Convert to Polars for efficient processing
    df_pl = pl.from_pandas(df)

    # Create a Polars DataFrame for the new time points
    new_time_pl = pl.DataFrame({"time": new_time})

    # Start with the time column
    result_pl = new_time_pl

    # Process numeric columns using Polars' interpolation
    if numeric_cols:
        for col in numeric_cols:
            # Use Polars' join_asof for efficient interpolation-like behavior
            # This is more memory efficient than pandas for large datasets
            col_data = df_pl.select(["time", col]).sort("time")

            # Perform interpolation using Polars operations
            # Note: Polars doesn't have direct linear interpolation, so we use numpy interp
            # but with Polars' efficient data extraction
            time_values = col_data["time"].to_numpy()
            col_values = col_data[col].to_numpy()

            # Linear interpolation
            interpolated_values = np.interp(new_time, time_values, col_values)

            # Add interpolated column to result
            result_pl = result_pl.with_columns(pl.lit(interpolated_values).alias(col))

    # Process datetime columns
    for col in datetime_cols:
        # Extract datetime data using Polars
        col_data = df_pl.select(["time", col]).sort("time")
        time_values = col_data["time"].to_numpy()

        # Convert datetime to timestamps for interpolation
        datetime_values = col_data[col].to_pandas().astype("int64").values / 10**9

        # Interpolate timestamps
        interpolated_timestamps = np.interp(new_time, time_values, datetime_values)

        # Convert back to datetime and add to result
        interpolated_datetimes = pd.to_datetime(interpolated_timestamps, unit="s", utc=True)
        result_pl = result_pl.with_columns(pl.Series(col, interpolated_datetimes))

    # Convert back to pandas DataFrame
    return result_pl.to_pandas()


def find_time_utc_value(df, time_value, time_column="time", time_utc_column="time_utc"):
    """Return UTC timestamp at a given time value via linear interpolation or extrapolation.

    This function maps a numeric simulation time to a UTC timestamp by linearly
    interpolating between rows in ``df``. If ``time_value`` lies outside the
    range of ``time_column``, linear extrapolation is performed.

    Args:
        df (pd.DataFrame): Input DataFrame containing time and UTC columns.
        time_value (float): Time at which to compute the UTC value.
        time_column (str, optional): Name of the numeric time column. Defaults to "time".
        time_utc_column (str, optional): Name of the UTC datetime column. Defaults to "time_utc".

    Returns:
        pd.Timestamp: UTC-aware timestamp corresponding to ``time_value``.
    """
    if time_column not in df.columns or time_utc_column not in df.columns:
        raise ValueError(f"DataFrame must contain '{time_column}' and '{time_utc_column}' columns")

    # Drop rows with missing values in either column, then sort by time
    df_valid = (
        df[[time_column, time_utc_column]]
        .dropna(subset=[time_column, time_utc_column])
        .sort_values(time_column)
    )

    if len(df_valid) < 2:
        raise ValueError("At least two valid rows are required for interpolation/extrapolation")

    # Extract arrays for interpolation. Convert datetimes to seconds since epoch (UTC)
    time_values = df_valid[time_column].to_numpy()
    utc_ns = df_valid[time_utc_column].astype("int64").to_numpy()  # nanoseconds since epoch
    utc_seconds = utc_ns.astype(np.float64) / 1e9

    # Linear interpolation/extrapolation
    f = interp1d(
        time_values,
        utc_seconds,
        kind="linear",
        bounds_error=False,
        fill_value="extrapolate",
        assume_sorted=True,
    )
    sec = float(f(time_value))
    return pd.to_datetime(sec, unit="s", utc=True)


def load_h_dict_from_text(filename):
    """Load h_dict from text file created by _save_h_dict_as_text.

    Reads Python dictionary representation from text file and converts back to dict.

    Args:
        filename (str): Path to text file containing h_dict representation.

    Returns:
        dict: Reconstructed h_dict dictionary.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file content cannot be parsed as valid Python dictionary.
    """

    try:
        with open(filename, "r") as f:
            content = f.read().strip()

        # Create a safe namespace with only numpy functions we expect
        safe_namespace = {
            "np": np,
            "array": np.array,
            "float64": np.float64,
            "float32": np.float32,
            "int64": np.int64,
            "True": True,
            "False": False,
            "None": None,
            "inf": np.inf,  # Added line
            "range": range,
        }

        # Use eval with the safe namespace to handle numpy objects
        # This is safe because we control the namespace
        h_dict = eval(content, {"__builtins__": {}}, safe_namespace)

        # Validate that we got a dictionary
        if not isinstance(h_dict, dict):
            raise ValueError(f"File content does not represent a valid dictionary: {filename}")

        return h_dict

    except FileNotFoundError:
        raise FileNotFoundError(f"Could not find file: {filename}")
    except (ValueError, SyntaxError, NameError) as e:
        raise ValueError(f"Could not parse dictionary from file {filename}: {str(e)}")


def load_perffile(perffile):
    """Load and parse a wind turbine performance file.

    This function reads a performance file containing wind turbine coefficient data
    including power coefficients (Cp), thrust coefficients (Ct), and torque coefficients (Cq)
    as functions of tip speed ratio (TSR) and blade pitch angle. The data is converted
    into RegularGridInterpolator objects for efficient interpolation during simulation.

    Args:
        perffile (str): Path to the performance file containing turbine coefficient data.

    Returns:
        dict: A dictionary containing RegularGridInterpolator objects for 'Cp', 'Ct', and 'Cq'
            coefficients, keyed by coefficient name.
    """
    perffuncs = {}

    with open(perffile) as pfile:
        for line in pfile:
            # Read Blade Pitch Angles (degrees)
            if "Pitch angle" in line:
                pitch_initial = np.array(
                    [float(x) for x in pfile.readline().strip().split()], dtype=hercules_float_type
                )
                pitch_initial_rad = pitch_initial * np.deg2rad(
                    1
                )  # degrees to rad            -- should this be conditional?

            # Read Tip Speed Ratios (rad)
            if "TSR" in line:
                TSR_initial = np.array(
                    [float(x) for x in pfile.readline().strip().split()], dtype=hercules_float_type
                )

            # Read Power Coefficients
            if "Power" in line:
                pfile.readline()
                Cp = np.empty((len(TSR_initial), len(pitch_initial)), dtype=hercules_float_type)
                for tsr_i in range(len(TSR_initial)):
                    Cp[tsr_i] = np.array(
                        [float(x) for x in pfile.readline().strip().split()],
                        dtype=hercules_float_type,
                    )
                perffuncs["Cp"] = RegularGridInterpolator(
                    (TSR_initial, pitch_initial_rad), Cp, bounds_error=False, fill_value=None
                )

            # Read Thrust Coefficients
            if "Thrust" in line:
                pfile.readline()
                Ct = np.empty((len(TSR_initial), len(pitch_initial)), dtype=hercules_float_type)
                for tsr_i in range(len(TSR_initial)):
                    Ct[tsr_i] = np.array(
                        [float(x) for x in pfile.readline().strip().split()],
                        dtype=hercules_float_type,
                    )
                perffuncs["Ct"] = RegularGridInterpolator(
                    (TSR_initial, pitch_initial_rad), Ct, bounds_error=False, fill_value=None
                )

            # Read Torque Coefficients
            if "Torque" in line:
                pfile.readline()
                Cq = np.empty((len(TSR_initial), len(pitch_initial)), dtype=hercules_float_type)
                for tsr_i in range(len(TSR_initial)):
                    Cq[tsr_i] = np.array(
                        [float(x) for x in pfile.readline().strip().split()],
                        dtype=hercules_float_type,
                    )
                perffuncs["Cq"] = RegularGridInterpolator(
                    (TSR_initial, pitch_initial_rad), Cq, bounds_error=False, fill_value=None
                )

    return perffuncs


def read_hercules_hdf5(filename):
    """Read Hercules HDF5 output file.

    Converts HDF5 file to pandas DataFrame with original output format structure.

    Args:
        filename (str): Path to Hercules HDF5 output file.

    Returns:
        pd.DataFrame: Simulation data with original output format columns.
    """
    with h5py.File(filename, "r") as f:
        # Read time data
        data = {
            "time": f["data/time"][:],
            "step": f["data/step"][:],
        }

        # Reconstruct time_utc using starttime_utc (required)
        if "starttime_utc" not in f["metadata"].attrs:
            raise ValueError(f"starttime_utc not found in metadata attributes in file {filename}")
        starttime_utc = pd.to_datetime(f["metadata"].attrs["starttime_utc"], unit="s", utc=True)
        time = pd.to_timedelta(data["time"], unit="s")
        data["time_utc"] = starttime_utc + time

        # Read plant data
        data["plant.power"] = f["data/plant_power"][:]
        data["plant.locally_generated_power"] = f["data/plant_locally_generated_power"][:]

        # Read component data
        components_group = f["data/components"]
        for dataset_name in components_group.keys():
            data[dataset_name] = components_group[dataset_name][:]

        # Read external signals
        if "external_signals" in f["data"]:
            for dataset_name in f["data/external_signals"].keys():
                data[dataset_name] = f["data/external_signals"][dataset_name][:]

    return pd.DataFrame(data)


def get_hercules_metadata(filename):
    """Read Hercules HDF5 output file metadata.

    Args:
        filename (str): Path to Hercules HDF5 output file.

    Returns:
        dict: Simulation metadata including h_dict and simulation info.
    """
    with h5py.File(filename, "r") as f:
        metadata = {}

        # Read h_dict from JSON string
        if "h_dict" in f["metadata"].attrs:
            import json

            metadata["h_dict"] = json.loads(f["metadata"].attrs["h_dict"])

        # Read simulation info
        for key, value in f["metadata"].attrs.items():
            if key != "h_dict":
                metadata[key] = value

    return metadata
