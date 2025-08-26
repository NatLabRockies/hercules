import logging
import os

import h5py
import numpy as np
import pandas as pd
import polars as pl
import yaml
from scipy.interpolate import interp1d, RegularGridInterpolator

# Define the Hercules float type
hercules_float_type = np.float32


# Define the available component names
def get_available_component_names():
    """Return a list of available component names.

    Returns:
        list: A list of strings containing the names of available plant components.
    """
    return [
        "wind_farm",
        "solar_farm",
        "battery",
        "electrolyzer",
    ]


# Note this is a subset of the components
def get_available_generator_names():
    """Return a list of available generator names.

    This function returns a subset of component names that represent power generators
    (wind_farm and solar_farm), excluding storage and conversion components.

    Returns:
        list: A list of strings containing the names of available generator components.
    """
    return [
        "wind_farm",
        "solar_farm",
    ]


def get_available_component_types():
    """Return a list of available component types, by component.

    Returns:
        dict: A dictionary mapping component names to lists of available simulation types.
    """
    return {
        "wind_farm": ["Wind_MesoToPower", "Wind_MesoToPowerPrecomFloris"],
        "solar_farm": ["SolarPySAMPVSam", "SolarPySAMPVWatts"],
        "battery": ["BatterySimple", "BatteryLithiumIon"],
        "electrolyzer": ["ElectrolyzerPlant"],
    }


class Loader(yaml.SafeLoader):
    """Custom YAML loader that supports !include tags.

    This loader extends yaml.SafeLoader to support custom !include tags that allow
    including other YAML files within a main YAML file.
    """

    def __init__(self, stream):
        """Initialize the Loader with a stream.

        Args:
            stream: The YAML stream to load from.
        """
        self._root = os.path.split(stream.name)[0]

        super().__init__(stream)

    def include(self, node):
        """Include another YAML file at the current location.

        Args:
            node: The YAML node containing the filename to include.

        Returns:
            dict: The parsed YAML content from the included file.
        """
        filename = os.path.join(self._root, self.construct_scalar(node))

        with open(filename, "r") as f:
            return yaml.load(f, self.__class__)


Loader.add_constructor("!include", Loader.include)


def load_yaml(filename, loader=Loader):
    """Load and parse a YAML file into a Python dictionary.

    This function loads a YAML file and parses it into a Python dictionary. It supports
    custom YAML tags like !include through the custom Loader class. If a dictionary is
    passed instead of a filename, it returns the dictionary unchanged.

    Args:
        filename (Union[str, dict]): Path to the YAML file to load, or an existing
            dictionary containing YAML data.
        loader (yaml.Loader, optional): The YAML loader class to use for parsing.
            Defaults to the custom Loader class that supports !include tags.

    Returns:
        dict: The parsed YAML data as a Python dictionary.

    """
    if isinstance(filename, dict):
        return filename  # filename already yaml dict
    with open(filename) as fid:
        return yaml.load(fid, loader)


def load_hercules_input(filename):
    """Load and parse a Hercules input file and return h_dict dictionary.

    This function loads a Hercules input YAML file and performs comprehensive validation
    of the input structure. It checks for required keys, validates data types, and
    ensures the configuration follows the expected format for Hercules simulations.

    Args:
        filename (str): Path to the Hercules input YAML file.

    Returns:
        dict: A validated dictionary containing the Hercules input configuration.

    Raises:
        ValueError: If required keys are missing, data types are invalid, or the
            configuration structure is incorrect.
    """
    h_dict = load_yaml(filename)

    # Known keys
    required_keys = ["dt", "starttime", "endtime", "plant"]
    component_names = get_available_component_names()
    component_types = get_available_component_types()
    other_keys = [
        "name",
        "description",
        "controller",
        "verbose",
        "output_file",
        "output_format",
        "output_time_step",
        "time_log_interval",
        "external_data_file",
        "output_use_compression",
        "output_buffer_size",
    ]

    # Check that required keys are present

    for key in required_keys:
        if key not in h_dict:
            raise ValueError(f"Required key {key} not found in input file {filename}")

    # Check that plant is a dictionary
    if not isinstance(h_dict["plant"], dict):
        raise ValueError(f"Plant must be a dictionary in input file {filename}")

    # Ensure that plant contains a interconnect_limit key
    if "interconnect_limit" not in h_dict["plant"]:
        raise ValueError(f"Plant must contain an interconnect_limit key in input file {filename}")

    # Ensure that interconnect_limit is a float or an int
    if not isinstance(h_dict["plant"]["interconnect_limit"], (float, int)):
        raise ValueError(f"Interconnect limit must be a float in input file {filename}")

    # Check that all keys are either required or optional
    for key in h_dict:
        if key not in required_keys + component_names + other_keys:
            raise ValueError(f"Key {key} not a valid key in input file {filename}")

    # Of the component keys present in h_dict, confirm all are dictionaries
    for key in component_names:
        if key in h_dict:
            if not isinstance(h_dict[key], dict):
                raise ValueError(f"{key} must be a dictionary in input file {filename}")

    # If verbose is not present, set it to False
    if "verbose" not in h_dict:
        h_dict["verbose"] = False
    # If verbose is present, check that it is a boolean
    elif not isinstance(h_dict["verbose"], bool):
        raise ValueError(f"Verbose must be a boolean in input file {filename}")

    # Check that none of the included components include a verbose key
    for key in component_names:
        if key in h_dict:
            if "verbose" in h_dict[key]:
                raise ValueError(f"{key} cannot include a verbose key in input file {filename}")

    # Check that all of the included components have a component_type key and that key is valid
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

    # Check that verbose is a boolean

    # Validate output configuration options
    if "output_format" in h_dict:
        valid_formats = ["feather", "parquet", "csv"]
        if h_dict["output_format"].lower() not in valid_formats:
            raise ValueError(
                f"output_format must be one of {valid_formats}, got '{h_dict['output_format']}'"
            )

    if "output_time_step" in h_dict:
        if (
            not isinstance(h_dict["output_time_step"], (int, float))
            or h_dict["output_time_step"] <= 0
        ):
            raise ValueError("output_time_step must be a positive number")
        if h_dict["output_time_step"] < h_dict["dt"]:
            raise ValueError("output_time_step must be greater than or equal to dt")

    return h_dict


# Configure logging
def setup_logging(logfile="log_hercules.log", console_output=True):
    """Set up logging to file and console.

    This function configures logging for the Hercules emulator. It creates an 'outputs'
    directory if it doesn't exist and sets up file logging with a timestamped format.
    By default, it enables console output for real-time logging with logger identification.

    Args:
        logfile (str, optional): Name of the log file. Defaults to "log_hercules.log".
        console_output (bool, optional): Whether to enable console logging output.
            Defaults to True.

    Returns:
        logging.Logger: The configured logger instance for the emulator.
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
    """
    Properly close all handlers for a logger to prevent resource warnings.

    Args:
        logger (logging.Logger): The logger instance to close.
    """
    if logger:
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


def interpolate_df(df, new_time):
    """Interpolates the values of a DataFrame to match a new time axis.

    This function takes a DataFrame with a 'time' column and other data columns,
    and interpolates the data columns to align with a new set of time points
    provided in `new_time`. The interpolation is performed using linear
    interpolation. For datetime columns, the function converts to timestamps
    for interpolation and then converts back to datetime format.

    Args:
        df (pd.DataFrame): The input DataFrame containing a 'time' column and
            other columns to be interpolated.
        new_time (array-like): A sequence of new time points to which the data
            should be interpolated.

    Returns:
        pd.DataFrame: A new DataFrame containing the 'time' column with values
            from `new_time` and the interpolated data columns.
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
    """Optimized version of interpolate_df with better memory efficiency and performance.

    This function provides the same functionality as interpolate_df but with significant
    performance improvements through Polars backend operations. Key optimizations include:
    - Polars backend for better memory efficiency and performance
    - Efficient data extraction and processing using Polars operations
    - Reduced memory allocations and intermediate object creation
    - Optimized datetime handling with efficient conversions

    Args:
        df (pd.DataFrame): The input DataFrame containing a 'time' column and
            other columns to be interpolated.
        new_time (array-like): A sequence of new time points to which the data
            should be interpolated.

    Returns:
        pd.DataFrame: A new DataFrame containing the 'time' column with values
            from `new_time` and the interpolated data columns.
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
    """Interpolate using Polars backend for memory efficiency.

    Args:
        df (pd.DataFrame): Input DataFrame.
        new_time (np.ndarray): New time points.
        datetime_cols (list): List of datetime column names.
        numeric_cols (list): List of numeric column names.

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


def load_h_dict_from_text(filename):
    """Load an h_dict from a text file created by _save_h_dict_as_text.

    This function reads a text file that contains a Python dictionary representation
    (as created by the print() function) and converts it back to a Python dictionary.
    The file is expected to contain a single dictionary that was saved using
    _save_h_dict_as_text method from the Emulator class.

    Args:
        filename (str): Path to the text file containing the h_dict representation.

    Returns:
        dict: The reconstructed h_dict dictionary.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file content cannot be parsed as a valid Python dictionary.
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
    """Read Hercules HDF5 output file and return data as pandas DataFrame.

    This function reads a Hercules HDF5 output file and converts it to a pandas DataFrame
    with the same structure as the original output format for backward compatibility.

    Args:
        filename (str): Path to the Hercules HDF5 output file.

    Returns:
        pd.DataFrame: DataFrame containing the simulation data with columns matching
            the original output format.
    """
    with h5py.File(filename, "r") as f:
        # Read basic time data
        data = {
            "time": f["data/time"][:],
            "step": f["data/step"][:],
            "clock_time": f["data/clock_time"][:],
        }

        # Read time_utc if available
        if "time_utc" in f["data"]:
            data["time_utc"] = f["data/time_utc"][:]

        # If start_time_utc is available, and time_utc is not, add time_utc to data
        # using time and start_time_utc
        if "start_time_utc" in f["metadata"].attrs and "time_utc" not in data:
            # Save as datetime
            start_time_utc = pd.to_datetime(
                f["metadata"].attrs["start_time_utc"], unit="s", utc=True
            )
            time = pd.to_timedelta(data["time"], unit="s")
            data["time_utc"] = start_time_utc + time

        # Read plant-level data
        data["plant.power"] = f["data/plant_power"][:]
        data["plant.locally_generated_power"] = f["data/plant_locally_generated_power"][:]

        # Read component data
        components_group = f["data/components"]
        for dataset_name in components_group.keys():
            # Dataset names use dot format (e.g., wind_farm.floris_wind_direction)
            # Use dataset name directly as column name
            data[dataset_name] = components_group[dataset_name][:]

        # Read in in all external signals external_signals.signal_name
        if "external_signals" in f["data"]:
            for signal_name in f["data/external_signals"].keys():
                data[f"external_signals.{signal_name}"] = f["data/external_signals"][signal_name][:]

    return pd.DataFrame(data)


def get_hercules_metadata(filename):
    """Read Hercules HDF5 output file metadata.

    Args:
        filename (str): Path to the Hercules HDF5 output file.

    Returns:
        dict: Dictionary containing simulation metadata including h_dict and simulation info.
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
