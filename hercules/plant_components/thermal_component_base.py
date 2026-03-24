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
        - 0 (OFF): Thermal Component is off, no power output
        - 1 (HOT_STARTING): Thermal Component is readying or ramping up to minimum
            stable load from off state (hot start)
        - 2 (WARM_STARTING): Thermal Component is readying or ramping up to minimum
            stable load from off state (warm start)
        - 3 (COLD_STARTING): Thermal Component is readying or ramping up to minimum
            stable load from off state (cold start)
        - 4 (ON): Thermal Component is operating normally
        - 5 (STOPPING): Thermal Component is ramping down to shutdown


    """

    component_category = "generator"

    class STATES(IntEnum):
        """Enumeration of thermal component operating states."""

        OFF = 0
        HOT_STARTING = 1
        WARM_STARTING = 2
        COLD_STARTING = 3
        ON = 4
        STOPPING = 5

    # Time constants
    #       Note the time definitions for cold versus warm versus hot starting are hard
    #   coded and based on the values in [5].
    HOT_START_TIME = 8 * 60 * 60  # 8 hours (less than 8 hours triggers a hot start)
    WARM_START_TIME = 48 * 60 * 60  # 48 hours (less than 48 hours triggers a warm start)

    def __init__(self, h_dict, component_name):
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
                - warm_startup_time: Time to reach min_stable_load_fraction from off in s.
                    Includes both readying time and ramping time.
                - cold_startup_time: Time to reach min_stable_load_fraction from off in s.
                    Includes both readying time and ramping time.
                - min_up_time: Minimum time unit must remain on in s.
                - min_down_time: Minimum time unit must remain off in s.
                - initial_conditions: Dictionary with initial power (state is
                    derived automatically: power > 0 means ON, power == 0 means OFF)
                - hhv: Higher heating value of fuel in J/m³
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
        self.rated_capacity = component_dict["rated_capacity"]  # kW
        self.min_stable_load_fraction = component_dict["min_stable_load_fraction"]
        self.ramp_rate_fraction = component_dict["ramp_rate_fraction"]
        self.run_up_rate_fraction = component_dict["run_up_rate_fraction"]
        self.hot_startup_time = component_dict["hot_startup_time"]  # s
        self.warm_startup_time = component_dict["warm_startup_time"]  # s
        self.cold_startup_time = component_dict["cold_startup_time"]  # s
        self.min_up_time = component_dict["min_up_time"]  # s
        self.min_down_time = component_dict["min_down_time"]  # s

        # Check all required parameters are numbers
        if not isinstance(self.rated_capacity, (int, float, hercules_float_type)):
            raise ValueError("rated_capacity must be a number")
        if not isinstance(self.min_stable_load_fraction, (int, float, hercules_float_type)):
            raise ValueError("min_stable_load_fraction must be a number")
        if not isinstance(self.ramp_rate_fraction, (int, float, hercules_float_type)):
            raise ValueError("ramp_rate_fraction must be a number")
        if not isinstance(self.run_up_rate_fraction, (int, float, hercules_float_type)):
            raise ValueError("run_up_rate_fraction must be a number")
        if not isinstance(self.hot_startup_time, (int, float, hercules_float_type)):
            raise ValueError("hot_startup_time must be a number")
        if not isinstance(self.warm_startup_time, (int, float, hercules_float_type)):
            raise ValueError("warm_startup_time must be a number")
        if not isinstance(self.cold_startup_time, (int, float, hercules_float_type)):
            raise ValueError("cold_startup_time must be a number")
        if not isinstance(self.min_up_time, (int, float, hercules_float_type)):
            raise ValueError("min_up_time must be a number")
        if not isinstance(self.min_down_time, (int, float, hercules_float_type)):
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
        if self.warm_startup_time < 0:
            raise ValueError("warm_startup_time must be greater than or equal to 0")
        if self.cold_startup_time < 0:
            raise ValueError("cold_startup_time must be greater than or equal to 0")
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

        # Check that warm_startup_time is greater than or equal to the ramp_time
        if self.warm_startup_time < self.ramp_time:
            raise ValueError("warm_startup_time must be greater than or equal to the ramp_time")

        # Check that cold_startup_time is greater than or equal to the ramp_time
        if self.cold_startup_time < self.ramp_time:
            raise ValueError("cold_startup_time must be greater than or equal to the ramp_time")

        # Check that the cold_startup_time is at least as long as the warm_startup_time
        if self.cold_startup_time < self.warm_startup_time:
            raise ValueError("cold_startup_time must be greater than or equal to warm_startup_time")

        # Check that the warm_startup_time is at least as long as the hot_startup_time
        if self.warm_startup_time < self.hot_startup_time:
            raise ValueError("warm_startup_time must be greater than or equal to hot_startup_time")

        # Compute the hot, warm, and cold readying times, which is the startup time minus
        # the ramp_time
        self.hot_readying_time = self.hot_startup_time - self.ramp_time  # s
        self.warm_readying_time = self.warm_startup_time - self.ramp_time  # s
        self.cold_readying_time = self.cold_startup_time - self.ramp_time  # s

        # Extract initial conditions
        initial_conditions = h_dict[self.component_name]["initial_conditions"]
        self.power_output = initial_conditions["power"]  # kW

        # Check that initial conditions are valid
        if self.power_output < 0 or self.power_output > self.rated_capacity:
            raise ValueError(
                "initial_conditions['power'] (initial power) "
                "must be between 0 and rated_capacity (inclusive)"
            )

        # Derive initial state from power: if power > 0 then ON, else OFF
        if self.power_output > 0:
            self.state = self.STATES.ON
            # Set time_in_state so the unit is immediately ready to stop
            self.time_in_state = float(self.min_up_time)  # s
        else:
            self.state = self.STATES.OFF
            # Set time_in_state so the unit is immediately ready to start
            if "time_in_shutdown" in initial_conditions:
                self.time_in_state = float(initial_conditions["time_in_shutdown"])  # s
            else:
                self.time_in_state = float(self.min_down_time)  # s

        # Extract efficiency table (HHV net efficiency), HHV, and fuel density
        # for fuel consumption calculations
        self.hhv = component_dict["hhv"]  # J/m³
        self.fuel_density = component_dict["fuel_density"]  # kg/m³
        efficiency_table = component_dict["efficiency_table"]

        # Validate hhv
        if not isinstance(self.hhv, (int, float, hercules_float_type)):
            raise ValueError("hhv must be a number")
        if self.hhv <= 0:
            raise ValueError("hhv must be greater than 0")

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
        self.efficiency = self.calculate_efficiency(self.power_output)
        self.fuel_volume_rate = 0.0  # m³/s
        self.fuel_mass_rate = 0.0  # kg/s

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Add initial conditions and meta data to the h_dict.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Updated dictionary with initial conditions and meta data.
        """
        h_dict[self.component_name]["power"] = self.power_output
        h_dict[self.component_name]["state"] = self.state.value
        h_dict[self.component_name]["efficiency"] = self.efficiency
        h_dict[self.component_name]["fuel_volume_rate"] = self.fuel_volume_rate
        h_dict[self.component_name]["fuel_mass_rate"] = self.fuel_mass_rate
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
        self.power_output = self._control(power_setpoint)

        # Calculate HHV net efficiency and fuel consumption rate
        self.efficiency = self.calculate_efficiency(self.power_output)
        self.fuel_volume_rate = self.calculate_fuel_volume_rate(self.power_output)
        # Compute fuel mass rate from volume rate using density [6]
        self.fuel_mass_rate = self.fuel_volume_rate * self.fuel_density

        # Update h_dict with outputs
        h_dict[self.component_name]["power"] = self.power_output
        h_dict[self.component_name]["state"] = self.state.value
        h_dict[self.component_name]["efficiency"] = self.efficiency
        h_dict[self.component_name]["fuel_volume_rate"] = self.fuel_volume_rate
        h_dict[self.component_name]["fuel_mass_rate"] = self.fuel_mass_rate

        return h_dict

    def _control(self, power_setpoint):
        """State machine for thermal component control.

        Handles state transitions, startup/shutdown ramps, and power constraints
        based on the current state (state) and time in that state.

        Note the time definitions for cold versus warm versus hot starting are hard
        coded and based on the values in [5].

        State Machine:
            STATE_OFF (0):
                - If setpoint > 0 and min_down_time satisfied and time_in_state < 8 hours:
                  begin HOT_STARTING
                - If setpoint > 0 and min_down_time satisfied and time_in_state >= 48 hours:
                  begin COLD_STARTING
                - If setpoint > 0 and min_down_time satisfied and time_in_state >= 8 hours
                  and time_in_state < 48 hours: begin WARM_STARTING
                - Otherwise: remain OFF, output 0

            STATE_HOT_STARTING (1):
                - If setpoint <= 0: abort startup, return to OFF
                - If time in state is less than hot_readying_time output 0
                - After hot_readying_time, ramp up to P_min using run_up_rate
                - When power output >= P_min: transition to STATE_ON

            STATE_WARM_STARTING (2):
                - If setpoint <= 0: abort startup, return to OFF
                - If time in state is less than warm_readying_time output 0
                - After warm_readying_time, ramp up to P_min using run_up_rate
                - When power output >= P_min: transition to STATE_ON

            STATE_COLD_STARTING (3):
                - If setpoint <= 0: abort startup, return to OFF
                - If time in state is less than cold_readying_time output 0
                - After cold_readying_time, ramp up to P_min using run_up_rate
                - When power output >= P_min: transition to STATE_ON

            STATE_ON (4):
                - If setpoint <= 0 and min_up_time satisfied: begin STOPPING
                - Otherwise: apply power limits and ramp rate constraints

            STATE_STOPPING (5):
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
        if self.state == self.STATES.OFF:
            # Check if we can start (min_down_time satisfied)
            can_start = self.time_in_state >= self.min_down_time

            if power_setpoint > 0 and can_start:
                # Check if hot, warm, or cold starting is implied
                if self.time_in_state < self.HOT_START_TIME:
                    self.state = self.STATES.HOT_STARTING
                elif self.time_in_state < self.WARM_START_TIME:
                    self.state = self.STATES.WARM_STARTING
                else:
                    self.state = self.STATES.COLD_STARTING
                self.time_in_state = 0.0

            return 0.0  # Power is always 0 when off

        # ====================================================================
        # STATE: HOT_STARTING
        # ====================================================================
        elif self.state == self.STATES.HOT_STARTING:
            # Check if startup should be aborted
            if power_setpoint <= 0:
                self.state = self.STATES.OFF
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
                self.state = self.STATES.ON
                self.time_in_state = 0.0
                return startup_power

            # Limit to below P_max (edge case)
            startup_power = np.clip(startup_power, 0, self.P_max)

            return startup_power

        # ====================================================================
        # STATE: WARM_STARTING
        # ====================================================================
        elif self.state == self.STATES.WARM_STARTING:
            # Check if startup should be aborted
            if power_setpoint <= 0:
                self.state = self.STATES.OFF
                self.time_in_state = 0.0
                self.power_output = 0.0
                return 0.0

            # Check if readying time is complete
            if self.time_in_state < self.warm_readying_time:
                return 0.0

            # Ramp up using run_up_rate
            startup_power = (self.time_in_state - self.warm_readying_time) * self.run_up_rate

            # Check if ramping is complete
            if startup_power >= self.P_min:
                self.state = self.STATES.ON
                self.time_in_state = 0.0
                return startup_power

            # Limit to below P_max (edge case)
            startup_power = np.clip(startup_power, 0, self.P_max)

            return startup_power

        # ====================================================================
        # STATE: COLD_STARTING
        # ====================================================================
        elif self.state == self.STATES.COLD_STARTING:
            # Check if startup should be aborted
            if power_setpoint <= 0:
                self.state = self.STATES.OFF
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
                self.state = self.STATES.ON
                self.time_in_state = 0.0
                return startup_power

            # Limit to below P_max (edge case)
            startup_power = np.clip(startup_power, 0, self.P_max)

            return startup_power

        # ====================================================================
        # STATE: ON
        # ====================================================================
        elif self.state == self.STATES.ON:
            # Check if we can shut down (min_up_time satisfied)
            can_shutdown = self.time_in_state >= self.min_up_time

            if power_setpoint <= 0 and can_shutdown:
                # Transition to shutdown sequence
                self.state = self.STATES.STOPPING
                self.time_in_state = 0.0

                # Immediately apply stopping-state ramp-down behavior
                shutdown_power = self.power_output - self.ramp_rate * self.dt

                # Check if shutdown is complete in this timestep
                if shutdown_power <= 0:
                    self.state = self.STATES.OFF
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
            shutdown_power = self.power_output - self.ramp_rate * self.dt

            # Check if shutdown is complete
            if shutdown_power <= 0:
                self.state = self.STATES.OFF
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
        P_constrained = np.clip(power_setpoint, self.P_min, self.P_max)

        # Apply ramp rate constraints
        max_ramp_up = self.power_output + self.ramp_rate * self.dt
        max_ramp_down = self.power_output - self.ramp_rate * self.dt
        P_constrained = np.clip(P_constrained, max_ramp_down, max_ramp_up)

        return P_constrained

    def calculate_efficiency(self, power_output):
        """Calculate HHV net efficiency based on current power output.

        Uses linear interpolation from the efficiency table. Values outside the
        table range are clamped to the nearest endpoint.

        Args:
            power_output (float): Current power output in kW.

        Returns:
            float: HHV net efficiency as a fraction (0-1).
        """
        if power_output <= 0:
            # Return efficiency at lowest power fraction when off
            return self.efficiency_values[0]

        # Calculate power fraction
        power_fraction = power_output / self.rated_capacity

        # Interpolate efficiency (numpy.interp clamps to endpoints by default)
        efficiency = np.interp(
            power_fraction, self.efficiency_power_fraction, self.efficiency_values
        )

        return efficiency

    def calculate_fuel_volume_rate(self, power_output):
        """Calculate fuel volume flow rate based on power output and HHV net efficiency.

        Args:
            power_output (float): Current power output in kW.

        Returns:
            float: Fuel volume flow rate in m³/s.
        """
        if power_output <= 0:
            return 0.0

        # Calculate current HHV net efficiency
        efficiency = self.calculate_efficiency(power_output)

        # Calculate fuel volume rate using HHV net efficiency
        # fuel_volume_rate (m³/s) = power (W) / (efficiency * hhv (J/m³))
        # Convert power from kW to W (multiply by 1000)
        fuel_m3_per_s = (power_output * 1000.0) / (efficiency * self.hhv)

        return fuel_m3_per_s
