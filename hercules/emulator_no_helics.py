import csv
import datetime as dt
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

LOGFILE = str(dt.datetime.now()).replace(":", "_").replace(" ", "_").replace(".", "_")

Path("outputs").mkdir(parents=True, exist_ok=True)


class EmulatorNoHelics:
    def __init__(self, controller, py_sims, input_dict, logger):
        """
        Initializes the emulator.

        Args:
            controller (object): The controller object responsible for managing the simulation.
            py_sims (object): An object containing Python-based simulation components.
            input_dict (dict): A dictionary containing configuration parameters for the emulator.
                Required keys:
                    - "dt" (float): The time step for the simulation in seconds.
                    - "starttime" (float): The start time of the simulation in seconds.
                    - "endtime" (float): The end time of the simulation in seconds.
                Optional keys:
                    - "output_file" (str): Path to the output CSV file.
                        Defaults to "outputs/hercules_output.csv".
                    - "external_data_file" (str): Path to an external data file
                        for additional inputs.
            logger (object): A logger instance for logging messages during the simulation.

        """

        # Make sure output folder exists
        Path("outputs").mkdir(parents=True, exist_ok=True)

        # Use the provided logger
        self.logger = logger

        # Save the input dict to main dict
        self.main_dict = input_dict

        # Initialize the flattened main_dict
        self.main_dict_flat = {}

        # Initialize the output file
        if "output_file" in input_dict:
            self.output_file = input_dict["output_file"]
        else:
            self.output_file = "outputs/hercules_output.csv"

        # Initialize the csv writer
        self.csv_file = None
        self.csv_writer = None
        self.header_written = False
        self.header = None

        # Initialize the csv buffer
        self.csv_buffer_size = 1000
        self.csv_buffer = []

        # Save time step, start time and end time
        self.dt = input_dict["dt"]
        self.starttime = input_dict["starttime"]
        self.endtime = input_dict["endtime"]
        self.total_simulation_time = self.endtime - self.starttime  # In seconds
        self.total_simulation_days = self.total_simulation_time / 86400
        self.time = self.starttime

        # Initialize the step
        self.step = 0
        self.n_steps = int(self.total_simulation_time / self.dt)

        # How often to update the user on current emulator time
        # In simulated time
        self.time_log_interval = 600  # seconds
        self.step_log_interval = self.time_log_interval / self.dt

        # Round to step_log_interval to be an integer greater than 0
        self.step_log_interval = np.max([1, np.round(self.step_log_interval)])

        # Initialize components
        self.controller = controller
        self.py_sims = py_sims

        # Update the input dict components
        self.main_dict["py_sims"] = self.py_sims.get_py_sim_dict()

        # Read in any external data
        self.external_data_all = {}
        if "external_data_file" in input_dict:
            self._read_external_data_file(input_dict["external_data_file"])
            self.external_signals = {}
            self.main_dict["external_signals"] = {}

    def _read_external_data_file(self, filename):
        """
        Read and interpolate external data from a CSV file.

        This method reads external data from the specified CSV file and interpolates it
        according to the simulation time steps. The external data must include a 'time' column.
        The interpolated data is stored in self.external_data_all.
        Args:
            filename (str): Path to the CSV file containing external data.
        """

        # Read in the external data file
        df_ext = pd.read_csv(filename)
        if "time" not in df_ext.columns:
            raise ValueError("External data file must have a 'time' column")

        # Interpolate the external data according to time.
        # Goes to 1 time step past stoptime specified in the input file.
        times = np.arange(
            self.starttime,
            self.endtime + (2 * self.dt),
            self.dt,
        )
        self.external_data_all["time"] = times
        for c in df_ext.columns:
            if c != "time":
                self.external_data_all[c] = np.interp(times, df_ext.time, df_ext[c])

    def _open_output_file(self):
        """
        Open the output file for writing with buffering.

        This method creates the output directory if it doesn't exist,
        opens the output file with buffering for improved performance,
        and determines whether a header needs to be written based on
        if the file is empty.
        """
        # Create directory if it doesn't exist
        output_dir = os.path.dirname(os.path.abspath(self.output_file))
        os.makedirs(output_dir, exist_ok=True)

        # Open the file with buffering
        self.csv_file = open(self.output_file, "a", newline="", buffering=8192)  # 8KB buffer
        self.csv_writer = csv.writer(self.csv_file)

        # Check if file is empty to determine if header needs to be written
        if os.path.getsize(self.output_file) == 0:
            self.header_written = False
        else:
            self.header_written = True
            # Read the header from file
            with open(self.output_file, "r") as f:
                self.header = f.readline().strip().split(",")

    def _save_main_dict_as_text(self):
        """
        Save the main dictionary to a text file.

        This method redirects stdout to a file, prints the main dictionary, and then
        restores stdout to its original state. The dictionary is saved to
        'outputs/main_dict.echo' to help with log interpretation.
        """

        # Echo the dictionary to a seperate file in case it is helpful
        # to see full dictionary in interpreting log

        original_stdout = sys.stdout
        with open("outputs/main_dict.echo", "w") as f_i:
            sys.stdout = f_i  # Change the standard output to the file we created.
            print(self.main_dict)
            sys.stdout = original_stdout  # Reset the standard output to its original value

    def enter_execution(self, function_targets=[], function_arguments=[[]]):
        """
        Execute the main simulation loop and handle timing and logging.

        This method initiates the simulation execution, runs the main loop, and handles
        all associated timing calculations, logging, and file operations. It ensures proper
        cleanup of resources even if exceptions occur during simulation.

        Args:
            function_targets (list, optional): List of functions to execute during simulation.
                Defaults to empty list.
            function_arguments (list of lists, optional): List of argument lists to pass to each
                corresponding function in function_targets.
                Defaults to a list containing an empty list.
        """

        # Open the output file
        self._open_output_file()

        # Wrap this effort in a try block so on failure or completion sure to purge csv buffer
        try:
            # Record the current wall time
            self.start_time_wall = dt.datetime.now()

            # Run the main loop
            self.run()

            # Note the total elapsed time
            self.end_time_wall = dt.datetime.now()
            self.total_time_wall = self.end_time_wall - self.start_time_wall

            # Update the user on time performance
            self.logger.info("=====================================")
            self.logger.info(
                (
                    "Total simulated time: ",
                    f"{self.total_simulation_time} seconds ({self.total_simulation_days} days)",
                )
            )
            self.logger.info(f"Total wall time: {self.total_time_wall}")
            self.logger.info(
                (
                    "Rate of simulation: ",
                    f"{self.total_simulation_time/self.total_time_wall.total_seconds():.1f}",
                    "x real time",
                )
            )
            self.logger.info("=====================================")

        except Exception as e:
            # Log the error
            self.logger.error(f"Error during execution: {str(e)}", exc_info=True)
            # Re-raise the exception after cleanup
            raise

        finally:
            # Ensure the CSV file is properly flushed and closed
            self.logger.info("Closing output files and flushing buffers")
            self.flush_buffer()  # Flush any remaining buffered rows
            self.close_output_file()

    def run(self):
        """
        Runs the emulation loop until the end time is reached.

        """

        self.logger.info(" #### Entering main loop #### ")

        self.first_iteration = True

        # Run simulation through steps
        for self.step in range(self.n_steps):
            # Compute the current time
            self.time = self.starttime + (self.step * self.dt)

            # Log the current time
            if (self.step % self.step_log_interval == 0) or self.first_iteration:
                self.logger.info(f"Emulator time: {self.time} (ending at {self.endtime})")
                self.logger.info(f"Step: {self.step} of {self.n_steps}")
                self.logger.info(f"--Percent completed: {100 * self.step / self.n_steps:.2f}%")

            for k in self.external_data_all:
                self.main_dict["external_signals"][k] = self.external_data_all[k][
                    self.external_data_all["time"] == self.time
                ][0]

            # Update controller and py sims
            self.main_dict["time"] = self.time
            self.main_dict["step"] = self.step
            self.main_dict = self.controller.step(self.main_dict)
            if self.main_dict["py_sims"]:
                self.py_sims.step(self.main_dict)
                self.main_dict["py_sims"] = self.py_sims.get_py_sim_dict()

            # Log the current state
            self.log_main_dict()

            # If this is first iteration log the input dict
            # And turn off the first iteration flag
            if self.first_iteration:
                self.logger.info(self.main_dict)
                self._save_main_dict_as_text()
                self.first_iteration = False

            # Update the time
            self.time = self.time + self.dt

    def recursive_flatten_main_dict(self, nested_dict, prefix=""):
        """
        Recursively flattens a nested dictionary and stores the flattened key-value pairs
        in the `main_dict_flat` attribute.
        Args:
            nested_dict (dict): The nested dictionary to be flattened.
            prefix (str, optional): The prefix to prepend to the keys in the flattened
                dictionary. Defaults to an empty string.
        """

        # Recursively flatten the input dict
        for k, v in nested_dict.items():
            if isinstance(v, dict):
                self.recursive_flatten_main_dict(v, prefix + k + ".")
            else:
                # If v is a list or np.array, enter each element seperately
                if isinstance(v, (list, np.ndarray)):
                    for i, vi in enumerate(v):
                        if isinstance(vi, (int, float)):
                            self.main_dict_flat[prefix + k + ".%03d" % i] = vi

                # If v is a string, int, or float, enter it directly
                if isinstance(v, (int, np.integer, float)):
                    self.main_dict_flat[prefix + k] = v

    def close_output_file(self):
        """Properly close the output file."""
        if self.csv_file:
            self.flush_buffer()
            self.csv_file.flush()
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None

    def flush_buffer(self):
        """Write buffered rows to the file."""
        if not self.csv_buffer:
            return

        for row in self.csv_buffer:
            self.csv_writer.writerow(row)

        # Clear the buffer
        self.csv_buffer = []

    def log_main_dict(self):
        """
        Logs the current state of the main dictionary to a CSV file.

        """

        # Update the flattened input dict
        self.recursive_flatten_main_dict(self.main_dict)

        # Add the current time
        self.main_dict_flat["clock_time"] = dt.datetime.now()

        # The keys and values as two lists
        keys = list(self.main_dict_flat.keys())
        values = list(self.main_dict_flat.values())

        # Ensure the output file is open
        if not self.csv_file:
            self._open_output_file()

        # Handle header
        if not self.header_written:
            self.csv_writer.writerow(keys)
            self.header = keys
            self.header_written = True
        elif self.header != keys:
            self.logger.warning(
                "Input dict keys have changed since first iteration. Not writing to csv file."
            )
            return

        # Add the values to the buffer
        self.csv_buffer.append(values)

        # Flush if buffer is full
        if len(self.csv_buffer) >= self.csv_buffer_size:
            self.flush_buffer()

    def parse_input_yaml(self, filename):
        pass
