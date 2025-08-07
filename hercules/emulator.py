import datetime as dt
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

LOGFILE = str(dt.datetime.now()).replace(":", "_").replace(" ", "_").replace(".", "_")

Path("outputs").mkdir(parents=True, exist_ok=True)


class Emulator:
    def __init__(self, controller, hybrid_plant, h_dict, logger):
        """
        Initializes the emulator.

        Args:
            controller (object): The controller object responsible for managing the simulation.
            hybrid_plant (object): An object containing hybrid plant components.
            h_dict (dict): A dictionary contains parameters and values for the simulation.
            logger (object): A logger instance for logging messages during the simulation.

        """

        # Make sure output folder exists
        Path("outputs").mkdir(parents=True, exist_ok=True)

        # Use the provided logger
        self.logger = logger

        # Save the input dict to main dict
        self.h_dict = h_dict

        # Initialize the flattened h_dict
        self.h_dict_flat = {}

        # Initialize the output file
        if "output_file" in h_dict:
            self.output_file = h_dict["output_file"]
        else:
            self.output_file = "outputs/hercules_output.csv"

        # Initialize fast logging with pre-allocated arrays
        self.output_data = None
        self.output_columns = None
        self.output_structure_determined = False

        # Save time step, start time and end time
        self.dt = h_dict["dt"]
        self.starttime = h_dict["starttime"]
        self.endtime = h_dict["endtime"]

        # Get verbose flag from h_dict
        self.verbose = h_dict.get("verbose", False)
        self.total_simulation_time = self.endtime - self.starttime  # In seconds
        self.total_simulation_days = self.total_simulation_time / 86400
        self.time = self.starttime

        # Initialize the step
        self.step = 0
        self.n_steps = int(self.total_simulation_time / self.dt)

        # How often to update the user on current emulator time
        # In simulated time
        if "time_log_interval" in h_dict:
            self.time_log_interval = h_dict["time_log_interval"]
        else:
            self.time_log_interval = 600  # seconds
        self.step_log_interval = self.time_log_interval / self.dt

        # Round to step_log_interval to be an integer greater than 0
        self.step_log_interval = np.max([1, np.round(self.step_log_interval)])

        # Initialize components
        self.controller = controller
        self.hybrid_plant = hybrid_plant

        # Add plant component metadata to the h_dict
        self.h_dict = self.hybrid_plant.add_plant_metadata_to_h_dict(self.h_dict)

        # Read in any external data
        self.external_data_all = {}
        if "external_data_file" in h_dict:
            self._read_external_data_file(h_dict["external_data_file"])
            self.h_dict["external_signals"] = {}

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

    def _save_h_dict_as_text(self):
        """
        Save the main dictionary to a text file.

        This method redirects stdout to a file, prints the main dictionary, and then
        restores stdout to its original state. The dictionary is saved to
        'outputs/h_dict.echo' to help with log interpretation.
        """

        # Echo the dictionary to a separate file in case it is helpful
        # to see full dictionary in interpreting log

        original_stdout = sys.stdout
        with open("outputs/h_dict.echo", "w") as f_i:
            sys.stdout = f_i  # Change the standard output to the file we created.
            print(self.h_dict)
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

        # No need to open output file upfront with fast logging

        # Wrap this effort in a try block to ensure proper cleanup
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
                    f"{self.total_simulation_time / self.total_time_wall.total_seconds():.1f}",
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
            # Ensure output data is written to file
            self.logger.info("Writing output data to file")
            self.close_output_file()

    def run(self):
        """Run the main emulation loop until the end time is reached.

        Executes the simulation step by step, updating controller and Python
        simulators, logging state, and handling external data interpolation.
        Logs progress at specified intervals and saves initial state on first iteration.
        """
        self.logger.info(" #### Entering main loop #### ")

        first_iteration = True

        # Create progress bar
        progress_bar = tqdm(
            total=self.n_steps,
            desc="Simulation Progress",
            unit="steps",
            ncols=100,
            leave=True,
            mininterval=5.0,  # Update at most once every 5 seconds
            maxinterval=30.0,  # Update at least every 30 seconds
        )

        # Run simulation through steps
        for self.step in range(self.n_steps):
            # Compute the current time
            self.time = self.starttime + (self.step * self.dt)

            # Log the current time
            if (self.step % self.step_log_interval == 0) or first_iteration:
                self.logger.info(f"Emulator time: {self.time} (ending at {self.endtime})")
                self.logger.info(f"Step: {self.step} of {self.n_steps}")
                self.logger.info(f"--Percent completed: {100 * self.step / self.n_steps:.2f}%")
                # Update progress bar only when logging
                progress_bar.update(self.step_log_interval)

            for k in self.external_data_all:
                self.h_dict["external_signals"][k] = self.external_data_all[k][
                    self.external_data_all["time"] == self.time
                ][0]

            # Update controller and py sims
            self.h_dict["time"] = self.time
            self.h_dict["step"] = self.step
            self.h_dict = self.controller.step(self.h_dict)

            self.h_dict = self.hybrid_plant.step(self.h_dict)

            # Log the current state
            self.log_h_dict()

            # If this is first iteration log the input dict
            # And turn off the first iteration flag
            if first_iteration:
                self.logger.info(self.h_dict)
                self._save_h_dict_as_text()
                first_iteration = False

            # Update the time
            self.time = self.time + self.dt

        # Update progress bar to final step and close
        remaining_steps = self.n_steps - progress_bar.n
        if remaining_steps > 0:
            progress_bar.update(remaining_steps)
        progress_bar.close()

    def close_output_file(self):
        """Write all simulation data to CSV file at once with deferred rounding."""
        if self.output_data is not None and self.output_columns is not None:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(os.path.abspath(self.output_file))
            os.makedirs(output_dir, exist_ok=True)

            # Convert to DataFrame
            df = pd.DataFrame(self.output_data, columns=self.output_columns)

            # Apply rounding only once at CSV write time for better precision and performance
            # Round time to 1 decimal place for readability
            if "time" in df.columns:
                df["time"] = df["time"].round(1)

            # Round power and numeric values to 3 decimal places
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            for col in numeric_columns:
                if col not in ["time", "step"]:  # Skip time (already rounded) and step (integer)
                    df[col] = df[col].round(3)

            # Convert timestamp back to datetime string format
            if "clock_time" in df.columns:
                df["clock_time"] = pd.to_datetime(df["clock_time"], unit="s")

            # Write to CSV
            df.to_csv(self.output_file, index=False)

            if self.verbose:
                self.logger.info(f"Wrote {len(df)} rows to {self.output_file}")

    def __del__(self):
        """Cleanup method to properly close output files when object is destroyed."""
        self.close_output_file()

    def close(self):
        """Explicitly close all resources and cleanup."""
        self.close_output_file()

    def log_h_dict(self):
        """
        Logs the current state of the main dictionary using fast pre-allocated arrays.

        This method uses pre-allocated numpy arrays,
        writing all data to CSV only once at the end of simulation.
        """
        # Determine output structure on first call
        if not self.output_structure_determined:
            self._determine_output_structure()

        # Extract values directly into pre-allocated array
        self._extract_values_to_array()

    def _determine_output_structure(self):
        """Determine the output structure by analyzing current h_dict state."""
        # Build output columns list
        columns = []

        # Basic time information
        columns.extend(["time", "step", "clock_time"])

        # Plant-level outputs
        columns.extend(["plant.power", "plant.locally_generated_power"])

        # Component outputs
        for component_name in self.hybrid_plant.component_names:
            component_obj = self.hybrid_plant.component_objects[component_name]
            log_outputs = getattr(component_obj, "log_outputs", ["power"])

            for output_name in log_outputs:
                if output_name in self.h_dict[component_name]:
                    output_value = self.h_dict[component_name][output_name]

                    # Handle arrays by creating individual columns
                    if isinstance(output_value, (list, np.ndarray)):
                        for i in range(len(output_value)):
                            columns.append(f"{component_name}.{output_name}.{i:03d}")
                    else:
                        # Handle scalar values
                        columns.append(f"{component_name}.{output_name}")

        # Store column structure and allocate data array
        self.output_columns = columns
        self.output_data = np.full((self.n_steps, len(columns)), np.nan)
        self.output_structure_determined = True

        if self.verbose:
            self.logger.info(f"Determined output structure with {len(columns)} columns")

    def _extract_values_to_array(self):
        """Extract values from h_dict into the pre-allocated output array.

        Optimized version that eliminates expensive round() calls during simulation.
        Rounding is deferred to CSV write time for massive performance improvement.
        """
        if self.output_data is None:
            return

        row_data = []

        # Basic time information - only round time for readability
        row_data.append(self.h_dict["time"])  # Keep full precision during simulation
        row_data.append(self.h_dict["step"])
        row_data.append(dt.datetime.now().timestamp())

        # Plant-level outputs
        row_data.append(self.h_dict["plant"]["power"])
        row_data.append(self.h_dict["plant"]["locally_generated_power"])

        # Component outputs - store raw values without rounding
        for component_name in self.hybrid_plant.component_names:
            component_obj = self.hybrid_plant.component_objects[component_name]
            log_outputs = getattr(component_obj, "log_outputs", ["power"])

            for output_name in log_outputs:
                if output_name in self.h_dict[component_name]:
                    output_value = self.h_dict[component_name][output_name]

                    # Handle arrays - store raw values
                    if isinstance(output_value, (list, np.ndarray)):
                        row_data.extend(output_value)
                    else:
                        # Handle scalar values - store raw
                        row_data.append(output_value)

        # Store in pre-allocated array
        if len(row_data) == len(self.output_columns):
            self.output_data[self.step] = row_data
        else:
            self.logger.warning(
                f"Data length mismatch: expected {len(self.output_columns)}, got {len(row_data)}"
            )

    def parse_input_yaml(self, filename):
        """Parse input YAML file (not implemented).

        Args:
            filename (str): Path to the YAML file to parse.

        Raises:
            NotImplementedError: This method is not implemented.
        """
        raise NotImplementedError("parse_input_yaml is not implemented.")
