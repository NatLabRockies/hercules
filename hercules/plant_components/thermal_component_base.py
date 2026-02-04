"""
Thermal Plant Base Class.

A base class for thermal plant components.  Based primarily on the parameterized model
presented in [1] but using some names and parameters from [2] and [3].  Table 1
on page 48 of [1] provides many of the default values for the parameters.

References:

[1] Agora Energiewende (2017): Flexibility in thermal power plants
     With a focus on existing coal-fired power plants.
[2] "Impact of Detailed Parameter Modeling of Open-Cycle Gas Turbines on
    Production Cost Simulation", NREL/CP-6A40-87554, National Renewable
    Energy Laboratory, 2024.
[3] Deane, J.P., G. Drayton, and B.P. Ó Gallachóir. “The Impact of Sub-Hourly
    Modelling in Power Systems with Significant Levels of Renewable Generation.”
     Applied Energy 113 (January 2014): 152–58.
     https://doi.org/10.1016/j.apenergy.2013.07.027.

"""

import numpy as np
from hercules.plant_components.component_base import ComponentBase


class ThermalComponentBase(ComponentBase):
    """Base class for thermal power plant components.

    This class provides common functionality for all thermal plant components,
    including power output calculation and ramp rate constraints.

    Note: All power units are in kW.

    Note: The base class does not provide default values of inputs.
    Subclasses must provide these in the h_dict.

    State Machine:
        state_num values and their meanings:
        - 0: "off" - Thermal Component is off, no power output
        - 1: "hot starting" - Thermal Component is readying or ramping up to minimum
            stable load from off state (hot start)
        - 2: "cold starting" - Thermal Component is readying or ramping up to minimum
            stable load from off state (cold start)
        - 3: "on" - Thermal Component is operating normally
        - 4: "stopping" - Thermal Component is ramping down to shutdown


    """

    # State constants
    STATE_OFF = 0
    STATE_HOT_STARTING = 1
    STATE_COLD_STARTING = 2
    STATE_ON = 3
    STATE_STOPPING = 4

    # Mapping from state number to state name
    STATE_NAMES = {
        STATE_OFF: "off",
        STATE_HOT_STARTING: "hot starting",
        STATE_COLD_STARTING: "cold starting",
        STATE_ON: "on",
        STATE_STOPPING: "stopping",
    }

    @property
    def state_name(self):
        """Return the name of the current state.

        Returns:
            str: Current state name ("off", "hot starting", "cold starting",
                "on", or "stopping").
        """
        return self.STATE_NAMES[self.state_num]

    def __init__(self, h_dict):
        """Initialize the ThermalComponentBase class.

        Args:
            h_dict (dict): Dictionary containing simulation parameters including:
                - rated_capacity: Maximum power output in kW
                - min_stable_load_fraction: Minimum operating point as fraction (0-1)
                - ramp_rate_fraction: Maximum rate of power increase/decrease
                    as fraction of rated capacity per minute
                - run_up_rate_fraction: Maximum rate of power increase during startup
                    as fraction of rated capacity per minute.
                - hot_startup_time: Time to reach min_stable_load_fraction from off in s.
                    Includes both readying time and ramping time.
                - cold_startup_time: Time to reach min_stable_load_fraction from off in s.
                    Includes both readying time and ramping time.
                - hot_cold_cutoff_time: Time in off after which cold starting is implied
                    in s.
                - min_up_time: Minimum time unit must remain on in s.
                - min_down_time: Minimum time unit must remain off in s.
                - initial_conditions: Dictionary with initial power and state_num
        """

        # Both the component name and type are defined in the subclass
        # But for testing purposes, we need to set the component name here
        # if not defined in the subclass
        if not hasattr(self, "component_name"):
            self.component_name = "thermal_component"
        if not hasattr(self, "component_type"):
            self.component_type = "ThermalComponentBase"

        # Call the base class init
        super().__init__(h_dict, self.component_name)

        # Extract parameters from the h_dict
        component_dict = h_dict[self.component_name]
        self.rated_capacity = component_dict["rated_capacity"]  # kW
        self.min_stable_load_fraction = component_dict["min_stable_load_fraction"]
        self.ramp_rate_fraction = component_dict["ramp_rate_fraction"]
        self.run_up_rate_fraction = component_dict["run_up_rate_fraction"]
        self.hot_startup_time = component_dict["hot_startup_time"]  # s
        self.cold_startup_time = component_dict["cold_startup_time"]  # s
        self.hot_cold_cutoff_time = component_dict["hot_cold_cutoff_time"]  # s
        self.min_up_time = component_dict["min_up_time"]  # s
        self.min_down_time = component_dict["min_down_time"]  # s

        # Check all required parameters are numbers
        if not isinstance(self.rated_capacity, (int, float)):
            raise ValueError("rated_capacity must be a number")
        if not isinstance(self.min_stable_load_fraction, (int, float)):
            raise ValueError("min_stable_load_fraction must be a number")
        if not isinstance(self.ramp_rate_fraction, (int, float)):
            raise ValueError("ramp_rate_fraction must be a number")
        if not isinstance(self.run_up_rate_fraction, (int, float)):
            raise ValueError("run_up_rate_fraction must be a number")
        if not isinstance(self.hot_startup_time, (int, float)):
            raise ValueError("hot_startup_time must be a number")
        if not isinstance(self.cold_startup_time, (int, float)):
            raise ValueError("cold_startup_time must be a number")
        if not isinstance(self.hot_cold_cutoff_time, (int, float)):
            raise ValueError("hot_cold_cutoff_time must be a number")
        if not isinstance(self.min_up_time, (int, float)):
            raise ValueError("min_up_time must be a number")
        if not isinstance(self.min_down_time, (int, float)):
            raise ValueError("min_down_time must be a number")

        # Check parameters
        if self.rated_capacity <= 0:
            raise ValueError("rated_capacity must be greater than 0")
        if self.min_stable_load_fraction < 0 or self.min_stable_load_fraction > 1:
            raise ValueError("min_stable_load_fraction must be between 0 and 1 (inclusive)")
        if self.ramp_rate_fraction <= 0:
            raise ValueError("ramp_rate_fraction must be greater than 0")
        if self.run_up_rate_fraction <= 0:
            raise ValueError("run_up_rate_fraction must be greater than 0")
        if self.hot_startup_time < 0:
            raise ValueError("hot_startup_time must be greater than or equal to 0")
        if self.cold_startup_time < 0:
            raise ValueError("cold_startup_time must be greater than or equal to 0")
        if self.hot_cold_cutoff_time < 0:
            raise ValueError("hot_cold_cutoff_time must be greater than or equal to 0")
        if self.min_up_time < 0:
            raise ValueError("min_up_time must be greater than or equal to 0")
        if self.min_down_time < 0:
            raise ValueError("min_down_time must be greater than or equal to 0")

        # Compute derived power limits
        self.P_min = self.min_stable_load_fraction * self.rated_capacity  # kW
        self.P_max = self.rated_capacity  # kW

        # Compute ramp_rate and run_up_rate in kW/s
        self.ramp_rate = self.ramp_rate_fraction * self.rated_capacity / 60.0  # kW/s
        self.run_up_rate = self.run_up_rate_fraction * self.rated_capacity / 60.0  # kW/s

        # Compute the ramp_time, which is the time to ramp from 0 to P_min
        # using the run_up_rate
        self.ramp_time = self.P_min / self.run_up_rate  # s

        # Check that hot_startup_time is greater than or equal to the ramp_time
        if self.hot_startup_time < self.ramp_time:
            raise ValueError("hot_startup_time must be greater than or equal to the ramp_time")

        # Check that the cold_startup_time is at least as long as the hot_startup_time
        if self.cold_startup_time < self.hot_startup_time:
            raise ValueError("cold_startup_time must be greater than or equal to hot_startup_time")

        # Compute the hot and cold readying times, which is the startup time minus the ramp_time
        self.hot_readying_time = self.hot_startup_time - self.ramp_time  # s
        self.cold_readying_time = self.cold_startup_time - self.ramp_time  # s

        # Extract initial conditions
        initial_conditions = h_dict[self.component_name]["initial_conditions"]
        self.power_output = initial_conditions["power"]  # kW
        self.state_num = initial_conditions["state_num"]

        # Check that initial conditions are valid
        if self.power_output < 0 or self.power_output > self.rated_capacity:
            raise ValueError(
                "initial_conditions['power'] (initial power) "
                "must be between 0 and rated_capacity (inclusive)"
            )
        if self.state_num not in self.STATE_NAMES:
            raise ValueError(
                f"initial_conditions['state_num'] must be one of {list(self.STATE_NAMES.keys())}"
            )

        # State tracking
        self.time_in_state = 0.0  # s

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Add any initial conditions or meta data to the h_dict.

        This is an abstract method that must be implemented by subclasses.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Updated dictionary with initial conditions and meta data.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError(
            "Subclasses must implement get_initial_conditions_and_meta_data()"
        )

    def step(self, h_dict):
        """Advance the thermal component simulation by one time step.

        Updates the thermal component state including power output, state, and
        based on the requested power setpoint.

        Args:
            h_dict (dict): Dictionary containing simulation state including:
                - self.component_name.power_setpoint: Desired power output [kW]

        Returns:
            dict: Updated h_dict with thermal component outputs:
                - power: Actual power output [kW]
                - state_num: Operating state number (0=off, 1=hot starting,
                    2=cold starting, 3=on, 4=stopping)

        """
        # Get power setpoint from controller
        power_setpoint = h_dict[self.component_name]["power_setpoint"]

        # Check that the power setpoint is a number
        if not isinstance(power_setpoint, (int, float)):
            raise ValueError("power_setpoint must be a number")

        # Update time in current state
        self.time_in_state += self.dt

        # Determine actual power output based on constraints and state
        self.power_output = self._control(power_setpoint)

        # Apply post-processing specific to the sub-class
        h_dict = self._post_process(h_dict)

        # Update h_dict with outputs
        h_dict[self.component_name]["power"] = self.power_output
        h_dict[self.component_name]["state_num"] = self.state_num

        return h_dict

    def _control(self, power_setpoint):
        """State machine for thermal component control.

        Handles state transitions, startup/shutdown ramps, and power constraints
        based on the current state (state_num) and time in that state.

        State Machine:
            STATE_OFF (0):
                - If setpoint > 0 and min_down_time satisfied and hot_cold_cutoff_time
                    not exceeded: begin HOT_STARTING
                - If setpoint > 0 and min_down_time satisfied and hot_cold_cutoff_time
                    exceeded: begin COLD_STARTING
                - Otherwise: remain OFF, output 0

            STATE_HOT_STARTING (1):
                - If setpoint <= 0: abort startup, return to OFF
                - If time in state is less than hot_readying_time output 0
                - After hot_readying_time, ramp up to P_min using run_up_rate
                - When power output >= P_min: transition to STATE_ON

            STATE_COLD_STARTING (2):
                - If setpoint <= 0: abort startup, return to OFF
                - If time in state is less than cold_readying_time output 0
                - After cold_readying_time, ramp up to P_min using run_up_rate
                - When power output >= P_min: transition to STATE_ON

            STATE_ON (3):
                - If setpoint <= 0 and min_up_time satisfied: begin STOPPING
                - Otherwise: apply power limits and ramp rate constraints

            STATE_STOPPING (4):
                - Ramp to 0 using ramp_rate
                - When power output <= 0: transition to STATE_OFF

        Args:
            power_setpoint (float): Desired power output in kW.

        Returns:
            float: Actual constrained power output in kW.
        """
        # ====================================================================
        # STATE: OFF
        # ====================================================================
        if self.state_num == self.STATE_OFF:
            # Check if we can start (min_down_time satisfied)
            can_start = self.time_in_state >= self.min_down_time

            if power_setpoint > 0 and can_start:
                # Check if hot or cold starting is implied
                if self.time_in_state < self.hot_cold_cutoff_time:
                    self.state_num = self.STATE_HOT_STARTING
                else:
                    self.state_num = self.STATE_COLD_STARTING
                self.time_in_state = 0.0

            return 0.0  # Power is always 0 when off

        # ====================================================================
        # STATE: HOT_STARTING
        # ====================================================================
        elif self.state_num == self.STATE_HOT_STARTING:
            # Check if startup should be aborted
            if power_setpoint <= 0:
                self.state_num = self.STATE_OFF
                self.time_in_state = 0.0
                self.power_output = 0.0
                return 0.0

            # Check if readying time is complete
            if self.time_in_state < self.hot_readying_time:
                return 0.0

            # Ramp up using run_up_rate
            startup_power = (self.time_in_state - self.hot_readying_time) * self.run_up_rate

            # Check if ramping is complete
            if startup_power >= self.P_min:
                self.state_num = self.STATE_ON
                self.time_in_state = 0.0
                return startup_power

            return startup_power

        # ====================================================================
        # STATE: COLD_STARTING
        # ====================================================================
        elif self.state_num == self.STATE_COLD_STARTING:
            # Check if startup should be aborted
            if power_setpoint <= 0:
                self.state_num = self.STATE_OFF
                self.time_in_state = 0.0
                self.power_output = 0.0
                return 0.0

            # Check if readying time is complete
            if self.time_in_state < self.cold_readying_time:
                return 0.0

            # Ramp up using run_up_rate
            startup_power = (self.time_in_state - self.cold_readying_time) * self.run_up_rate

            # Check if ramping is complete
            if startup_power >= self.P_min:
                self.state_num = self.STATE_ON
                self.time_in_state = 0.0
                return startup_power

            return startup_power

        # ====================================================================
        # STATE: ON
        # ====================================================================
        elif self.state_num == self.STATE_ON:
            # Check if we can shut down (min_up_time satisfied)
            can_shutdown = self.time_in_state >= self.min_up_time

            if power_setpoint <= 0 and can_shutdown:
                # Transition to shutdown sequence
                self.state_num = self.STATE_STOPPING
                self.time_in_state = 0.0

            # Apply constraints for on operation
            return self._apply_on_constraints(power_setpoint)

        # ====================================================================
        # STATE: STOPPING
        # ====================================================================
        elif self.state_num == self.STATE_STOPPING:
            # Ramp the power output down using ramp_rate
            shutdown_power = self.power_output - self.ramp_rate * self.dt

            # Check if shutdown is complete
            if shutdown_power <= 0:
                self.state_num = self.STATE_OFF
                self.time_in_state = 0.0
                return 0.0

            return shutdown_power

        else:
            raise ValueError(f"Unexpected state_num in _control: {self.state_num}")

    def _apply_on_constraints(self, power_setpoint):
        """Apply power and ramp rate constraints when unit is on.

        Args:
            power_setpoint (float): Desired power output in kW.

        Returns:
            float: Constrained power output in kW.
        """
        # Apply power limits
        P_constrained = np.clip(power_setpoint, self.P_min, self.P_max)

        # Apply ramp rate constraints
        max_ramp_up = self.power_output + self.ramp_rate * self.dt
        max_ramp_down = self.power_output - self.ramp_rate * self.dt
        P_constrained = np.clip(P_constrained, max_ramp_down, max_ramp_up)

        return P_constrained

    # Define the _post_process as an abstract method that does nothing to be
    # overridden by the subclass.  However don't raise an error if it is not overridden.
    def _post_process(self, h_dict):
        """Post-process the thermal component simulation.

        This is an abstract method that can be implemented by subclasses.  If not
        overridden, the default behavior is to do nothing.

        Args:
            h_dict (dict): Dictionary containing simulation state.

        Returns:
            dict: Updated dictionary with post-processed simulation state.
        """
        return h_dict
