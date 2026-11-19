"""
Thermal Plant Base Class.

A base class for thermal plant components.  Based primarily on the parameterized model
presented in [1] but using some names and parameters from [2] and [3].  Table 1
on page 48 of [1] provides many of the default values for the parameters.

Note: All efficiency values in this module are HHV (Higher Heating Value) net plant
efficiencies, consistent with the data in Exhibit ES-4 of [5].

References:

[1] Agora Energiewende (2017): Flexibility in thermal power plants
     With a focus on existing coal-fired power plants.
[2] "Impact of Detailed Parameter Modeling of Open-Cycle Gas Turbines on
    Production Cost Simulation", NREL/CP-6A40-87554, National Renewable
    Energy Laboratory, 2024.
[3] Deane, J.P., G. Drayton, and B.P. Ó Gallachóir. "The Impact of Sub-Hourly
    Modelling in Power Systems with Significant Levels of Renewable Generation."
     Applied Energy 113 (January 2014): 152–58.
     https://doi.org/10.1016/j.apenergy.2013.07.027.
[4] IRENA (2019), Innovation landscape brief: Flexibility in conventional power plants,
    International Renewable Energy Agency, Abu Dhabi.
[5] M. Oakes, M. Turner, " Cost and Performance Baseline for Fossil Energy Plants, Volume 5:
    Natural Gas Electricity Generating Units for Flexible Operation," National Energy
    Technology Laboratory, Pittsburgh, May 5, 2023.
[6] I. Staffell, "The Energy and Fuel Data Sheet," University of Birmingham, March 2011.
    https://claverton-energy.com/cms4/wp-content/uploads/2012/08/the_energy_and_fuel_data_sheet.pdf

"""

from enum import IntEnum

import numpy as np
from hercules.plant_components.component_base import ComponentBase
from hercules.utilities import hercules_float_type


class ThermalComponentBase(ComponentBase):
    """Base class for thermal power plant components.

    This class provides common functionality for all thermal plant components,
    including power output calculation and ramp rate constraints.

    Note: All power units are in kW.

    Note: The base class does not provide default values of inputs.
    Subclasses must provide these in the h_dict.

    State Machine:
        state values (IntEnum) and their meanings:
        - 0 (OFF_HOT): Thermal Component is off and still hot
            (time_in_state < cooldown_time_warm)
        - 1 (HOT_STARTING): Thermal Component is readying or ramping up to minimum
            stable load from off state (hot start)
        - 2 (WARM_STARTING): Thermal Component is readying or ramping up to minimum
            stable load from off state (warm start)
        - 3 (COLD_STARTING): Thermal Component is readying or ramping up to minimum
            stable load from off state (cold start)
        - 4 (ON): Thermal Component is operating normally
        - 5 (STOPPING): Thermal Component is ramping down to shutdown
        - 6 (OFF_WARM): Thermal Component is off and warm
            (cooldown_time_warm <= time_in_state < cooldown_time_cold)
        - 7 (OFF_COLD): Thermal Component is off and cold
            (time_in_state >= cooldown_time_cold)


    """

    component_category = "generator"

    class STATES(IntEnum):
        """Enumeration of thermal component operating states."""

        OFF_COLD = 0
        COLD_STARTING = 1
        OFF_WARM = 2
        WARM_STARTING = 3
        OFF_HOT = 4
        HOT_STARTING = 5
        ON = 6
        STOPPING = 7

        @property
        def label(self):
            """Return a human-readable label for the state."""
            return self.name.replace("_", " ").title()

    def _is_off(self):
        """Return True if the unit is in any OFF substate."""
        return self.state in (
            self.STATES.OFF_HOT,
            self.STATES.OFF_WARM,
            self.STATES.OFF_COLD,
        )

    def _classify_off_state(self):
        """Set the OFF substate based on time_in_state and cooldown thresholds."""
        if self.time_in_state < self.cooldown_time_warm:
            self.state = self.STATES.OFF_HOT
        elif self.time_in_state < self.cooldown_time_cold:
            self.state = self.STATES.OFF_WARM
        else:
            self.state = self.STATES.OFF_COLD

    def __init__(self, h_dict, component_name):
        """Initialize the ThermalComponentBase class.

        Args:
            h_dict (dict): Dictionary containing simulation parameters including:
                - capacity_rated: Maximum power output in kW
                - load_stable_min_fraction: Minimum operating point as fraction (0-1)
                - ramp_rate_fraction_per_min: Maximum rate of power increase/decrease
                    as fraction of rated capacity per minute
                - run_up_rate_fraction_per_min: Maximum rate of power increase during startup
                    as fraction of rated capacity per minute.
                - startup_time_hot: Time to reach load_stable_min_fraction from off in s.
                    Includes both readying time and ramping time.
                - startup_time_warm: Time to reach load_stable_min_fraction from off in s.
                    Includes both readying time and ramping time.
                - startup_time_cold: Time to reach load_stable_min_fraction from off in s.
                    Includes both readying time and ramping time.
                - up_time_min: Minimum time unit must remain on in s.
                - down_time_min: Minimum time unit must remain off in s.
                - cooldown_time_warm: Optional, time after shutdown before the unit
                    transitions from hot to warm state in s. Default: 28800.0 (8 hours).
                - cooldown_time_cold: Optional, time after shutdown before the unit
                    transitions from warm to cold state in s. Default: 172800.0 (48 hours).
                - initial_conditions: Dictionary with initial power (state is
                    derived automatically: power > 0 means ON, power == 0 means OFF)
                - HHV: Higher heating value of fuel in J/m³
                - fuel_density: Fuel density in kg/m³
                - efficiency_table: Dictionary with power_fraction and efficiency arrays
                    (both as fractions 0-1). Efficiency values must be HHV net plant
                    efficiencies.
            component_name (str): Unique name for this instance (the YAML top-level key).
        """

        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)

        # Extract parameters from the h_dict
        component_dict = h_dict[self.component_name]
        self.capacity_rated = component_dict["capacity_rated"]  # kW
        self.load_stable_min_fraction = component_dict["load_stable_min_fraction"]
        self.ramp_rate_fraction_per_min = component_dict["ramp_rate_fraction_per_min"]
        self.run_up_rate_fraction_per_min = component_dict["run_up_rate_fraction_per_min"]
        self.startup_time_hot = component_dict["startup_time_hot"]  # s
        self.startup_time_warm = component_dict["startup_time_warm"]  # s
        self.startup_time_cold = component_dict["startup_time_cold"]  # s
        self.up_time_min = component_dict["up_time_min"]  # s
        self.down_time_min = component_dict["down_time_min"]  # s

        # Cooldown threshold times (optional, with defaults matching [5])
        self.cooldown_time_warm = component_dict.get("cooldown_time_warm", 28800.0)  # s (8h)
        self.cooldown_time_cold = component_dict.get("cooldown_time_cold", 172800.0)  # s (48h)
        # Extract optional parameters for startup and shutdown fuel fractions
        self.fuel_startup_fraction = component_dict.get("fuel_startup_fraction", None)
        self.fuel_shutdown_fraction = component_dict.get("fuel_shutdown_fraction", None)

        # Check all required parameters are numbers
        numeric_params = {
            "capacity_rated": self.capacity_rated,
            "load_stable_min_fraction": self.load_stable_min_fraction,
            "ramp_rate_fraction_per_min": self.ramp_rate_fraction_per_min,
            "run_up_rate_fraction_per_min": self.run_up_rate_fraction_per_min,
            "startup_time_hot": self.startup_time_hot,
            "startup_time_warm": self.startup_time_warm,
            "startup_time_cold": self.startup_time_cold,
            "up_time_min": self.up_time_min,
            "down_time_min": self.down_time_min,
            "cooldown_time_warm": self.cooldown_time_warm,
            "cooldown_time_cold": self.cooldown_time_cold,
        }
        for name, value in numeric_params.items():
            if not isinstance(value, (int, float, hercules_float_type)):
                raise ValueError(f"{name} must be a number")

        # Check parameters
        if self.capacity_rated <= 0:
            raise ValueError("capacity_rated must be greater than 0")
        if self.load_stable_min_fraction < 0 or self.load_stable_min_fraction > 1:
            raise ValueError("load_stable_min_fraction must be between 0 and 1 (inclusive)")
        if self.ramp_rate_fraction_per_min <= 0:
            raise ValueError("ramp_rate_fraction_per_min must be greater than 0")
        if self.run_up_rate_fraction_per_min <= 0:
            raise ValueError("run_up_rate_fraction_per_min must be greater than 0")
        for name in [
            "startup_time_hot",
            "startup_time_warm",
            "startup_time_cold",
            "up_time_min",
            "down_time_min",
            "cooldown_time_warm",
            "cooldown_time_cold",
        ]:
            if numeric_params[name] < 0:
                raise ValueError(f"{name} must be greater than or equal to 0")
        if self.cooldown_time_cold < self.cooldown_time_warm:
            raise ValueError(
                "cooldown_time_cold must be greater than or equal to cooldown_time_warm"
            )

        # Compute derived power limits
        self.power_min = self.load_stable_min_fraction * self.capacity_rated  # kW
        self.power_max = self.capacity_rated  # kW

        # Compute ramp_rate and run_up_rate in kW/s
        self.ramp_rate = self.ramp_rate_fraction_per_min * self.capacity_rated / 60.0  # kW/s
        self.run_up_rate = self.run_up_rate_fraction_per_min * self.capacity_rated / 60.0  # kW/s

        # Compute the ramp_time, which is the time to ramp from 0 to power_min
        # using the run_up_rate
        self.ramp_time = self.power_min / self.run_up_rate  # s

        # Check that each startup time is at least the ramp_time
        for name in ["startup_time_hot", "startup_time_warm", "startup_time_cold"]:
            if numeric_params[name] < self.ramp_time:
                raise ValueError(f"{name} must be greater than or equal to the ramp_time")

        if self.startup_time_cold < self.startup_time_warm:
            raise ValueError("startup_time_cold must be greater than or equal to startup_time_warm")

        if self.startup_time_warm < self.startup_time_hot:
            raise ValueError("startup_time_warm must be greater than or equal to startup_time_hot")

        # Compute the hot, warm, and cold readying times, which is the startup time minus
        # the ramp_time
        self.readying_time_hot = self.startup_time_hot - self.ramp_time  # s
        self.readying_time_warm = self.startup_time_warm - self.ramp_time  # s
        self.readying_time_cold = self.startup_time_cold - self.ramp_time  # s

        # Extract initial conditions
        initial_conditions = h_dict[self.component_name]["initial_conditions"]
        self.power = initial_conditions["power"]  # kW

        # Check that initial conditions are valid
        if self.power < 0 or self.power > self.capacity_rated:
            raise ValueError(
                "initial_conditions['power'] (initial power) "
                "must be between 0 and capacity_rated (inclusive)"
            )

        # Derive initial state from power: if power > 0 then ON, else OFF
        if self.power > 0:
            self.state = self.STATES.ON
            # Set time_in_state so the unit is immediately ready to stop
            self.time_in_state = float(self.up_time_min)  # s
        else:
            # Set time_in_state so the unit is immediately ready to start
            if "time_in_shutdown" in initial_conditions:
                self.time_in_state = float(initial_conditions["time_in_shutdown"])  # s
            else:
                self.time_in_state = float(self.down_time_min)  # s
            # Classify into the appropriate OFF substate
            self._classify_off_state()

        # Extract efficiency table (HHV net efficiency), HHV, and fuel density
        # for fuel consumption calculations
        self.HHV = component_dict["HHV"]  # J/m³
        self.fuel_density = component_dict["fuel_density"]  # kg/m³
        efficiency_table = component_dict["efficiency_table"]

        # Validate HHV
        if not isinstance(self.HHV, (int, float, hercules_float_type)):
            raise ValueError("HHV must be a number")
        if self.HHV <= 0:
            raise ValueError("HHV must be greater than 0")

        # Validate fuel_density
        if not isinstance(self.fuel_density, (int, float, hercules_float_type)):
            raise ValueError("fuel_density must be a number")
        if self.fuel_density <= 0:
            raise ValueError("fuel_density must be greater than 0")

        # Validate efficiency_table structure
        if not isinstance(efficiency_table, dict):
            raise ValueError("efficiency_table must be a dictionary")
        if "power_fraction" not in efficiency_table:
            raise ValueError("efficiency_table must contain 'power_fraction'")
        if "efficiency" not in efficiency_table:
            raise ValueError("efficiency_table must contain 'efficiency'")

        # Extract and convert to numpy arrays for interpolation
        self.efficiency_power_fraction = np.array(
            efficiency_table["power_fraction"], dtype=hercules_float_type
        )
        self.efficiency_values = np.array(efficiency_table["efficiency"], dtype=hercules_float_type)

        # Validate array lengths match
        if len(self.efficiency_power_fraction) != len(self.efficiency_values):
            raise ValueError(
                "efficiency_table power_fraction and efficiency arrays must have the same length"
            )

        # Validate array lengths are at least 1
        if len(self.efficiency_power_fraction) < 1:
            raise ValueError("efficiency_table must have at least one entry")

        # Validate power_fraction values are in [0, 1]
        if np.any(self.efficiency_power_fraction < 0) or np.any(self.efficiency_power_fraction > 1):
            raise ValueError("efficiency_table power_fraction values must be between 0 and 1")

        # Validate efficiency values are in (0, 1]
        if np.any(self.efficiency_values <= 0) or np.any(self.efficiency_values > 1):
            raise ValueError("efficiency_table efficiency values must be between 0 and 1")

        # Sort arrays by power_fraction for proper interpolation
        sort_idx = np.argsort(self.efficiency_power_fraction)
        self.efficiency_power_fraction = self.efficiency_power_fraction[sort_idx]
        self.efficiency_values = self.efficiency_values[sort_idx]

        # Initialize HHV net efficiency and fuel consumption rate
        self.efficiency = self.calculate_efficiency(self.power)
        self.fuel_volume_rate = 0.0  # m³/s
        self.fuel_mass_rate = 0.0  # kg/s

        # Initialize number of starts
        self.start_count = 0
        self.start_count_hot = 0
        self.start_count_warm = 0
        self.start_count_cold = 0

        # Saved off-duration before a startup attempt (for restore on abort)
        self._time_off_before_start = None

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Add initial conditions and meta data to the h_dict.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Updated dictionary with initial conditions and meta data.
        """
        h_dict[self.component_name]["power"] = self.power
        h_dict[self.component_name]["state"] = self.state.value
        h_dict[self.component_name]["efficiency"] = self.efficiency
        h_dict[self.component_name]["fuel_volume_rate"] = self.fuel_volume_rate
        h_dict[self.component_name]["fuel_mass_rate"] = self.fuel_mass_rate
        h_dict[self.component_name]["start_count"] = self.start_count
        h_dict[self.component_name]["start_count_hot"] = self.start_count_hot
        h_dict[self.component_name]["start_count_warm"] = self.start_count_warm
        h_dict[self.component_name]["start_count_cold"] = self.start_count_cold
        return h_dict

    def step(self, h_dict):
        """Advance the thermal component simulation by one time step.

        Updates the thermal component state including power output, state,
        HHV net efficiency, and fuel consumption based on the requested power setpoint.

        Args:
            h_dict (dict): Dictionary containing simulation state including:
                - self.component_name.power_setpoint: Desired power output [kW]

        Returns:
            dict: Updated h_dict with thermal component outputs:
                - power: Actual power output [kW]
                - state: Operating state number (0=off, 1=hot starting,
                    2=warm starting, 3=cold starting, 4=on, 5=stopping)
                - efficiency: Current HHV net efficiency as fraction (0-1)
                - fuel_volume_rate: Fuel volume flow rate [m³/s]
                - fuel_mass_rate: Fuel mass flow rate [kg/s]

        """
        # Get power setpoint from controller
        power_setpoint = h_dict[self.component_name]["power_setpoint"]

        # Check that the power setpoint is a number
        if not isinstance(power_setpoint, (int, float, hercules_float_type)):
            raise ValueError("power_setpoint must be a number")
        if np.isnan(power_setpoint):
            raise ValueError(f"{self.component_name}: power_setpoint is NaN")

        # Update time in current state
        self.time_in_state += self.dt

        # Determine actual power output based on constraints and state
        self.power = self._control(power_setpoint)

        # Re-classify OFF substate based on time_in_state
        if self._is_off():
            self._classify_off_state()

        # Calculate HHV net efficiency and fuel consumption rate
        self.efficiency = self.calculate_efficiency(self.power)
        self.fuel_volume_rate = self.calculate_fuel_volume_rate(self.power)
        # Compute fuel mass rate from volume rate using density [6]
        self.fuel_mass_rate = self.fuel_volume_rate * self.fuel_density

        # Update h_dict with outputs
        h_dict[self.component_name]["power"] = self.power
        h_dict[self.component_name]["state"] = self.state.value
        h_dict[self.component_name]["efficiency"] = self.efficiency
        h_dict[self.component_name]["fuel_volume_rate"] = self.fuel_volume_rate
        h_dict[self.component_name]["fuel_mass_rate"] = self.fuel_mass_rate

        # Update start counts in h_dict for tracking purposes
        h_dict[self.component_name]["start_count"] = self.start_count
        h_dict[self.component_name]["start_count_hot"] = self.start_count_hot
        h_dict[self.component_name]["start_count_warm"] = self.start_count_warm
        h_dict[self.component_name]["start_count_cold"] = self.start_count_cold

        return h_dict

    def _control(self, power_setpoint):
        """State machine for thermal component control.

        Handles state transitions, startup/shutdown ramps, and power constraints
        based on the current state (state) and time in that state.

        The startup type (hot/warm/cold) is determined by the parameterized
        cooldown thresholds cooldown_time_warm and cooldown_time_cold.

        State Machine:
            STATE_OFF_HOT/OFF_WARM/OFF_COLD (0/6/7):
                - If setpoint > 0 and down_time_min satisfied and
                  time_in_state < cooldown_time_warm: begin HOT_STARTING
                - If setpoint > 0 and down_time_min satisfied and
                  time_in_state >= cooldown_time_cold: begin COLD_STARTING
                - If setpoint > 0 and down_time_min satisfied and
                  time_in_state >= cooldown_time_warm and
                  time_in_state < cooldown_time_cold: begin WARM_STARTING
                - Otherwise: remain OFF, output 0

            STATE_HOT_STARTING (1):
                - If setpoint <= 0: abort startup, return to OFF_HOT
                - If time in state is less than readying_time_hot output 0
                - After readying_time_hot, ramp up to power_min using run_up_rate
                - When power output >= power_min: transition to STATE_ON

            STATE_WARM_STARTING (2):
                - If setpoint <= 0: abort startup, return to OFF_HOT
                - If time in state is less than readying_time_warm output 0
                - After readying_time_warm, ramp up to power_min using run_up_rate
                - When power output >= power_min: transition to STATE_ON

            STATE_COLD_STARTING (3):
                - If setpoint <= 0: abort startup, return to OFF_HOT
                - If time in state is less than readying_time_cold output 0
                - After readying_time_cold, ramp up to power_min using run_up_rate
                - When power output >= power_min: transition to STATE_ON

            STATE_ON (4):
                - If setpoint <= 0 and up_time_min satisfied: begin STOPPING
                - Otherwise: apply power limits and ramp rate constraints

            STATE_STOPPING (5):
                - Ramp to 0 using ramp_rate
                - When power output <= 0: transition to STATE_OFF_HOT

        Args:
            power_setpoint (float): Desired power output in kW.

        Returns:
            float: Actual constrained power output in kW.
        """
        # ====================================================================
        # STATE: OFF (OFF_HOT, OFF_WARM, OFF_COLD)
        # ====================================================================
        if self._is_off():
            # Check if we can start (down_time_min satisfied)
            if not hasattr(self, "can_start"):
                can_start = self.time_in_state >= self.down_time_min
            else:
                can_start = self.can_start

            if power_setpoint > 0 and can_start:
                self.start_count += 1
                # Check if hot, warm, or cold starting is implied
                if self.time_in_state < self.cooldown_time_warm:
                    self.state = self.STATES.HOT_STARTING
                    self.start_count_hot += 1
                elif self.time_in_state < self.cooldown_time_cold:
                    self.state = self.STATES.WARM_STARTING
                    self.start_count_warm += 1
                else:
                    self.state = self.STATES.COLD_STARTING
                    self.start_count_cold += 1
                self._time_off_before_start = self.time_in_state
                self.time_in_state = 0.0
                if hasattr(self, "can_start"):
                    del self.can_start

            return 0.0  # Power is always 0 when off

        # ====================================================================
        # STATE: HOT_STARTING
        # ====================================================================
        elif self.state == self.STATES.HOT_STARTING:
            # Check if startup should be aborted
            if power_setpoint <= 0:
                # Restore off-duration: saved pre-start time + time spent starting
                self.time_in_state = self._time_off_before_start + self.time_in_state
                self.state = self.STATES.OFF_HOT
                self.power = 0.0
                return 0.0

            # Check if readying time is complete
            if self.time_in_state < self.readying_time_hot:
                return 0.0

            # Ramp up using run_up_rate
            startup_power = (self.time_in_state - self.readying_time_hot) * self.run_up_rate

            # Check if ramping is complete
            if startup_power >= self.power_min:
                self.state = self.STATES.ON
                self.time_in_state = 0.0
                self._time_off_before_start = None
                return startup_power

            # Limit to below power_max (edge case)
            startup_power = np.clip(startup_power, 0, self.power_max)

            return startup_power

        # ====================================================================
        # STATE: WARM_STARTING
        # ====================================================================
        elif self.state == self.STATES.WARM_STARTING:
            # Check if startup should be aborted
            if power_setpoint <= 0:
                # Restore off-duration: saved pre-start time + time spent starting
                self.time_in_state = self._time_off_before_start + self.time_in_state
                self._classify_off_state()
                self.power = 0.0
                return 0.0

            # Check if readying time is complete
            if self.time_in_state < self.readying_time_warm:
                return 0.0

            # Ramp up using run_up_rate
            startup_power = (self.time_in_state - self.readying_time_warm) * self.run_up_rate

            # Check if ramping is complete
            if startup_power >= self.power_min:
                self.state = self.STATES.ON
                self.time_in_state = 0.0
                self._time_off_before_start = None
                return startup_power

            # Limit to below power_max (edge case)
            startup_power = np.clip(startup_power, 0, self.power_max)

            return startup_power

        # ====================================================================
        # STATE: COLD_STARTING
        # ====================================================================
        elif self.state == self.STATES.COLD_STARTING:
            # Check if startup should be aborted
            if power_setpoint <= 0:
                # Restore off-duration: saved pre-start time + time spent starting
                self.time_in_state = self._time_off_before_start + self.time_in_state
                self._classify_off_state()
                self.power = 0.0
                return 0.0

            # Check if readying time is complete
            if self.time_in_state < self.readying_time_cold:
                return 0.0

            # Ramp up using run_up_rate
            startup_power = (self.time_in_state - self.readying_time_cold) * self.run_up_rate

            # Check if ramping is complete
            if startup_power >= self.power_min:
                self.state = self.STATES.ON
                self.time_in_state = 0.0
                self._time_off_before_start = None
                return startup_power

            # Limit to below power_max (edge case)
            startup_power = np.clip(startup_power, 0, self.power_max)

            return startup_power

        # ====================================================================
        # STATE: ON
        # ====================================================================
        elif self.state == self.STATES.ON:
            # Check if we can shut down (up_time_min satisfied)
            can_shutdown = self.time_in_state >= self.up_time_min

            if power_setpoint <= 0 and can_shutdown:
                # Transition to shutdown sequence
                self.state = self.STATES.STOPPING
                self.time_in_state = 0.0

                # Immediately apply stopping-state ramp-down behavior
                shutdown_power = self.power - self.ramp_rate * self.dt

                # Check if shutdown is complete in this timestep
                if shutdown_power <= 0:
                    self.state = self.STATES.OFF_HOT
                    self.time_in_state = 0.0
                    return 0.0

                return shutdown_power

            # Apply constraints for on operation
            return self._apply_on_constraints(power_setpoint)

        # ====================================================================
        # STATE: STOPPING
        # ====================================================================
        elif self.state == self.STATES.STOPPING:
            # Ramp the power output down using ramp_rate
            shutdown_power = self.power - self.ramp_rate * self.dt

            # Check if shutdown is complete
            if shutdown_power <= 0:
                self.state = self.STATES.OFF_HOT
                self.time_in_state = 0.0
                return 0.0

            return shutdown_power

        else:
            raise ValueError(f"Unexpected state in _control: {self.state}")

    def _apply_on_constraints(self, power_setpoint):
        """Apply power and ramp rate constraints when unit is on.

        Args:
            power_setpoint (float): Desired power output in kW.

        Returns:
            float: Constrained power output in kW.
        """
        # Apply power limits
        power_constrained = np.clip(power_setpoint, self.power_min, self.power_max)

        # Apply ramp rate constraints
        max_ramp_up = self.power + self.ramp_rate * self.dt
        max_ramp_down = self.power - self.ramp_rate * self.dt
        power_constrained = np.clip(power_constrained, max_ramp_down, max_ramp_up)

        return power_constrained

    def calculate_efficiency(self, power):
        """Calculate HHV net efficiency based on current power output and state.

        Args:
            power (float): Current power output in kW.

        Returns:
            float: HHV net efficiency as a fraction (0-1).
        """
        fuel_consumption_rate = self.calculate_fuel_volume_rate(power)  # m³/s

        if fuel_consumption_rate == 0:
            return np.nan  # Efficiency is undefined when fuel consumption is zero

        return (power * 1000.0) / (fuel_consumption_rate * self.HHV)

    def interpolate_efficiency(self, power):
        """Interpolate HHV net efficiency based on current power output.

        Uses linear interpolation from the efficiency table. Values outside the
        table range are clamped to the nearest endpoint.

        Args:
            power (float): Current power output in kW.

        Returns:
            float: HHV net efficiency as a fraction (0-1).
        """
        power_fraction = power / self.capacity_rated

        # Interpolate efficiency (numpy.interp clamps to endpoints by default)
        efficiency = np.interp(
            power_fraction, self.efficiency_power_fraction, self.efficiency_values
        )

        return efficiency

    def calculate_fuel_volume_rate(self, power):
        """Calculate fuel volume flow rate based on power output and HHV net efficiency.

        Args:
            power (float): Current power output in kW.

        Returns:
            float: Fuel volume flow rate in m³/s.
        """
        fuel_volume_rate_rated = (self.capacity_rated * 1000.0) / (
            self.HHV * self.interpolate_efficiency(self.capacity_rated)
        )  # m³/s at rated capacity

        if self._is_off():
            # When off, fuel flow is zero
            return 0.0
        elif self.state == self.STATES.STOPPING and self.fuel_shutdown_fraction is not None:
            # When stopping, use shutdown fuel fraction if provided
            return max(
                self.fuel_shutdown_fraction * fuel_volume_rate_rated,
                power * 1000.0 / (self.HHV * self.interpolate_efficiency(power)),
            )

        elif (
            self.state
            in [
                self.STATES.HOT_STARTING,
                self.STATES.WARM_STARTING,
                self.STATES.COLD_STARTING,
            ]
            and self.fuel_startup_fraction is not None
        ):
            # During startup (HOT_STARTING, WARM_STARTING, COLD_STARTING), use startup fuel fraction
            return self.fuel_startup_fraction * fuel_volume_rate_rated

        # When on, calculate fuel rate based on current HHV net efficiency
        efficiency = self.interpolate_efficiency(power)

        # fuel_volume_rate (m³/s) = power (W) / (efficiency * HHV (J/m³))
        return (power * 1000.0) / (efficiency * self.HHV)
