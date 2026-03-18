"""
Steam turbine model, for use as a standalone component or part of a multi-unit thermal plant.
"""

from hercules.plant_components.thermal_component_base import ThermalComponentBase


class SteamTurbine(ThermalComponentBase):
    """Steam turbine model.

    This model represents an steam turbine with state management, ramp rate constraints, minimum
    stable load, and fuel consumption tracking. Note it is a subclass of the ThermalComponentBase
    class.

    All efficiency values are HHV (Higher Heating Value) net plant efficiencies.
    """

    def __init__(self, h_dict, component_name):
        """Initialize the SteamTurbine class.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
                Defaults are specified below.
            component_name (str): Unique name for this component instance.
        """

        # Specify default parameter values
        default_parameters_steam_turbine = {
            "min_stable_load_fraction": 0.30,
            "ramp_rate_fraction": 0.03,
            "hot_startup_time": 27000.0,
            "warm_startup_time": 27000.0,
            "cold_startup_time": 27000.0,
            "min_up_time": 172800.0,
            "min_down_time": 172800.0,
            "hhv": 29310000000,  # J/m³
            "fuel_density": 1000,  # kg/m³
            "efficiency_table": {
                "power_fraction": [1.0, 0.5, 0.3],
                "efficiency": [0.35, 0.32, 0.30],
            },
        }

        # Update the input dictionary with default values for any missing parameters
        h_dict[component_name] = default_parameters_steam_turbine | h_dict[component_name]

        # If the run_up_rate_fraction is not provided, it defaults to the ramp_rate_fraction
        if "run_up_rate_fraction" not in h_dict[component_name]:
            h_dict[component_name]["run_up_rate_fraction"] = h_dict[component_name][
                "ramp_rate_fraction"
            ]

        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)
