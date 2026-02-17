"""
Open Cycle Gas Turbine Class.

Open cycle gas turbine (OCGT) model is a subclass of the ThermalComponentBase class.
It implements the model as presented in [1], [2], [3], [4], [5] and [6].

Like other subclasses of ThermalComponentBase, it inherits the main control functions,
and adds defaults for many variables based on [1], [2], [3], [4], [5] and [6].

Note: All efficiency values are HHV (Higher Heating Value) net plant efficiencies.
The default efficiency table is based on the SC1A curve from Exhibit ES-4 of [5].

Note: This class is based on aeroderivative open cycle gas turbines,
which are commonly used for flexible power generation.

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

from hercules.plant_components.thermal_component_base import ThermalComponentBase


class OpenCycleGasTurbine(ThermalComponentBase):
    """Open cycle gas turbine model.

    This model represents an open cycle gas turbine with state
    management, ramp rate constraints, minimum stable load, and fuel consumption
    tracking.  Note it is a subclass of the ThermalComponentBase class.

    All efficiency values are HHV (Higher Heating Value) net plant efficiencies.
    """

    component_name = "open_cycle_gas_turbine"
    component_type = "OpenCycleGasTurbine"

    def __init__(self, h_dict):
        """Initialize the OpenCycleGasTurbine class.

        Args:
            h_dict (dict): Dictionary containing simulation parameters including:
                - rated_capacity: Maximum power output in kW
                - min_stable_load_fraction: Optional, minimum operating point as fraction (0-1).
                    Default: 0.40 (40%) [4]
                - ramp_rate_fraction: Optional, maximum rate of power increase/decrease
                    as fraction of rated capacity per minute. Default: 0.1 (10%)
                - run_up_rate_fraction: Optional, maximum rate of power increase during startup
                    as fraction of rated capacity per minute. Default: ramp_rate_fraction
                - hot_startup_time: Optional, time to reach min_stable_load_fraction from off
                    in s. Includes both readying time and ramping time.
                    Default: 420.0 s (7 minutes) [1, 5]
                - warm_startup_time: Optional, time to reach min_stable_load_fraction from off
                    in s. Includes both readying time and ramping time.
                    Default: 480.0 s (8 minutes) [1, 5]
                - cold_startup_time: Optional, time to reach min_stable_load_fraction from off
                    in s. Includes both readying time and ramping time.
                    Default: 480.0 s (8 minutes) [1, 5]
                - min_up_time: Optional, minimum time unit must remain on in s.
                    Default: 1800.0 s (30 minutes) [4]
                - min_down_time: Optional, minimum time unit must remain off in s.
                    Default: 3600.0 s (1 hour) [4]
                - initial_conditions: Dictionary with initial power (state is
                    derived automatically: power > 0 means ON, power == 0 means OFF)
                - hhv: Optional, higher heating value of natural gas in J/m³.
                    Default: 39050000 J/m³ (39.05 MJ/m³) [6]
                - fuel_density: Optional, fuel density in kg/m³.
                    Default: 0.768 kg/m³ [6]
                - efficiency_table: Optional, dictionary with power_fraction and
                    efficiency arrays (both as fractions 0-1). Efficiency values must
                    be HHV net plant efficiencies. Default values are approximate
                    readings from the SC1A curve in Exhibit ES-4 of [5]:
                    power_fraction = [1.0, 0.75, 0.50, 0.25],
                    efficiency = [0.39, 0.37, 0.325, 0.245].
        """

        # Apply fixed default parameters based on [1], [2] and [3]
        # back into the h_dict if they are not provided
        if "min_stable_load_fraction" not in h_dict[self.component_name]:
            h_dict[self.component_name]["min_stable_load_fraction"] = 0.40
        if "ramp_rate_fraction" not in h_dict[self.component_name]:
            h_dict[self.component_name]["ramp_rate_fraction"] = 0.1
        if "hot_startup_time" not in h_dict[self.component_name]:
            h_dict[self.component_name]["hot_startup_time"] = 420.0
        if "warm_startup_time" not in h_dict[self.component_name]:
            h_dict[self.component_name]["warm_startup_time"] = 480.0
        if "cold_startup_time" not in h_dict[self.component_name]:
            h_dict[self.component_name]["cold_startup_time"] = 480.0
        if "min_up_time" not in h_dict[self.component_name]:
            h_dict[self.component_name]["min_up_time"] = 1800.0
        if "min_down_time" not in h_dict[self.component_name]:
            h_dict[self.component_name]["min_down_time"] = 3600.0

        # If the run_up_rate_fraction is not provided, it defaults to the ramp_rate_fraction
        if "run_up_rate_fraction" not in h_dict[self.component_name]:
            h_dict[self.component_name]["run_up_rate_fraction"] = h_dict[self.component_name][
                "ramp_rate_fraction"
            ]

        # Default HHV for natural gas (39.05 MJ/m³) from [6]
        if "hhv" not in h_dict[self.component_name]:
            h_dict[self.component_name]["hhv"] = 39050000  # J/m³ (39.05 MJ/m³)

        # Default fuel density for natural gas (0.768 kg/m³) from [6]
        if "fuel_density" not in h_dict[self.component_name]:
            h_dict[self.component_name]["fuel_density"] = 0.768  # kg/m³

        # Default HHV net plant efficiency table based on approximate readings from
        # the SC1A curve in Exhibit ES-4 of [5]
        if "efficiency_table" not in h_dict[self.component_name]:
            h_dict[self.component_name]["efficiency_table"] = {
                "power_fraction": [1.0, 0.75, 0.50, 0.25],
                "efficiency": [0.39, 0.37, 0.325, 0.245],
            }

        # Call the base class init
        super().__init__(h_dict)
