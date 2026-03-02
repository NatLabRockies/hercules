# Base class for plant components in Hercules.


from typing import ClassVar

from hercules.utilities import setup_logging


class ComponentBase:
    """Base class for plant components.

    Provides common functionality for all Hercules plant components including logging setup,
    time step management, and shared configuration parameters.

    Subclasses must define the class attribute ``component_category`` with one of three
    values: ``"generator"``, ``"load"``, or ``"storage"``.  The per-instance
    ``component_name`` (the unique YAML key chosen by the user) is passed into ``__init__``
    and may differ from the category when multiple instances of the same type are present.
    ``component_type`` is always set automatically to the concrete class name.
    """

    # Subclasses must override this with one of: "generator", "load", "storage"
    component_category: ClassVar[str]

    # Valid component categories
    _ALLOWED_CATEGORIES = {"generator", "load", "storage"}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "component_category"):
            raise TypeError(f"{cls.__name__} must define a class attribute 'component_category'")

        value = cls.component_category
        if not isinstance(value, str):
            raise TypeError(
                f"{cls.__name__}.component_category must be a string in "
                f"{cls._ALLOWED_CATEGORIES}, got {type(value).__name__!r}: {value!r}"
            )
        if value not in cls._ALLOWED_CATEGORIES:
            raise TypeError(
                f"{cls.__name__}.component_category must be one of "
                f"{cls._ALLOWED_CATEGORIES}, got {value!r}"
            )

    def __init__(self, h_dict, component_name):
        """Initialize the base component with a dictionary of parameters.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
            component_name (str): Unique name for this component instance (the YAML top-level
                key).  For single-instance plants this is typically the category name (e.g.
                ``"battery"``); for multi-instance plants it may be any user-chosen string
                (e.g. ``"battery_unit_1"``).
        """

        # Store the component name (unique instance identifier from the YAML key)
        self.component_name = component_name

        # Derive component_type from the concrete class name — no hardcoding needed
        self.component_type = type(self).__name__

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
        """Set up logging for the component.


        Configures a logger to write to both file and console. Creates log directory
        if needed and clears any existing handlers to avoid duplicates.


        Args:
            log_file_name (str): Full path to the log file.

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
        """Cleanup method to properly close log file handlers."""
        if hasattr(self, "logger"):
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)

    def close_logging(self):
        """Explicitly close all log file handlers."""
        if hasattr(self, "logger"):
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
