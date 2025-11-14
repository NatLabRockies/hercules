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

from hercules.hybrid_plant import HybridPlant
from hercules.utilities import (
    close_logging,
    hercules_float_type,
    interpolate_df,
    load_hercules_input,
    setup_logging,
)

LOGFILE = str(dt.datetime.now()).replace(":", "_").replace(" ", "_").replace(".", "_")

Path("outputs").mkdir(parents=True, exist_ok=True)


class HerculesModel:
    def __init__(self, input_file):
        """
        Initializes the HerculesModel.

        Args:
            input_file (Union[str, dict]): Path to Hercules input YAML file or dictionary
                containing input configuration.

        """

        # Make sure output folder exists
        Path("outputs").mkdir(parents=True, exist_ok=True)

        # Set up logging
        self.logger = self._setup_logging()

        # Load and validate the input file
        h_dict = self._load_hercules_input(input_file)

        # Initialize the flattened h_dict
        self.h_dict_flat = {}

        # Save time step, start time and end time first
        self.dt = h_dict["dt"]
        self.starttime = h_dict["starttime"]  # Always 0, computed from UTC
        self.endtime = h_dict["endtime"]  # Duration in seconds, computed from UTC

        # Save UTC timestamps
        self.starttime_utc = h_dict["starttime_utc"]
        self.endtime_utc = h_dict["endtime_utc"]

        # Initialize logging configuration
        self.log_every_n = h_dict.get("log_every_n", 1)
        self.dt_log = self.dt * self.log_every_n

        # Initialize the hybrid plant
        self.hybrid_plant = HybridPlant(h_dict)

        # Add plant component metadata to h_dict
        self.h_dict = self.hybrid_plant.add_plant_metadata_to_h_dict(h_dict)

        # Initialize the controller as None, to be assigned in a subsequent call
        self._controller = None

        # Read in any external data
        self.external_data_all = {}
        self.external_data_log_channels = None
        if "external_data" in self.h_dict:
            self._read_external_data_file(self.h_dict["external_data"]["external_data_file"])
            self.external_data_log_channels = self.h_dict["external_data"]["log_channels"]
            self.h_dict["external_signals"] = {}

        # Initialize HDF5 output configuration
        if "output_file" in self.h_dict:
            self.output_file = self.h_dict["output_file"]
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
        self.use_compression = self.h_dict.get("output_use_compression", True)

        # Buffering configuration
        # Buffer 10000 rows in memory (optimized default)
        self.buffer_size = self.h_dict.get("output_buffer_size", 50000)
        self.data_buffers = {}  # Dictionary to hold buffered data
        self.buffer_row = 0  # Current position in buffer

        # Get verbose flag from h_dict
        self.verbose = self.h_dict.get("verbose", False)
        self.total_simulation_time = self.endtime - self.starttime  # In seconds
        self.total_simulation_days = self.total_simulation_time / 86400
        self.time = self.starttime

        # Initialize the step
        self.step = 0
        self.n_steps = int(self.total_simulation_time / self.dt)

        # How often to update the user on current simulation time
        # In simulated time
        if "time_log_interval" in self.h_dict:
            self.time_log_interval = self.h_dict["time_log_interval"]
        else:
            self.time_log_interval = 600  # seconds
        self.step_log_interval = self.time_log_interval / self.dt

        # Round to step_log_interval to be an integer greater than 0
        self.step_log_interval = np.max([1, np.round(self.step_log_interval)])

        # Calculate progress bar update interval (independent of verbose logging)
        # Update every 1% of completion or every 100 steps, whichever is more frequent
        self.progress_update_interval = min(max(1, self.n_steps // 100), 100)

        # Save start time UTC (zero_time_utc is redundant since time=0 corresponds to starttime_utc)
        # starttime_utc is required and should already be set, but ensure it's still present
        self.starttime_utc = self.h_dict["starttime_utc"]

    def _setup_logging(self, logfile="log_hercules.log", console_output=True):
        """Set up logging to file and console.

        Creates 'outputs' directory and configures file/console logging with timestamps.
        This method wraps the utilities.setup_logging function for backward compatibility.

        Args:
            logfile (str, optional): Log file name. Defaults to "log_hercules.log".
            console_output (bool, optional): Enable console output. Defaults to True.

        Returns:
            logging.Logger: Configured logger instance.
        """
        return setup_logging(
            logger_name="hercules",
            log_file=logfile,
            console_output=console_output,
            console_prefix="HERCULES",
        )

    def _load_hercules_input(self, filename):
        """Load and validate Hercules input file.

        Loads YAML file and validates input structure, required keys, and data types.

        Args:
            filename (Union[str, dict]): Path to Hercules input YAML file or dictionary.

        Returns:
            dict: Validated Hercules input configuration with computed starttime/endtime.

        Raises:
            ValueError: If required keys missing, invalid data types, or incorrect structure.
        """
        h_dict = load_hercules_input(filename)

        # Add in starttime and endttime as needed for Hercules simulation
        h_dict["starttime"] = 0.0
        h_dict["endtime"] = (
            h_dict["endtime_utc"] - h_dict["starttime_utc"]
        ).total_seconds() + float(h_dict["dt"])

        return h_dict

    def _read_external_data_file(self, filename):
        """
        Read and interpolate external data from a CSV, feather, or pickle file.

        This method reads external data from the specified file (CSV, feather, or pickle)
        and interpolates it according to the simulation time steps. The external data must
        include a 'time_utc' column which will be converted to simulation time.
        The interpolated data is stored in self.external_data_all.

        Args:
            filename (str): Path to the file containing external data. Supported formats:
                - CSV files (.csv)
                - Feather files (.feather)
                - Pickle files (.pkl, .pickle)
        """

        # Determine file format from extension
        filename_lower = filename.lower()
        if filename_lower.endswith(".csv"):
            df_ext = pd.read_csv(filename)
        elif filename_lower.endswith((".feather", ".ftr")):
            df_ext = pd.read_feather(filename)
        elif filename_lower.endswith((".pickle", ".p", ".pkl")):
            df_ext = pd.read_pickle(filename)
        else:
            raise ValueError(
                f"Unsupported file format for '{filename}'. "
                "Supported formats: CSV (.csv), Feather (.ftr, .f, .feather), "
                "Pickle (.p, .pkl, .pickle)"
            )
        if "time_utc" not in df_ext.columns:
            raise ValueError("External data file must have a 'time_utc' column")

        # Convert time_utc to pandas datetime and then to simulation time
        df_ext["time_utc"] = pd.to_datetime(df_ext["time_utc"], utc=True)
        starttime_utc = pd.to_datetime(self.starttime_utc, utc=True)
        df_ext["time"] = (df_ext["time_utc"] - starttime_utc).dt.total_seconds()

        # Create simulation time array
        # Goes to 1 time step past stoptime specified in the input file.
        new_times = np.arange(
            self.starttime,
            self.endtime + (2 * self.dt),
            self.dt,
        )

        # Interpolate using the utility function
        df_interpolated = interpolate_df(df_ext, new_times)

        # Convert interpolated DataFrame to dictionary format
        for col in df_interpolated.columns:
            self.external_data_all[col] = df_interpolated[col].values

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

        # Store start time UTC information (required)
        # Convert pandas Timestamp to Unix timestamp for HDF5 compatibility
        if hasattr(self.starttime_utc, "timestamp"):
            metadata_group.attrs["starttime_utc"] = self.starttime_utc.timestamp()
        else:
            metadata_group.attrs["starttime_utc"] = self.starttime_utc

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
                # Only create dataset if signal should be logged
                should_log = (
                    self.external_data_log_channels is None
                    or signal_name in self.external_data_log_channels
                )
                if should_log:
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

    def assign_controller(self, controller):
        """
        Assign a controller instance to the HerculesModel.

        This method allows setting controller instance used in the simulation.
        It is useful when the controller needs to be initialized separately or changed after
        the HerculesModel has been created.

        Alternatively, the controller can be set directly using HerculesModel.controller = ...

        Args:
            controller (object): An instance of the controller to be used in the simulation.
        """
        if not hasattr(controller, "step"):
            raise ValueError(
                "Assigned controller does not have a 'step' method. ",
                "Ensure the controller is properly implemented.",
            )
        self._controller = controller

    @property
    def controller(self):
        """Get the assigned controller instance.

        Returns:
            object: The controller instance assigned to the HerculesModel.
        """
        return self._controller

    def run(self):
        """
        Execute the main simulation loop and handle timing and logging.

        This method runs the complete simulation from start to end, including timing calculations,
        progress logging, and resource cleanup. It executes the simulation step by step, updating
        controller and Python simulators, logging state, and handling external data interpolation.
        Ensures proper cleanup of resources even if exceptions occur during simulation.
        """

        # Check that a valid controller has been assigned
        if self._controller is None:
            raise ValueError(
                "No valid controller assigned to HerculesModel. ",
                "Call assign_controller() before running the simulation.",
            )

        # Wrap this effort in a try block to ensure proper cleanup
        try:
            # Record start clock time for metadata
            self.start_clock_time = _time.time()

            # Begin the main simulation loop
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
                        self.logger.info(f"Simulation time: {self.time} (ending at {self.endtime})")
                        self.logger.info(f"Step: {self.step} of {self.n_steps}")
                        percent_complete = 100 * self.step / self.n_steps
                        self.logger.info(f"--Percent completed: {percent_complete:.2f}%")

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
        """Cleanup method to properly close output files and logging when destroyed."""
        try:
            # Only attempt cleanup if Python is not shutting down
            import sys

            if sys.meta_path is not None:
                self._finalize_hdf5_file()
                if hasattr(self, "logger"):
                    close_logging(self.logger)
        except (ImportError, AttributeError):
            # Ignore errors during Python shutdown
            pass

    def close(self):
        """Explicitly close all resources and cleanup."""
        self._finalize_hdf5_file()
        if hasattr(self, "logger"):
            close_logging(self.logger)

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

        # Buffer external signals (only those specified in log_channels)
        if "external_signals" in self.h_dict and self.h_dict["external_signals"]:
            for signal_name, signal_value in self.h_dict["external_signals"].items():
                # Only buffer if signal should be logged
                should_log = (
                    self.external_data_log_channels is None
                    or signal_name in self.external_data_log_channels
                )
                if should_log:
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
