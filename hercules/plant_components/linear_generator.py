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

    Class Attributes:
        DEFAULTS (dict): Default parameter values applied when a key is absent from
            the input dictionary. Tests should reference this dict directly rather
            than hardcoding expected values. Note that ``run_up_rate_fraction`` is
            not included here because its default is derived from
            ``ramp_rate_fraction`` at runtime.
    """

    DEFAULTS = {
        "min_stable_load_fraction": 0.0,
        "ramp_rate_fraction": 1.2,  # fraction of rated capacity per minute [2]
        "hot_startup_time": 90.0,  # s (1.5 minutes)
        "warm_startup_time": 450.0,  # s (7.5 minutes)
        "cold_startup_time": 900.0,  # s (15 minutes)
        "min_up_time": 300.0,  # s (5 minutes)
        "min_down_time": 300.0,  # s (5 minutes)
        "hot_to_warm_time": 2700.0,  # s (45 minutes)
        "hot_to_cold_time": 10800.0,  # s (3 hours)
        "hhv": 39050000,  # J/m³ (39.05 MJ/m³) for natural gas [3]
        "fuel_density": 0.768,  # kg/m³ for natural gas [3]
        "efficiency_table": {  # HHV net plant efficiency from [1]
            "power_fraction": [1.0, 0.0],
            "efficiency": [0.4144, 0.4144],
        },
    }

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
                    in s. Default: 90.0 s (1.5 minutes)
                - warm_startup_time: Optional, time to reach min_stable_load_fraction from off
                    in s. Default: 450.0 s (7.5 minutes)
                - cold_startup_time: Optional, time to reach min_stable_load_fraction from off
                    in s. Default: 900.0 s (15 minutes)
                - min_up_time: Optional, minimum time unit must remain on in s.
                    Default: 300.0 s (5 minutes)
                - min_down_time: Optional, minimum time unit must remain off in s.
                    Default: 300.0 s (5 minutes)
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

        # Apply DEFAULTS for any parameter not present in h_dict
        for key, value in self.DEFAULTS.items():
            if key not in h_dict[component_name]:
                h_dict[component_name][key] = value

        # run_up_rate_fraction is not in DEFAULTS because it derives from ramp_rate_fraction
        if "run_up_rate_fraction" not in h_dict[component_name]:
            h_dict[component_name]["run_up_rate_fraction"] = h_dict[component_name][
                "ramp_rate_fraction"
            ]

        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)
