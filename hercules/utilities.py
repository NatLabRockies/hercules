import logging
import os

import numpy as np
import pandas as pd
import yaml
from scipy.interpolate import interp1d, RegularGridInterpolator


# Define the available py_sim names
def get_available_py_sim_names():
    """Return a list of available py_sim names.

    Returns:
        list: A list of strings containing the names of available py_sim components.
    """
    return [
        "wind_farm",
        "solar_farm",
        "battery",
        "electrolyzer",
    ]


# Note this is a subset of the py_sims
def get_available_generator_names():
    """Return a list of available generator names.

    This function returns a subset of py_sim names that represent power generators
    (wind_farm and solar_farm), excluding storage and conversion components.

    Returns:
        list: A list of strings containing the names of available generator components.
    """
    return [
        "wind_farm",
        "solar_farm",
    ]


def get_available_py_sim_types():
    """Return a list of available py_sim types, by py_sim.

    Returns:
        dict: A dictionary mapping py_sim names to lists of available simulation types.
    """
    return {
        "wind_farm": ["WindSimLongTerm"],
        "solar_farm": ["SimpleSolar", "SolarPySAM"],
        "battery": ["SimpleBattery", "LIB"],
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
    py_sim_names = get_available_py_sim_names()
    py_sim_types = get_available_py_sim_types()
    other_keys = [
        "name",
        "description",
        "controller",
        "verbose",
        "output_file",
        "time_log_interval",
        "external_data_file",
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

    # Ensure that interconnect_limit is a float
    if not isinstance(h_dict["plant"]["interconnect_limit"], float):
        raise ValueError(f"Interconnect limit must be a float in input file {filename}")

    # Check that all keys are either required or optional
    for key in h_dict:
        if key not in required_keys + py_sim_names + other_keys:
            raise ValueError(f"Key {key} not a valid key in input file {filename}")

    # Of the pysim keys present in h_dict, confirm all are dictionaries
    for key in py_sim_names:
        if key in h_dict:
            if not isinstance(h_dict[key], dict):
                raise ValueError(f"{key} must be a dictionary in input file {filename}")

    # If verbose is not present, set it to False
    if "verbose" not in h_dict:
        h_dict["verbose"] = False
    # If verbose is present, check that it is a boolean
    elif not isinstance(h_dict["verbose"], bool):
        raise ValueError(f"Verbose must be a boolean in input file {filename}")

    # Check that none of the include py_sims include a verbose key
    for key in py_sim_names:
        if key in h_dict:
            if "verbose" in h_dict[key]:
                raise ValueError(f"{key} cannot include a verbose key in input file {filename}")

    # Check that all of the included py_sims have a py_sim_type key and that key is valid
    for key in py_sim_names:
        if key in h_dict:
            if "py_sim_type" not in h_dict[key]:
                raise ValueError(f"{key} must include a py_sim_type key in input file {filename}")
            if h_dict[key]["py_sim_type"] not in py_sim_types[key]:
                raise ValueError(
                    f"{key} has an invalid py_sim_type {h_dict[key]['py_sim_type']} in input file {filename}"
                )

    # Check that verbose is a boolean
    return h_dict


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
                pitch_initial = np.array([float(x) for x in pfile.readline().strip().split()])
                pitch_initial_rad = pitch_initial * np.deg2rad(
                    1
                )  # degrees to rad            -- should this be conditional?

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


# Configure logging
def setup_logging(logfile="log_hercules.log", console_output=False):
    """Set up logging to file and console.

    This function configures logging for the Hercules emulator. It creates an 'outputs'
    directory if it doesn't exist and sets up file logging with a timestamped format.
    Optionally, it can also enable console output for real-time logging.

    Args:
        logfile (str, optional): Name of the log file. Defaults to "log_hercules.log".
        console_output (bool, optional): Whether to enable console logging output.
            Defaults to False.

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
        console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(console_handler)

    return logger


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
                timestamps = df[col].view("int64") / 10**9  # nanoseconds to seconds
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
