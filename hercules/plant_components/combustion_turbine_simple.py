"""
Combustion Turbine Simple Model.

A simple combustion turbine (natural gas peaker) model for hybrid plant simulations.

References:
[1] "Impact of Detailed Parameter Modeling of Open-Cycle Gas Turbines on
    Production Cost Simulation", NREL/CP-6A40-87554, National Renewable
    Energy Laboratory, 2024.
"""

import numpy as np
from hercules.plant_components.component_base import ComponentBase


class CombustionTurbineSimple(ComponentBase):
    """Simple combustion turbine (peaker) model.

    This model represents a natural gas combustion turbine with state
    management, ramp rate constraints, minimum stable load, and fuel consumption
    tracking. It is classified as a generator component.

    Note:
        All power units are in kW, heat rate in kJ/kWh, and ramp rates in kW/s.

    State Machine:
        state_num values and their meanings:
        - 0: "off" - Turbine is off, no power output
        - 1: "starting" - Turbine is ramping up to minimum stable load
        - 2: "on" - Turbine is operating normally
        - 3: "stopping" - Turbine is ramping down to shutdown
    """

    # State constants
    STATE_OFF = 0
    STATE_STARTING = 1
    STATE_ON = 2
    STATE_STOPPING = 3

    # Mapping from state number to state name
    STATE_NAMES = {
        STATE_OFF: "off",
        STATE_STARTING: "starting",
        STATE_ON: "on",
        STATE_STOPPING: "stopping",
    }

    @property
    def state_name(self):
        """Return the name of the current state.

        Returns:
            str: Current state name ("off", "starting", "on", or "stopping").
        """
        return self.STATE_NAMES[self.state_num]

    def __init__(self, h_dict):
        """Initialize the CombustionTurbineSimple class.

        Args:
            h_dict (dict): Dictionary containing simulation parameters including:
                - rated_capacity: Maximum power output in kW
                - min_stable_load: Minimum operating point as fraction (0-1)
                - heat_rate: Fuel consumption rate at rated load in kJ/kWh
                - ramp_rate_up: Maximum rate of power increase in kW/s
                - ramp_rate_down: Maximum rate of power decrease in kW/s
                - initial_conditions: Dictionary with initial power and state_num
                - startup_time: Optional, time to reach min_stable_load from off in s.
                    Default: 3600.0 (1 hour)
                - shutdown_time: Optional, time to shut down in s. Default: 3600.0 (1 hour)
                - min_up_time: Optional, minimum time unit must remain on in s.
                    Default: 3600.0 (1 hour)
                - min_down_time: Optional, minimum time unit must remain off in s.
                    Default: 3600.0 (1 hour)
                - part_load_factor: Optional, heat rate penalty at min load.
                    Default: 1.0 (no penalty)
        """
        # Store the name of this component
        self.component_name = "combustion_turbine"

        # Store the type of this component
        self.component_type = "CombustionTurbineSimple"

        # Call the base class init
        super().__init__(h_dict, self.component_name)

        # Extract required parameters
        self.rated_capacity = h_dict[self.component_name]["rated_capacity"]  # kW
        self.min_stable_load_fraction = h_dict[self.component_name]["min_stable_load"]
        self.heat_rate = h_dict[self.component_name]["heat_rate"]  # kJ/kWh
        self.ramp_rate_up = h_dict[self.component_name]["ramp_rate_up"]  # kW/s
        self.ramp_rate_down = h_dict[self.component_name]["ramp_rate_down"]  # kW/s

        # Check required parameters
        if self.rated_capacity <= 0:
            raise ValueError("rated_capacity must be greater than 0")
        if self.min_stable_load_fraction < 0 or self.min_stable_load_fraction > 1:
            raise ValueError("min_stable_load_fraction must be between 0 and 1 (inclusive)")
        if self.heat_rate <= 0:
            raise ValueError("heat_rate must be greater than 0")
        if self.ramp_rate_up <= 0 or self.ramp_rate_down <= 0:
            raise ValueError("ramp_rate_up and ramp_rate_down must be greater than 0")

        # Compute derived power limits
        self.P_min = self.min_stable_load_fraction * self.rated_capacity  # kW
        self.P_max = self.rated_capacity  # kW

        # Extract initial conditions
        initial_conditions = h_dict[self.component_name]["initial_conditions"]
        self.power_output = initial_conditions["power"]  # kW
        self.state_num = initial_conditions["state_num"]

        # Check that initial conditions are valid
        if self.power_output < 0 or self.power_output > self.rated_capacity:
            raise ValueError("power_output must be between 0 and rated_capacity (inclusive)")
        if self.state_num < 0 or self.state_num > 3:
            raise ValueError("state_num must be between 0 and 3 (inclusive)")
        if self.state_num not in self.STATE_NAMES:
            raise ValueError(
                "state_num must be one of the following: " + str(self.STATE_NAMES.values())
            )

        # Extract optional parameters with defaults
        # TODO: Based on [1] could differentiate hot start versus cold start
        self.startup_time = h_dict[self.component_name].get("startup_time", 3600.0)  # s
        self.shutdown_time = h_dict[self.component_name].get("shutdown_time", 3600.0)  # s
        self.min_up_time = h_dict[self.component_name].get("min_up_time", 3600.0)  # s
        self.min_down_time = h_dict[self.component_name].get("min_down_time", 3600.0)  # s
        self.part_load_factor = h_dict[self.component_name].get("part_load_factor", 1.0)

        # Check optional parameters
        if self.startup_time < 0:
            raise ValueError("startup_time must be greater than or equal to 0")
        if self.shutdown_time < 0:
            raise ValueError("shutdown_time must be greater than or equal to 0")
        if self.min_up_time < 0:
            raise ValueError("min_up_time must be greater than or equal to 0")
        if self.min_down_time < 0:
            raise ValueError("min_down_time must be greater than or equal to 0")
        if self.part_load_factor < 1 or self.part_load_factor > 2:
            raise ValueError("part_load_factor must be between 1.0 and 2.0")

        # State tracking
        self.time_in_state = 0.0  # s

        # Current step outputs
        self.fuel_consumption = 0.0  # kJ this timestep
        self.current_heat_rate = self.heat_rate  # kJ/kWh

        self.logger.info(
            "Initialized CombustionTurbineSimple: rated_capacity=%.1f kW, "
            "min_stable_load=%.1f%%, heat_rate=%.1f kJ/kWh",
            self.rated_capacity,
            self.min_stable_load_fraction * 100,
            self.heat_rate,
        )

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Add initial conditions and meta data to the h_dict.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Updated dictionary with initial conditions and meta data.
        """
        h_dict[self.component_name]["power"] = self.power_output
        h_dict[self.component_name]["state_num"] = self.state_num
        # h_dict[self.component_name]["state_name"] = self.state_name
        h_dict[self.component_name]["fuel_consumption"] = 0.0
        h_dict[self.component_name]["heat_rate"] = self.heat_rate

        return h_dict

    def step(self, h_dict):
        """Advance the combustion turbine simulation by one time step.

        Updates the turbine state including power output, state, and
        fuel consumption based on the requested power setpoint.

        Args:
            h_dict (dict): Dictionary containing simulation state including:
                - combustion_turbine.power_setpoint: Desired power output [kW]

        Returns:
            dict: Updated h_dict with combustion turbine outputs:
                - power: Actual power output [kW]
                - state_num: Operating state number (0=off, 1=starting, 2=on, 3=stopping)
                - state_name: Operating state string ("off", "starting", "on", "stopping")
                - fuel_consumption: Fuel consumed this timestep [kJ]
                - heat_rate: Current heat rate [kJ/kWh]
        """
        # Get power setpoint from controller
        power_setpoint = h_dict[self.component_name]["power_setpoint"]

        # Update time in current state
        self.time_in_state += self.dt

        # Determine actual power output based on constraints and state
        self.power_output = self._control(power_setpoint)

        # Calculate fuel consumption for this timestep
        self.fuel_consumption = self._calc_fuel_consumption(self.power_output)

        # Update h_dict with outputs
        h_dict[self.component_name]["power"] = self.power_output
        h_dict[self.component_name]["state_num"] = self.state_num
        # h_dict[self.component_name]["state_name"] = self.state_name
        h_dict[self.component_name]["fuel_consumption"] = self.fuel_consumption
        h_dict[self.component_name]["heat_rate"] = self.current_heat_rate

        return h_dict

    def _control(self, power_setpoint):
        """State machine for combustion turbine control.

        Handles state transitions, startup/shutdown ramps, and power constraints
        based on the current state (state_num) and time in that state.

        State Machine:
            STATE_OFF (0):
                - If setpoint > 0 and min_down_time satisfied: begin STARTING
                - Otherwise: remain OFF, output 0

            STATE_STARTING (1):
                - If setpoint <= 0: abort startup, return to OFF
                - Linear ramp from 0 to P_min over startup_time
                - When startup_power >= P_min: transition to ON

            STATE_ON (2):
                - If setpoint <= 0 and min_up_time satisfied: begin STOPPING
                - Otherwise: apply power limits and ramp rate constraints

            STATE_STOPPING (3):
                - Linear ramp from P_min to 0 over shutdown_time
                - When shutdown_power <= 0: transition to OFF

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
                # Transition to startup sequence
                self.state_num = self.STATE_STARTING
                self.time_in_state = 0.0

            return 0.0  # Power is always 0 when off

        # ====================================================================
        # STATE: STARTING
        # ====================================================================
        elif self.state_num == self.STATE_STARTING:
            # Check if startup should be aborted
            if power_setpoint <= 0:
                self.state_num = self.STATE_OFF
                self.time_in_state = 0.0
                self.power_output = 0.0
                return 0.0

            # Calculate startup power (linear ramp from 0 to P_min)
            if self.startup_time <= 0:
                startup_power = self.P_min  # Instant startup
            else:
                startup_progress = min(self.time_in_state / self.startup_time, 1.0)
                startup_power = startup_progress * self.P_min

            # Check if startup is complete
            if startup_power >= self.P_min:
                # Transition to on state
                self.state_num = self.STATE_ON
                self.time_in_state = 0.0

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
            # Calculate shutdown power (linear ramp from P_min to 0)
            if self.shutdown_time <= 0:
                shutdown_power = 0.0  # Instant shutdown
            else:
                shutdown_progress = min(self.time_in_state / self.shutdown_time, 1.0)
                shutdown_power = self.P_min * (1.0 - shutdown_progress)

            # Check if shutdown is complete
            if shutdown_power <= 0:
                self.state_num = self.STATE_OFF
                self.time_in_state = 0.0
                return 0.0

            return shutdown_power

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
        max_ramp_up = self.power_output + self.ramp_rate_up * self.dt
        max_ramp_down = self.power_output - self.ramp_rate_down * self.dt
        P_constrained = np.clip(P_constrained, max_ramp_down, max_ramp_up)

        return P_constrained

    def _calc_fuel_consumption(self, power_output):
        """Calculate fuel consumed based on power output and heat rate.

        Args:
            power_output (float): Current power output in kW.

        Returns:
            float: Fuel consumed this timestep in kJ.
        """

        # TODO: Is this correct?  Should we be getting to m^3 of natural gas?
        if power_output <= 0:
            self.current_heat_rate = self.heat_rate
            return 0.0

        # Calculate current heat rate with part-load penalty
        self.current_heat_rate = self._calc_heat_rate(power_output)

        # Fuel = Power * Heat Rate * dt
        # Units: kW * (kJ/kWh) * (s) * (h/3600s) = kJ
        fuel_kJ = power_output * self.current_heat_rate * (self.dt / 3600.0)

        return fuel_kJ

    def _calc_heat_rate(self, power_output):
        """Calculate heat rate accounting for part-load efficiency degradation.

        Uses linear interpolation between rated load (heat_rate) and minimum
        stable load (heat_rate * part_load_factor).

        Args:
            power_output (float): Current power output in kW.

        Returns:
            float: Current heat rate in kJ/kWh.
        """
        if power_output <= 0:
            return self.heat_rate

        if self.part_load_factor == 1.0:
            return self.heat_rate

        # Linear interpolation of efficiency penalty
        # At rated load: heat_rate
        # At min load: heat_rate * part_load_factor
        load_fraction = power_output / self.rated_capacity

        # Avoid division by zero if min_stable_load is 1.0
        if self.min_stable_load_fraction >= 1.0:
            return self.heat_rate

        # Linear interpolation
        # efficiency_penalty goes from part_load_factor at min_load to 1.0 at rated
        normalized_load = (load_fraction - self.min_stable_load_fraction) / (
            1.0 - self.min_stable_load_fraction
        )
        normalized_load = np.clip(normalized_load, 0.0, 1.0)

        efficiency_penalty = self.part_load_factor - (self.part_load_factor - 1.0) * normalized_load

        return self.heat_rate * efficiency_penalty
