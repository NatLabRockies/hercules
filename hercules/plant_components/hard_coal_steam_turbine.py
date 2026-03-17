"""
Hard Coal Steam Turbine Class.

Hard coal steam turbine model is a subclass of the ThermalComponentBase class.
It implements the model as presented in [1], [2], [3], and [4].

Like other subclasses of ThermalComponentBase, it inherits the main control functions,
and adds defaults for many variables based on [1], [2], [3], and [4].

References:

[1] Agora Energiewende (2017): Flexibility in thermal power plants
     With a focus on existing coal-fired power plants.
[2] IRENA (2019), Innovation landscape brief: Flexibility in conventional power plants,
    International Renewable Energy Agency, Abu Dhabi.
[3] Schmitt, Tommy, Sarah Leptinsky, Marc Turner, Alex Zoelle, Chuck White, Sydney Hughes,
    Sally Homsy, et al. “Cost And Performance Baseline for Fossil Energy Plants Volume 1:
    Bituminous Coal and Natural Gas to Electricity.” Pittsburgh, PA: National Energy Technology
    Laboratory, October 14, 2022b. https://doi.org/10.2172/1893822.
[4] I. Staffell, "The Energy and Fuel Data Sheet," University of Birmingham, March 2011.
    https://claverton-energy.com/cms4/wp-content/uploads/2012/08/the_energy_and_fuel_data_sheet.pdf
"""

from hercules.plant_components.thermal_component_base import ThermalComponentBase


class HardCoalSteamTurbine(ThermalComponentBase):
    """Hard coal steam turbine model.

    This model represents a hard coal steam turbine with state
    management, ramp rate constraints, minimum stable load, and fuel consumption
    tracking.  Note it is a subclass of the ThermalComponentBase class.

    All efficiency values are HHV (Higher Heating Value) net plant efficiencies.

    NOTE: if minimum downtime is 48 hours, then hot start = warm start = cold start = 7.5 hours
        as per [1].
    """

    def __init__(self, h_dict, component_name):
        """Initialize the HardCoalSteamTurbine class.

        Args:
            h_dict (dict): Dictionary containing simulation parameters including:
                - rated_capacity: Maximum power output in kW
                - min_stable_load_fraction: Optional, minimum operating point as fraction (0-1).
                    Default: 0.30 (30%) [2]
                - ramp_rate_fraction: Optional, maximum rate of power increase/decrease
                    as fraction of rated capacity per minute. Default: 0.03 (3%) [1,2]
                - run_up_rate_fraction: Optional, maximum rate of power increase during startup
                    as fraction of rated capacity per minute. Default: ramp_rate_fraction
                - hot_startup_time: Optional, time to reach min_stable_load_fraction from off
                    in s. Includes both readying time and ramping time.
                    Default: 27000.0 s (7.5 hours) [1]
                - warm_startup_time: Optional, time to reach min_stable_load_fraction from off
                    in s. Includes both readying time and ramping time.
                    Default: 27000.0 s (7.5 hours) [1]
                - cold_startup_time: Optional, time to reach min_stable_load_fraction from off
                    in s. Includes both readying time and ramping time.
                    Default: 27000.0 s (7.5 hours) [1]
                - min_up_time: Optional, minimum time unit must remain on in s.
                    Default: 172800.0 s (48 hours) [2]
                - min_down_time: Optional, minimum time unit must remain off in s.
                    Default: 172800.0 s (48 hours) [2]
                - initial_conditions: Dictionary with initial power (state is
                    derived automatically: power > 0 means ON, power == 0 means OFF)
                - hhv: Optional, higher heating value of coal (Bituminous) in J/m³.
                    Default: 29,310,000,000 J/m³ (29.31 MJ/kg) [4]
                - fuel_density: Optional, fuel density in kg/m³. https://www.engineeringtoolbox.com/classification-coal-d_164.html
                    Default: 1000 kg/m³
                - efficiency_table: Optional, dictionary with power_fraction and
                    efficiency arrays (both as fractions 0-1). Efficiency values must
                    be HHV net plant efficiencies. Default values are taken from [2,3]:
                    power_fraction = [1.0, 0.5, 0.3],
                    efficiency = [0.35, 0.32, 0.30].

            component_name (str): Unique name for this instance (the YAML top-level key).
        """

        # Apply fixed default parameters based on references
        # back into the h_dict if they are not provided
        if "min_stable_load_fraction" not in h_dict[component_name]:
            h_dict[component_name]["min_stable_load_fraction"] = 0.30
        if "ramp_rate_fraction" not in h_dict[component_name]:
            h_dict[component_name]["ramp_rate_fraction"] = 0.03
        if "hot_startup_time" not in h_dict[component_name]:
            h_dict[component_name]["hot_startup_time"] = 27000.0
        if "warm_startup_time" not in h_dict[component_name]:
            h_dict[component_name]["warm_startup_time"] = 27000.0
        if "cold_startup_time" not in h_dict[component_name]:
            h_dict[component_name]["cold_startup_time"] = 27000.0
        if "min_up_time" not in h_dict[component_name]:
            h_dict[component_name]["min_up_time"] = 172800.0
        if "min_down_time" not in h_dict[component_name]:
            h_dict[component_name]["min_down_time"] = 172800.0

        # If the run_up_rate_fraction is not provided, it defaults to the ramp_rate_fraction
        if "run_up_rate_fraction" not in h_dict[component_name]:
            h_dict[component_name]["run_up_rate_fraction"] = h_dict[component_name][
                "ramp_rate_fraction"
            ]

        # Default HHV for coal (Bituminous)
        if "hhv" not in h_dict[component_name]:
            h_dict[component_name]["hhv"] = 29310000000  # J/m³ (29310 MJ/m³)

        # Default fuel density for coal (Bituminous)
        if "fuel_density" not in h_dict[component_name]:
            h_dict[component_name]["fuel_density"] = 1000.0  # kg/m³

        # Default HHV net plant efficiency table based on [2]:
        if "efficiency_table" not in h_dict[component_name]:
            h_dict[component_name]["efficiency_table"] = {
                "power_fraction": [1.0, 0.5, 0.3],
                "efficiency": [0.35, 0.32, 0.30],
            }

        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)
