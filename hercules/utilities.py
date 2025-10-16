import logging
import os

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


def load_hercules_input(filename):
    """Load and validate Hercules input file.

    Loads YAML file and validates input structure, required keys, and data types.

    Args:
        filename (str): Path to Hercules input YAML file.

    Returns:
        dict: Validated Hercules input configuration.

    Raises:
        ValueError: If required keys missing, invalid data types, or incorrect structure.
    """
    h_dict = load_yaml(filename)

    # Define valid keys
    required_keys = ["dt", "starttime", "endtime", "plant"]
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
        "output_use_compression",
        "output_buffer_size",
    ]

    # Validate required keys
    for key in required_keys:
        if key not in h_dict:
            raise ValueError(f"Required key {key} not found in input file {filename}")

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
            raise ValueError(f"Key {key} not a valid key in input file {filename}")

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

    return h_dict


def setup_logging(logfile="log_hercules.log", console_output=True):
    """Set up logging to file and console.

    Creates 'outputs' directory and configures file/console logging with timestamps.

    Args:
        logfile (str, optional): Log file name. Defaults to "log_hercules.log".
        console_output (bool, optional): Enable console output. Defaults to True.

    Returns:
        logging.Logger: Configured logger instance.
    """
    log_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, logfile)

    # Get the root logger
    logger = logging.getLogger("emulator")

    # Clear any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    logger.setLevel(logging.INFO)

    # Add file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

    # Add console handler
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("[EMULATOR] %(asctime)s - %(levelname)s - %(message)s")
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

    Uses linear interpolation. Converts datetime columns to timestamps for interpolation.

    Args:
        df (pd.DataFrame): DataFrame with 'time' column and data columns.
        new_time (array-like): New time points for interpolation.

    Returns:
        pd.DataFrame: DataFrame with new time axis and interpolated data columns.
    """
    # Create dictionary to store all columns
    result_dict = {"time": new_time}

    # Populate the dictionary with interpolated values for each column
    for col in df.columns:
        if col != "time":
            # Check if column contains datetime values
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                # Convert datetime to timestamps (float) for interpolation
                timestamps = df[col].astype("int64") / 10**9  # nanoseconds to seconds
                f = interp1d(df["time"].values, timestamps, bounds_error=True)
                interpolated_timestamps = f(new_time)
                # Convert timestamps back to datetime
                result_dict[col] = pd.to_datetime(interpolated_timestamps, unit="s", utc=True)
            else:
                # Standard interpolation for non-datetime columns
                f = interp1d(df["time"].values, df[col].values, bounds_error=True)
                result_dict[col] = f(new_time)

    # Create DataFrame from the dictionary (all columns at once)
    result = pd.DataFrame(result_dict)
    return result


def interpolate_df_fast(df, new_time):
    """Optimized interpolate_df with Polars backend for better performance.

    Same functionality as interpolate_df but with improved memory efficiency and speed.

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

        # Reconstruct time_utc using zero_time_utc
        if "zero_time_utc" in f["metadata"].attrs:
            zero_time_utc = pd.to_datetime(f["metadata"].attrs["zero_time_utc"], unit="s", utc=True)
            time = pd.to_timedelta(data["time"], unit="s")
            data["time_utc"] = zero_time_utc + time

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


# def read_hercules_hdf5_subset(filename, columns=None, time_range=None, stride=1):
#     """Read subset of Hercules HDF5 output file data.

#     Returns only specified columns and time range, reducing memory usage for large datasets.
#     Optionally applies stride to read every Nth data point for further downsampling.

#     Args:
#         filename (str): Path to Hercules HDF5 output file.
#         columns (list, optional): Column names to include. If None, includes only time column.
#         time_range (tuple, optional): (start_time, end_time) in seconds. If None, includes all
#             times.
#         stride (int, optional): Read every Nth data point. Defaults to 1 (read all points).

#     Returns:
#         pd.DataFrame: Subset of simulation data.
#     """
#     with h5py.File(filename, "r") as f:
#         # Get time indices for subset
#         time_data = f["data/time"][:]
#         start_idx = 0
#         end_idx = len(time_data)

#         if time_range is not None:
#             start_time, end_time = time_range
#             start_idx = np.searchsorted(time_data, start_time, side="left")
#             end_idx = np.searchsorted(time_data, end_time, side="right")

#         # Apply stride to indices
#         indices = np.arange(start_idx, end_idx, stride)

#         # Always include time data
#         data = {"time": time_data[indices]}

#         # If no columns specified, return only time
#         if columns is None:
#             return pd.DataFrame(data)

#         # Read requested columns
#         for col in columns:
#             if col == "step":
#                 data[col] = f["data/step"][indices]

#             elif col == "time_utc":
#                 if "time_utc" in f["data"]:
#                     data[col] = f["data/time_utc"][indices]
#                 elif "start_time_utc" in f["metadata"].attrs:
#                     # Reconstruct time_utc from start_time_utc
#                     start_time_utc = pd.to_datetime(
#                         f["metadata"].attrs["start_time_utc"], unit="s", utc=True
#                     )
#                     time_subset = pd.to_timedelta(data["time"], unit="s")
#                     data[col] = start_time_utc + time_subset
#             elif col == "plant.power":
#                 data[col] = f["data/plant_power"][indices]
#             elif col == "plant.locally_generated_power":
#                 data[col] = f["data/plant_locally_generated_power"][indices]
#             elif col in f["data/components"]:
#                 data[col] = f["data/components"][col][indices]
#             elif col in f["data/external_signals"]:
#                 data[col] = f["data/external_signals"][col][indices]

#     return pd.DataFrame(data)


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
