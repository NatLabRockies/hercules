import datetime as dt
import json
import os
import sys
import time as _time
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from tqdm import tqdm

from hercules.utilities import hercules_float_type

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

        # Save time step, start time and end time first
        self.dt = h_dict["dt"]
        self.starttime = h_dict["starttime"]
        self.endtime = h_dict["endtime"]

        # Initialize logging configuration
        self.log_every_n = h_dict.get("log_every_n", 1)
        self.dt_log = self.dt * self.log_every_n

        # Initialize HDF5 output configuration
        if "output_file" in h_dict:
            self.output_file = h_dict["output_file"]
            # Ensure .h5 extension
            if not self.output_file.endswith(".h5"):
                self.output_file = self.output_file.rsplit(".", 1)[0] + ".h5"
        else:
            self.output_file = "outputs/hercules_output.h5"

        # Initialize HDF5 output system
        self.hdf5_file = None
        self.hdf5_datasets = {}
        self.output_structure_determined = False
        self.output_written = False
        self.current_row = 0
        self.total_rows_written = 0

        # HDF5 configuration
        # Enable/disable compression
        self.use_compression = h_dict.get("output_use_compression", True)

        # Buffering configuration
        # Buffer 10000 rows in memory (optimized default)
        self.buffer_size = h_dict.get("output_buffer_size", 50000)
        self.data_buffers = {}  # Dictionary to hold buffered data
        self.buffer_row = 0  # Current position in buffer

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

        # Calculate progress bar update interval (independent of verbose logging)
        # Update every 1% of completion or every 100 steps, whichever is more frequent
        self.progress_update_interval = min(max(1, self.n_steps // 100), 100)

        # Initialize components
        self.controller = controller
        self.hybrid_plant = hybrid_plant

        # Add plant component metadata to the h_dict
        self.h_dict = self.hybrid_plant.add_plant_metadata_to_h_dict(self.h_dict)

        # Save zero time and start time following add meta data
        self.zero_time_utc = h_dict.get("zero_time_utc", None)
        self.start_time_utc = h_dict.get("start_time_utc", None)

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

    def _initialize_hdf5_file(self):
        """Initialize HDF5 file with metadata and data structure."""

        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(os.path.abspath(self.output_file))
        os.makedirs(output_dir, exist_ok=True)

        # Open HDF5 file
        self.hdf5_file = h5py.File(self.output_file, "w")

        # Create metadata group
        metadata_group = self.hdf5_file.create_group("metadata")

        # Store h_dict as JSON string in attributes
        # Use a custom serializer that handles numpy types properly
        def numpy_serializer(obj):
            if hasattr(obj, "tolist"):  # numpy arrays
                return obj.tolist()
            elif hasattr(obj, "item"):  # numpy scalars
                return obj.item()
            else:
                return str(obj)

        h_dict_json = json.dumps(self.h_dict, default=numpy_serializer)
        metadata_group.attrs["h_dict"] = h_dict_json

        # Store simulation info
        metadata_group.attrs["starttime"] = self.starttime
        metadata_group.attrs["endtime"] = self.endtime
        metadata_group.attrs["dt_sim"] = self.dt
        metadata_group.attrs["dt_log"] = self.dt_log
        metadata_group.attrs["log_every_n"] = self.log_every_n
        metadata_group.attrs["total_simulation_time"] = self.total_simulation_time
        metadata_group.attrs["total_simulation_days"] = self.total_simulation_days

        # Store zero and start time UTC information if not None
        if self.zero_time_utc is not None:
            # Convert pandas Timestamp to Unix timestamp for HDF5 compatibility
            if hasattr(self.zero_time_utc, "timestamp"):
                metadata_group.attrs["zero_time_utc"] = self.zero_time_utc.timestamp()
            else:
                metadata_group.attrs["zero_time_utc"] = self.zero_time_utc
        if self.start_time_utc is not None:
            # Convert pandas Timestamp to Unix timestamp for HDF5 compatibility
            if hasattr(self.start_time_utc, "timestamp"):
                metadata_group.attrs["start_time_utc"] = self.start_time_utc.timestamp()
            else:
                metadata_group.attrs["start_time_utc"] = self.start_time_utc

        # Create data group
        data_group = self.hdf5_file.create_group("data")

        # Calculate total number of rows with logging stride
        total_rows = self.n_steps // self.log_every_n
        if self.n_steps % self.log_every_n != 0:
            total_rows += 1

        # Set compression parameters based on configuration
        if self.use_compression:
            # Optimized compression with chunking for better performance
            # Ensure chunk size doesn't exceed dataset size
            chunk_size = min(1000, self.buffer_size, total_rows)
            compression_params = {
                "compression": "gzip",
                "compression_opts": 6,  # Higher compression level
                "chunks": (chunk_size,),
            }
        else:
            compression_params = {}

        self.hdf5_datasets["time"] = data_group.create_dataset(
            "time",
            shape=(total_rows,),
            dtype=hercules_float_type,
            **compression_params,
        )

        self.hdf5_datasets["step"] = data_group.create_dataset(
            "step",
            shape=(total_rows,),
            dtype=np.int32,
            **compression_params,
        )

        # Create plant-level datasets
        self.hdf5_datasets["plant_power"] = data_group.create_dataset(
            "plant_power",
            shape=(total_rows,),
            dtype=hercules_float_type,
            **compression_params,
        )

        self.hdf5_datasets["plant_locally_generated_power"] = data_group.create_dataset(
            "plant_locally_generated_power",
            shape=(total_rows,),
            dtype=hercules_float_type,
            **compression_params,
        )

        # Create component datasets
        components_group = data_group.create_group("components")
        for component_name in self.hybrid_plant.component_names:
            component_obj = self.hybrid_plant.component_objects[component_name]

            for c in component_obj.log_channels:
                # First check if channel name ends with a 3-digit number after a period
                if len(c) >= 4 and c[-4] == "." and c[-3:].isdigit():
                    # In this case, we want a single index from within an array output
                    # For example, wind_farm.turbine_powers.000
                    # We want to create a dataset for this index
                    index = int(c[-3:])
                    channel_name = c[:-4]
                    channel_obj = self.h_dict[component_name][channel_name]
                    if isinstance(channel_obj, (list, np.ndarray)):
                        if index < len(channel_obj):
                            dataset_name = f"{component_name}.{channel_name}.{index:03d}"
                            self.hdf5_datasets[dataset_name] = components_group.create_dataset(
                                dataset_name,
                                shape=(total_rows,),
                                dtype=hercules_float_type,
                                **compression_params,
                            )
                        else:
                            raise ValueError(
                                (
                                    f"Index {index} is out of range for {channel_name} "
                                    f"in {component_name}"
                                )
                            )
                    else:
                        raise ValueError(
                            f"Channel {channel_name} is not an array in {component_name}"
                        )

                else:
                    # In this case, either the value is a scalar, or we want to log the entire array
                    if c in self.h_dict[component_name]:
                        output_value = self.h_dict[component_name][c]

                        if isinstance(output_value, (list, np.ndarray)):
                            # Handle arrays by creating individual datasets
                            arr = np.asarray(output_value)
                            for i in range(len(arr)):
                                dataset_name = f"{component_name}.{c}.{i:03d}"
                                self.hdf5_datasets[dataset_name] = components_group.create_dataset(
                                    dataset_name,
                                    shape=(total_rows,),
                                    dtype=hercules_float_type,
                                    **compression_params,
                                )
                        else:
                            # Handle scalar values
                            dataset_name = f"{component_name}.{c}"
                            self.hdf5_datasets[dataset_name] = components_group.create_dataset(
                                dataset_name,
                                shape=(total_rows,),
                                dtype=hercules_float_type,
                                **compression_params,
                            )
                    else:
                        raise ValueError(f"Output {c} not found in {component_name}")

        # Create external signals datasets
        if "external_signals" in self.h_dict and self.h_dict["external_signals"]:
            external_signals_group = data_group.create_group("external_signals")
            for signal_name in self.h_dict["external_signals"].keys():
                dataset_name = f"external_signals.{signal_name}"
                self.hdf5_datasets[dataset_name] = external_signals_group.create_dataset(
                    dataset_name,
                    shape=(total_rows,),
                    dtype=hercules_float_type,
                    **compression_params,
                )

        self.output_structure_determined = True

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
            # Record start clock time for metadata
            self.start_clock_time = _time.time()

            # Run the main loop
            self.run()

            # Note the total elapsed time

            self.end_clock_time = _time.time()
            self.total_time_wall = self.end_clock_time - self.start_clock_time

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
                    f"{self.total_simulation_time / self.total_time_wall:.1f}",
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
            self.logger.info("Finalizing HDF5 output file")
            self._finalize_hdf5_file()

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

        # Cache frequently accessed attributes and methods locally for speed
        controller_step = self.controller.step
        plant_step = self.hybrid_plant.step
        log_current_state = self._log_data_to_hdf5
        external_data_all = self.external_data_all
        h_dict = self.h_dict

        # Set current time and run simulation through steps
        self.time = self.starttime
        last_progress_update = 0
        for self.step in range(self.n_steps):
            # Log the current time
            if self.verbose:
                if (self.step % self.step_log_interval == 0) or first_iteration:
                    self.logger.info(f"Emulator time: {self.time} (ending at {self.endtime})")
                    self.logger.info(f"Step: {self.step} of {self.n_steps}")
                    self.logger.info(f"--Percent completed: {100 * self.step / self.n_steps:.2f}%")

            # Update progress bar independently of verbose logging, more frequently
            if (self.step % self.progress_update_interval == 0) or first_iteration:
                steps_to_update = self.step - last_progress_update
                if steps_to_update > 0:
                    progress_bar.update(steps_to_update)
                    last_progress_update = self.step

            # Fast external data lookup by step index (avoids per-step array equality checks)
            if external_data_all:
                for k in external_data_all:
                    if k == "time":
                        continue
                    h_dict["external_signals"][k] = external_data_all[k][self.step]

            # Update controller and py sims
            h_dict["time"] = self.time
            h_dict["step"] = self.step
            h_dict = controller_step(h_dict)
            h_dict = plant_step(h_dict)
            self.h_dict = h_dict

            # Log the current state
            log_current_state()

            # If this is first iteration log the input dict
            # And turn off the first iteration flag
            if first_iteration:
                # self.logger.info(self.h_dict)
                self._save_h_dict_as_text()
                first_iteration = False

            # Update the time
            self.time = self.time + self.dt

        # Update progress bar to final step and close
        final_steps_to_update = self.n_steps - last_progress_update
        if final_steps_to_update > 0:
            progress_bar.update(final_steps_to_update)
        progress_bar.close()

    def _finalize_hdf5_file(self):
        """Finalize HDF5 file with proper compression and metadata."""
        if self.output_written or self.hdf5_file is None:
            return

        try:
            # Flush any remaining buffered data
            if hasattr(self, "data_buffers") and self.data_buffers and self.buffer_row > 0:
                self._flush_buffer_to_hdf5()

            # Flush any remaining data
            if self.hdf5_file:
                self.hdf5_file.flush()

            # Add final metadata
            if self.hdf5_file:
                metadata_group = self.hdf5_file["metadata"]
                metadata_group.attrs["total_rows_written"] = self.total_rows_written
                metadata_group.attrs["hercules_version"] = "2.0"
                metadata_group.attrs["start_clock_time"] = getattr(
                    self, "start_clock_time", _time.time()
                )
                metadata_group.attrs["end_clock_time"] = getattr(
                    self, "end_clock_time", _time.time()
                )
                metadata_group.attrs["total_time_wall"] = getattr(
                    self, "total_time_wall", _time.time()
                )

            if self.verbose:
                file_size = os.path.getsize(self.output_file) / (1024 * 1024)  # MB
                self.logger.info(
                    f"Finalized HDF5 file: {self.output_file} "
                    f"({file_size:.2f} MB, {self.total_rows_written} rows)"
                )

        except Exception as e:
            self.logger.error(f"Error finalizing HDF5 file: {e}")
            raise
        finally:
            # Close HDF5 file
            if self.hdf5_file:
                self.hdf5_file.close()
                self.hdf5_file = None

        self.output_written = True

    def __del__(self):
        """Cleanup method to properly close output files when object is destroyed."""
        try:
            # Only attempt cleanup if Python is not shutting down
            import sys

            if sys.meta_path is not None:
                self._finalize_hdf5_file()
        except (ImportError, AttributeError):
            # Ignore errors during Python shutdown
            pass

    def close(self):
        """Explicitly close all resources and cleanup."""
        self._finalize_hdf5_file()

    def _log_data_to_hdf5(self):
        """
        Logs the  state of the main dict to memory buffers and writes to HDF5 periodically.

        This method buffers data in memory and only writes to disk when the buffer is full,
        significantly improving performance by reducing disk I/O frequency.
        """
        # Initialize HDF5 file on first call
        if not self.output_structure_determined:
            self._initialize_hdf5_file()

        # Apply  logging stride
        if self.step % self.log_every_n != 0:
            return

        # Initialize buffers on first call
        if not self.data_buffers:
            self._initialize_data_buffers()

        # Buffer basic time information
        self.data_buffers["time"][self.buffer_row] = self.h_dict["time"]
        self.data_buffers["step"][self.buffer_row] = self.h_dict["step"]

        # Buffer plant-level outputs
        self.data_buffers["plant_power"][self.buffer_row] = self.h_dict["plant"]["power"]
        self.data_buffers["plant_locally_generated_power"][self.buffer_row] = self.h_dict["plant"][
            "locally_generated_power"
        ]

        # Buffer component outputs
        for component_name in self.hybrid_plant.component_names:
            component_obj = self.hybrid_plant.component_objects[component_name]

            for c in component_obj.log_channels:
                # First check if channel ends in with a 3-digit number after a period
                if len(c) >= 4 and c[-4] == "." and c[-3:].isdigit():
                    # In this case, we want a single index from within an array output
                    # For example, wind_farm.turbine_powers.000
                    # We want to create a dataset for this index
                    index = int(c[-3:])
                    channel_name = c[:-4]
                    channel_obj = self.h_dict[component_name][channel_name]
                    if isinstance(channel_obj, (list, np.ndarray)):
                        if index < len(channel_obj):
                            dataset_name = f"{component_name}.{channel_name}.{index:03d}"
                            if dataset_name in self.data_buffers:
                                self.data_buffers[dataset_name][self.buffer_row] = channel_obj[
                                    index
                                ]
                    else:
                        raise ValueError(
                            f"Channel {channel_name} is not an array in {component_name}"
                        )
                else:
                    # In this case, either the value is a scalar, or we want to log the entire array
                    if c in self.h_dict[component_name]:
                        output_value = self.h_dict[component_name][c]

                        if isinstance(output_value, (list, np.ndarray)):
                            # Handle arrays by buffering to individual datasets
                            arr = np.asarray(output_value)
                            for i in range(len(arr)):
                                dataset_name = f"{component_name}.{c}.{i:03d}"
                                if dataset_name in self.data_buffers:
                                    self.data_buffers[dataset_name][self.buffer_row] = arr[i]
                        else:
                            # Handle scalar values
                            dataset_name = f"{component_name}.{c}"
                            if dataset_name in self.data_buffers:
                                self.data_buffers[dataset_name][self.buffer_row] = output_value

        # Buffer external signals
        if "external_signals" in self.h_dict and self.h_dict["external_signals"]:
            for signal_name, signal_value in self.h_dict["external_signals"].items():
                dataset_name = f"external_signals.{signal_name}"
                if dataset_name in self.data_buffers:
                    self.data_buffers[dataset_name][self.buffer_row] = signal_value

        # Increment buffer row counter
        self.buffer_row += 1
        self.total_rows_written += 1

        # Write buffer to disk when full
        if self.buffer_row >= self.buffer_size:
            self._flush_buffer_to_hdf5()

    def _initialize_data_buffers(self):
        """Initialize memory buffers for all datasets."""
        for dataset_name in self.hdf5_datasets.keys():
            if dataset_name == "step":
                # Integer buffer for step
                self.data_buffers[dataset_name] = np.zeros(self.buffer_size, dtype=np.int32)
            else:
                # Float buffer for everything else
                self.data_buffers[dataset_name] = np.zeros(
                    self.buffer_size, dtype=hercules_float_type
                )

    def _flush_buffer_to_hdf5(self):
        """Write buffered data to HDF5 datasets and reset buffer."""
        if self.buffer_row == 0:
            return  # Nothing to flush

        # Calculate the range to write
        start_row = self.current_row
        end_row = start_row + self.buffer_row

        # Pre-filter valid datasets to avoid redundant lookups
        valid_datasets = {
            name: buffer_data
            for name, buffer_data in self.data_buffers.items()
            if name in self.hdf5_datasets
        }

        # Write all buffered data at once (optimized)
        for dataset_name, buffer_data in valid_datasets.items():
            # Use direct slice assignment without creating intermediate views
            self.hdf5_datasets[dataset_name][start_row:end_row] = buffer_data[: self.buffer_row]

        # Update current row position
        self.current_row = end_row

        # Reset buffer
        self.buffer_row = 0
