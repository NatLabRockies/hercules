"""
Open Cycle Gas Turbine Class.

Open cycle gas turbine (OCGT) model is a subclass of the ThermalComponentBase class.
It implements the model as presented in [1], [2] and [3].

Like other subclasses of ThermalComponentBase, it inherits the main control functions,
and adds defaults for many variables based on [1], [2] and [3].

Finally the subclass implements several OCGT specific functions be called by the overloaded
_post_process() function.

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

from hercules.plant_components.thermal_component_base import ThermalComponentBase

import numpy as np


class OpenCycleGasTurbine(ThermalComponentBase):
    """Open cycle gas turbine model.

    This model represents an open cycle gas turbine with state
    management, ramp rate constraints, minimum stable load, and fuel consumption
    tracking.  Note it is a subclass of the ThermalComponentBase class.
    """

    def __init__(self, h_dict):
        """Initialize the OpenCycleGasTurbine class.

        Args:
            h_dict (dict): Dictionary containing simulation parameters including:
                - rated_capacity: Maximum power output in kW
                - min_stable_load_fraction: Optional, minimum operating point as fraction (0-1).
                    Default: 0.20 (20%)
                - ramp_rate_fraction: Optional, maximum rate of power increase/decrease
                    as fraction of rated capacity per minute. Default: 0.1 (10%)
                - run_up_rate_fraction: Optional, maximum rate of power increase during startup
                    as fraction of rated capacity per minute. Default: ramp_rate_fraction
                - hot_startup_time: Optional, time to reach min_stable_load_fraction from off
                    in s. Includes both readying time and ramping time.
                    Default: 420.0 s (7 minutes)
                - cold_startup_time: Optional, time to reach min_stable_load_fraction from off
                    in s. Includes both readying time and ramping time.
                    Default: 480.0 s (8 minutes)
                - hot_cold_cutoff_time: Optional, time in off after which cold starting is
                    implied in s. Default: 28800.0 s (8 hours)
                - min_up_time: Optional, minimum time unit must remain on in s.
                    Default: 7200.0 s (2 hours)
                - min_down_time: Optional, minimum time unit must remain off in s.
                    Default: 7200.0 s (2 hours)
                - initial_conditions: Dictionary with initial power and state_num
                - part_load_factor: Optional, heat rate penalty at min load.
                    Default: 1.0 (no penalty)
                - heat_rate_at_rated_load: Optional, fuel consumption rate at rated load
                    in kJ/kWh. Default: 10000
        """

        # Store the name of this component
        self.component_name = "open_cycle_gas_turbine"

        # Store the type of this component
        self.component_type = "OpenCycleGasTurbine"

        # Apply fixeddefault parameters based on [1], [2] and [3]
        # back into the h_dict if they are not provided
        if "min_stable_load_fraction" not in h_dict[self.component_name]:
            h_dict[self.component_name]["min_stable_load_fraction"] = 0.20
        if "ramp_rate_fraction" not in h_dict[self.component_name]:
            h_dict[self.component_name]["ramp_rate_fraction"] = 0.1
        if "hot_startup_time" not in h_dict[self.component_name]:
            h_dict[self.component_name]["hot_startup_time"] = 7 * 60.0
        if "cold_startup_time" not in h_dict[self.component_name]:
            h_dict[self.component_name]["cold_startup_time"] = 8 * 60.0
        if "hot_cold_cutoff_time" not in h_dict[self.component_name]:
            h_dict[self.component_name]["hot_cold_cutoff_time"] = 8 * 60.0 * 60.0
        if "min_up_time" not in h_dict[self.component_name]:
            h_dict[self.component_name]["min_up_time"] = 2 * 60.0 * 60.0
        if "min_down_time" not in h_dict[self.component_name]:
            h_dict[self.component_name]["min_down_time"] = 2 * 60.0 * 60.0
        
        # If the run_up_rate_fraction is not provided, it defaults to the ramp_rate_fraction
        if "run_up_rate_fraction" not in h_dict[self.component_name]:
            h_dict[self.component_name]["run_up_rate_fraction"] = h_dict[self.component_name]["ramp_rate_fraction"]

        # Call the base class init
        super().__init__(h_dict)

        # Extract parameters specific to OCGT
        component_dict = h_dict[self.component_name]
        self.part_load_factor = component_dict.get("part_load_factor", 1.0)
        self.heat_rate_at_rated_load = component_dict.get(
            "heat_rate_at_rated_load", 10000
        )  # kJ/kWh at rated load

        # Check parameters specific to OCGT
        if self.part_load_factor < 1 or self.part_load_factor > 2:
            raise ValueError("part_load_factor must be between 1.0 and 2.0")
        if self.heat_rate_at_rated_load <= 0:
            raise ValueError("heat_rate_at_rated_load must be greater than 0")

        # Initialize the heat rate
        self.heat_rate = self._calc_heat_rate(self.power_output)

        # Initialize the fuel consumption
        self.fuel_consumption = self._calc_fuel_consumption(self.power_output)

    # Overload get_initial_conditions_and_meta_data to add OCGT specific initial conditions
    def get_initial_conditions_and_meta_data(self, h_dict):
        """Add initial conditions and meta data to the h_dict.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Updated dictionary with initial conditions and meta data.
        """
        h_dict[self.component_name]["power"] = self.power_output
        h_dict[self.component_name]["state_num"] = self.state_num
        h_dict[self.component_name]["fuel_consumption"] = 0.0
        h_dict[self.component_name]["heat_rate"] = self.heat_rate
        return h_dict

    def _calc_fuel_consumption(self, power_output):
        """Calculate fuel consumed based on power output and heat rate.

        Args:
            power_output (float): Current power output in kW.

        Returns:
            float: Fuel consumed this timestep in kJ.
        """

        # TODO: Is this correct?  Should we be getting to m^3 of natural gas?
        if power_output <= 0:
            self.heat_rate = self.heat_rate_at_rated_load
            return 0.0

        # Calculate current heat rate with part-load penalty
        self.heat_rate = self._calc_heat_rate(power_output)

        # Fuel = Power * Heat Rate * dt
        # Units: kW * (kJ/kWh) * (s) * (h/3600s) = kJ
        fuel_kJ = power_output * self.heat_rate * (self.dt / 3600.0)

        return fuel_kJ

    def _calc_heat_rate(self, power_output):
        """Calculate heat rate accounting for part-load efficiency degradation.

        Uses linear interpolation between rated load (self.heat_rate_at_rated_load) and minimum
        stable load (self.heat_rate_at_rated_load * self.part_load_factor).

        Args:
            power_output (float): Current power output in kW.

        Returns:
            float: Current heat rate in kJ/kWh.
        """
        if power_output <= 0:
            return self.heat_rate_at_rated_load

        if self.part_load_factor == 1.0:
            return self.heat_rate_at_rated_load

        # Linear interpolation of efficiency penalty
        # At rated load: heat_rate
        # At min load: heat_rate * part_load_factor
        load_fraction = power_output / self.rated_capacity

        # Avoid division by zero if min_stable_load_fraction is 1.0
        if self.min_stable_load_fraction >= 1.0:
            return self.heat_rate_at_rated_load

        # Linear interpolation
        # efficiency_penalty goes from part_load_factor at min_load to 1.0 at rated
        normalized_load = (load_fraction - self.min_stable_load_fraction) / (
            1.0 - self.min_stable_load_fraction
        )
        normalized_load = np.clip(normalized_load, 0.0, 1.0)

        efficiency_penalty = self.part_load_factor - (self.part_load_factor - 1.0) * normalized_load

        return self.heat_rate_at_rated_load * efficiency_penalty


    # Overload _post_process to add OCGT specific post-processing
    def _post_process(self, h_dict):
        """Post-process the OCGT simulation. 
        
        This is called by the base class after the control function.  
        Computes the fuel consumption and heat rate.     

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Updated dictionary with post-processed simulation state.
        """
        # Calculate fuel consumption for this timestep
        self.fuel_consumption = self._calc_fuel_consumption(self.power_output)

        # Update h_dict with outputs
        h_dict[self.component_name]["fuel_consumption"] = self.fuel_consumption
        h_dict[self.component_name]["heat_rate"] = self.current_heat_rate

        return h_dict
