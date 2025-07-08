# Implements the long run wind model for Hercules.

import logging
from pathlib import Path


class PySimBase:
    """
    Base class for Python simulators.
    """

    def __init__(self, h_dict, py_sim_name):
        """
        Initialize the base simulator with a dictionary of parameters.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
        """

        # Set up logging
        # Check if log_file_name is defined in the h_dict['wind_farm']
        if "log_file_name" in h_dict[py_sim_name]:
            self.log_file_name = h_dict[py_sim_name]["log_file_name"]
        else:
            self.log_file_name = f"outputs/log_{py_sim_name}.log"

        self.logger = self._setup_logging(self.log_file_name)

        # Initialize the outputs to log
        self.log_outputs = ["power"]

        # Save the time information
        self.dt = h_dict["dt"]
        self.starttime = h_dict["starttime"]
        self.endtime = h_dict["endtime"]

        # Compute the number of time steps
        self.n_steps = int((self.endtime - self.starttime) / self.dt)

        # Use the top-level verbose option
        self.verbose = h_dict["verbose"]
        self.logger.info(f"read in verbose flag = {self.verbose}")

    def _setup_logging(self, log_file_name):
        """
        Sets up logging for the wind simulator.

        This method configures a logger named "wind_sim" to log messages to a specified file.
        It ensures the log directory exists, clears any existing handlers to avoid duplicates,
        and formats log messages with timestamps, log levels, and messages.
        Args:
            log_file_name (str): The full path to the log file where log messages will be written.
        Returns:
            logging.Logger: Configured logger instance for the wind simulator.
        """

        # Split the logfile into directory and filename
        log_dir = Path(log_file_name).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Get the logger for wind_sim, note that root logger already in use
        logger = logging.getLogger("wind_sim")
        logger.setLevel(logging.INFO)

        # Clear any existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Add file handler
        file_handler = logging.FileHandler(log_file_name)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(file_handler)

        return logger

    def __del__(self):
        """
        Cleanup method to properly close log file handlers.
        """
        if hasattr(self, 'logger'):
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)

    def close_logging(self):
        """
        Explicitly close all log file handlers.
        """
        if hasattr(self, 'logger'):
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)