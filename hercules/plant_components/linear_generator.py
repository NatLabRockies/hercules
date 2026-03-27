"""
Linear Generator Class.

Linear generator model is a subclass of the ThermalComponentBase class.
Default parameters are based on aeroderivative linear generators as described
in the example configuration for the multi-unit thermal plant.

Like other subclasses of ThermalComponentBase, it inherits the main control
functions, and adds defaults for many variables appropriate for linear generators.

Note: All efficiency values are HHV (Higher Heating Value) net plant efficiencies.
The default efficiency table is sourced from the Mainspring Energy Linear Generator
datasheet [1].

References:

[1] Mainspring Energy, "Linear Generator Datasheet," Rev. R30313.3, March 16, 2026.
    https://linear-power.files.svdcdn.com/production/Mainspring-Linear-Generator-Datasheet-R30313.3_2026-03-16-205457_psod.pdf
[2] https://www.energy.ca.gov/sites/default/files/2024-05/CEC-500-2024-037.pdf
[3] I. Staffell, "The Energy and Fuel Data Sheet," University of Birmingham, March 2011.
    https://claverton-energy.com/cms4/wp-content/uploads/2012/08/the_energy_and_fuel_data_sheet.pdf
"""

from hercules.plant_components.thermal_component_base import ThermalComponentBase


class LinearGenerator(ThermalComponentBase):
    """Linear generator model.

    This model represents a linear generator with state management, ramp rate
    constraints, minimum stable load, and fuel consumption tracking. Note it is
    a subclass of the ThermalComponentBase class.

    All efficiency values are HHV (Higher Heating Value) net plant efficiencies.
    """

    def __init__(self, h_dict, component_name):
        """Initialize the LinearGenerator class.

        Args:
            h_dict (dict): Dictionary containing simulation parameters including:
                - rated_capacity: Maximum power output in kW
                - min_stable_load_fraction: Optional, minimum operating point as fraction (0-1).
                    Default: 0.0
                - ramp_rate_fraction: Optional, maximum rate of power increase/decrease
                    as fraction of rated capacity per minute. Default: 1.2
                - run_up_rate_fraction: Optional, maximum rate of power increase during startup
                    as fraction of rated capacity per minute. Default: ramp_rate_fraction
                - hot_startup_time: Optional, time to reach min_stable_load_fraction from off
                    in s. Default: 420.0 s (7 minutes)
                - warm_startup_time: Optional, time to reach min_stable_load_fraction from off
                    in s. Default: 480.0 s (8 minutes)
                - cold_startup_time: Optional, time to reach min_stable_load_fraction from off
                    in s. Default: 480.0 s (8 minutes)
                - min_up_time: Optional, minimum time unit must remain on in s.
                    Default: 3600.0 s (1 hour)
                - min_down_time: Optional, minimum time unit must remain off in s.
                    Default: 3600.0 s (1 hour)
                - initial_conditions: Dictionary with initial power (state is
                    derived automatically: power > 0 means ON, power == 0 means OFF)
                - hhv: Optional, higher heating value of natural gas in J/m³.
                    Default: 39050000 J/m³ (39.05 MJ/m³) [3]
                - fuel_density: Optional, fuel density in kg/m³.
                    Default: 0.768 kg/m³ [3]
                - efficiency_table: Optional, dictionary with power_fraction and
                    efficiency arrays (both as fractions 0-1). Efficiency values must
                    be HHV net plant efficiencies. Default values from [1]:
                    power_fraction = [1.0, 0.0],
                    efficiency = [0.4144, 0.4144].
            component_name (str): Unique name for this instance (the YAML top-level key).
        """

        # Apply default parameters back into h_dict if not provided
        if "min_stable_load_fraction" not in h_dict[component_name]:
            h_dict[component_name]["min_stable_load_fraction"] = 0.0
        if "ramp_rate_fraction" not in h_dict[component_name]:
            h_dict[component_name]["ramp_rate_fraction"] = 1.2
        if "hot_startup_time" not in h_dict[component_name]:
            h_dict[component_name]["hot_startup_time"] = 420.0
        if "warm_startup_time" not in h_dict[component_name]:
            h_dict[component_name]["warm_startup_time"] = 480.0
        if "cold_startup_time" not in h_dict[component_name]:
            h_dict[component_name]["cold_startup_time"] = 480.0
        if "min_up_time" not in h_dict[component_name]:
            h_dict[component_name]["min_up_time"] = 3600.0
        if "min_down_time" not in h_dict[component_name]:
            h_dict[component_name]["min_down_time"] = 3600.0

        # If run_up_rate_fraction is not provided, it defaults to ramp_rate_fraction
        if "run_up_rate_fraction" not in h_dict[component_name]:
            h_dict[component_name]["run_up_rate_fraction"] = h_dict[component_name][
                "ramp_rate_fraction"
            ]

        # Default HHV for natural gas (39.05 MJ/m³) from [3]
        if "hhv" not in h_dict[component_name]:
            h_dict[component_name]["hhv"] = 39050000  # J/m³ (39.05 MJ/m³)

        # Default fuel density for natural gas (0.768 kg/m³) from [3]
        if "fuel_density" not in h_dict[component_name]:
            h_dict[component_name]["fuel_density"] = 0.768  # kg/m³

        # Default HHV net plant efficiency table from [1]
        if "efficiency_table" not in h_dict[component_name]:
            h_dict[component_name]["efficiency_table"] = {
                "power_fraction": [1.0, 0.0],
                "efficiency": [0.4144, 0.4144],
            }

        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)
