# Base class for plant components in Hercules.


from hercules.utilities import setup_logging


class ComponentBase:
    """
    Base class for plant components.
    """

    def __init__(self, h_dict, component_name):
        """
        Initialize the base component with a dictionary of parameters.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
            component_name (str): Name of the component.
        """

        # Store the component name
        self.component_name = component_name

        # Set up logging
        # Check if log_file_name is defined in the h_dict[component_name]
        if "log_file_name" in h_dict[component_name]:
            self.log_file_name = h_dict[component_name]["log_file_name"]
        else:
            self.log_file_name = f"outputs/log_{component_name}.log"

        self.logger = self._setup_logging(self.log_file_name)

        # Parse log_channels from the h_dict
        if "log_channels" in h_dict[component_name]:
            log_channels_input = h_dict[component_name]["log_channels"]
            # Require list format
            if isinstance(log_channels_input, list):
                self.log_channels = log_channels_input
            else:
                raise TypeError(
                    f"log_channels must be a list, got {type(log_channels_input)}. "
                    f"Use YAML list format:\n"
                    f"  log_channels:\n"
                    f"    - power\n"
                    f"    - channel_name"
                )

            # If power is not in the list, add it
            if "power" not in self.log_channels:
                self.log_channels.append("power")
        else:
            # Default to just power if not specified
            self.log_channels = ["power"]

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
        Sets up logging for the component.

        This method configures a logger named after the component to log messages to a specified
        file and console. It ensures the log directory exists, clears any existing handlers to
        avoid duplicates, and formats log messages with timestamps, log levels, and messages.
        Both file and console output are enabled with component identification in console messages.
        This method wraps the utilities.setup_logging function for backward compatibility.

        Args:
            log_file_name (str): The full path to the log file where log messages will be written.
        Returns:
            logging.Logger: Configured logger instance for the component.
        """
        return setup_logging(
            logger_name=self.component_name,
            log_file=log_file_name,
            console_output=True,
            console_prefix=self.component_name.upper(),
            use_outputs_dir=False,  # log_file_name is already a full path
        )

    def __del__(self):
        """
        Cleanup method to properly close log file handlers.
        """
        if hasattr(self, "logger"):
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)

    def close_logging(self):
        """
        Explicitly close all log file handlers.
        """
        if hasattr(self, "logger"):
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
