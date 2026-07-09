"""
Multiunit combined cycle gas power plant.
This plant has both an open cycle gas turbine and steam turbine. The steam turbine is modeled
as a single unit with a power output that is a function of the open cycle gas turbine power output.
"""

import copy

import hercules.hybrid_plant as hp
import numpy as np
from hercules.plant_components.component_base import ComponentBase
from hercules.plant_components.thermal_component_base import ThermalComponentBase
from hercules.utilities import hercules_float_type


class CombinedCyclePlant(ComponentBase):
    """ """

    component_category = "generator"

    def __init__(self, h_dict, component_name):
        # Instantiate individual units from the h_dict.

        self.component_name = component_name
        self.component_type = "combined_cycle_plant"

        self.unit_names = h_dict[component_name]["unit_names"]
        generic_units = h_dict[component_name]["units"]
        if "steam_turbine" not in generic_units:
            raise ValueError(
                "For the combined cycle plant, one of the units must be a steam turbine."
            )
        if "open_cycle_gas_turbine" not in generic_units:
            raise ValueError(
                "For the combined cycle plant, one of the units must be an open cycle gas turbine."
            )

        if len(generic_units) != 2:
            raise ValueError(
                "For the combined cycle plant, there must be exactly two units: "
                "one steam turbine and one open cycle gas turbine."
            )

        for unit, unit_name in zip(generic_units, self.unit_names):
            if unit not in ["open_cycle_gas_turbine", "steam_turbine"]:
                raise ValueError(
                    "For the combined cycle plant, units must be either "
                    "'open_cycle_gas_turbine' or 'steam_turbine'."
                )
            if unit_name not in h_dict[component_name]:
                h_dict[component_name][unit_name] = copy.deepcopy(h_dict[component_name][unit])

        # Remove the template from the component dict since it's now copied into each unit dict
        for unit in generic_units:
            if unit in h_dict[component_name]:
                del h_dict[component_name][unit]

        self.units = []
        self.unit_types = []
        for unit, unit_name in zip(h_dict[component_name]["units"], self.unit_names):
            h_dict_ccgt = h_dict[component_name]
            h_dict_ccgt["dt"] = h_dict["dt"]
            h_dict_ccgt["starttime"] = h_dict["starttime"]
            h_dict_ccgt["endtime"] = h_dict["endtime"]
            h_dict_ccgt["verbose"] = h_dict["verbose"]
            unit_type = h_dict["combined_cycle_plant"][unit_name]["component_type"]
            unit_class = hp.COMPONENT_REGISTRY[unit_type]
            if unit_class is None:
                raise ValueError(f"Unit type {unit_type} not found in component registry.")
            elif not issubclass(unit_class, ThermalComponentBase):
                raise ValueError(
                    f"Unit type {unit_type} must be a subclass of ThermalComponentBase."
                )
            else:
                self.units.append(unit_class(h_dict_ccgt, unit_name))
                self.unit_types.append(unit_type)

        # Extract initial conditions
        self.power_output = 0.0
        for unit_name in self.unit_names:
            initial_conditions = h_dict[component_name][unit_name]["initial_conditions"]
            self.power_output += initial_conditions["power"]  # kW

        h_dict[component_name]["power"] = self.power_output

        self.steam_turbine_index = self.unit_types.index("SteamTurbine")
        self.gas_turbine_index = self.unit_types.index("OpenCycleGasTurbine")

        # Check that initial conditions are valid
        if (
            self.units[self.gas_turbine_index].power_output == 0
            and self.units[self.steam_turbine_index].power_output > 0
        ):
            raise ValueError(
                "Invalid initial conditions: steam turbine cannot be producing power if "
                "the open cycle gas turbine is not producing power."
            )

        self.gas_power_ratio = self.units[self.gas_turbine_index].rated_capacity / (
            self.units[self.steam_turbine_index].rated_capacity
            + self.units[self.gas_turbine_index].rated_capacity
        )

        # Default HHV net plant efficiency table based on [2]:
        if "efficiency_table" not in h_dict[component_name]:
            h_dict[component_name]["efficiency_table"] = {
                "power_fraction": [
                    1.0,
                    0.95,
                    0.90,
                    0.85,
                    0.80,
                    0.75,
                    0.7,
                    0.65,
                    0.6,
                    0.55,
                    0.50,
                    0.4,
                ],
                "efficiency": [
                    0.53,
                    0.515,
                    0.52,
                    0.52,
                    0.52,
                    0.52,
                    0.52,
                    0.515,
                    0.505,
                    0.5,
                    0.47,
                    0.47,
                ],
            }

        efficiency_table = h_dict[component_name]["efficiency_table"]

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

        self.rated_capacity = (
            self.units[self.gas_turbine_index].rated_capacity
            + self.units[self.steam_turbine_index].rated_capacity
        )
        h_dict[component_name]["rated_capacity"] = self.rated_capacity

        # Derive initial state from power: if power > 0 then ON, else OFF
        for unit in self.units:
            if unit.power_output > 0:
                unit.state = unit.STATES.ON
                # Set time_in_state so the unit is immediately ready to stop
                unit.time_in_state = float(unit.min_up_time)  # s
            else:
                unit.state = unit._is_off()
                # Set time_in_state so the unit is immediately ready to start
                if "time_in_shutdown" in initial_conditions:
                    unit.time_in_state = float(initial_conditions["time_in_shutdown"])  # s
                else:
                    unit.time_in_state = float(unit.min_down_time)  # s

        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)

    def step(self, h_dict):

        power_setpoint = h_dict[self.component_name]["power_setpoint"]

        # Update time in state
        for unit in self.units:
            unit.time_in_state += unit.dt

        # Apply control
        self.power_output = sum(self.control(power_setpoint))

        for unit, unit_name in zip(self.units, self.unit_names):
            h_dict_ccgt = h_dict[self.component_name]
            h_dict_ccgt = unit.get_initial_conditions_and_meta_data(h_dict_ccgt)
            h_dict_ccgt[unit_name]["power_setpoint"] = unit.power_setpoint

        self.efficiency = self.calculate_efficiency(self.power_output)

        self.fuel_volume_rate = self.calculate_fuel_volume_rate(self.power_output)
        self.fuel_mass_rate = (
            self.fuel_volume_rate * self.units[self.gas_turbine_index].fuel_density
        )

        # Update h_dict with outputs
        h_dict[self.component_name]["power"] = self.power_output
        # h_dict[self.component_name]["state"] = self.state.value
        h_dict[self.component_name]["efficiency"] = self.efficiency
        h_dict[self.component_name]["fuel_volume_rate"] = self.fuel_volume_rate
        h_dict[self.component_name]["fuel_mass_rate"] = self.fuel_mass_rate

        return h_dict

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Get initial conditions and metadata for the ccgt plant.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
        """
        for unit, unit_name in zip(self.units, self.unit_names):
            h_dict_ccgt = h_dict[self.component_name]
            h_dict_ccgt = unit.get_initial_conditions_and_meta_data(h_dict_ccgt)

        h_dict[self.component_name]["power"] = self.power_output

        # TODO: we likely want to save off data for the individual units to the
        # h_dict as well. Will need to figure out how to do that.

        return h_dict

    def control(self, power_setpoint):
        """"""

        # Check that the power setpoint is a number
        if not isinstance(power_setpoint, (int, float)):
            raise ValueError("power_setpoint must be a number")

        # Set gas turbine power setpoint
        self.units[self.gas_turbine_index].power_setpoint = self.gas_power_ratio * power_setpoint
        self.units[self.steam_turbine_index].power_setpoint = (
            1 - self.gas_power_ratio
        ) * power_setpoint

        # TODO: we probably want to add an actual controller for the gas turbine
        self.units[self.gas_turbine_index].power_output = self.units[
            self.gas_turbine_index
        ]._control(self.units[self.gas_turbine_index].power_setpoint)
        self.units[self.steam_turbine_index].power_output = self.control_steam_turbine(
            self.units[self.steam_turbine_index].power_setpoint
        )

        return [unit.power_output for unit in self.units]

    def control_steam_turbine(self, power_setpoint):
        """
        Control the steam turbine based on the gas turbine's state and the desired power setpoint.

        - If the gas turbine is off, or starting up, the steam turbine should be off.
        - If the gas turbine goes from startup to on, the steam turbine startup process should begin
        - Otherwise, use regular control based on the power setpoint.
        """
        if self.units[self.gas_turbine_index].state != (
            self.units[self.gas_turbine_index].STATES.ON
            or self.units[self.gas_turbine_index].STATES.STOPPING
        ):
            # If the gas turbine is off or starting up, the steam turbine should be off
            self.units[self.steam_turbine_index].can_start = False
            self.units[self.steam_turbine_index].power_output = self.units[
                self.steam_turbine_index
            ]._control(0.0)
        elif (
            self.units[self.gas_turbine_index].state == "STOPPING"
            and self.units[self.steam_turbine_index].power_output > 0
            or self.units[self.steam_turbine_index].state
            == self.units[self.steam_turbine_index].STATES.STOPPING
        ):
            # If the gas turbine is stopping but the steam turbine is still producing power,
            # we need to turn off the steam turbine
            self.units[self.steam_turbine_index].power_output = self.units[
                self.steam_turbine_index
            ]._control(0.0)
        elif (
            self.units[self.gas_turbine_index].state == self.units[self.gas_turbine_index].STATES.ON
            and self.units[self.steam_turbine_index].state
            == self.units[self.steam_turbine_index]._is_off()
        ):
            # If the gas turbine just turned on and the steam turbine is still off,
            # we need to start up the steam turbine
            self.units[self.steam_turbine_index].can_start = (
                self.units[self.steam_turbine_index].time_in_state
                >= self.units[self.steam_turbine_index].min_down_time
            )
            self.units[self.steam_turbine_index].power_output = self.units[
                self.steam_turbine_index
            ]._control(power_setpoint)
        else:
            # Normal operation
            self.units[self.steam_turbine_index].power_output = self.units[
                self.steam_turbine_index
            ]._control(power_setpoint)

        return self.units[self.steam_turbine_index].power_output

    def calculate_efficiency(self, power_output):
        """Calculate HHV net efficiency based on current power output.

        Uses linear interpolation from the efficiency table. Values outside the
        table range are clamped to the nearest endpoint.

        Args:
            power_output (float): Current power output in kW.

        Returns:
            float: HHV net efficiency as a fraction (0-1).
        """
        if self.units[self.gas_turbine_index].state == (
            self.units[self.gas_turbine_index]._is_off()
        ):
            # Efficiency is not defined when off
            return np.nan
        elif self.units[self.gas_turbine_index].state == (
            self.units[self.gas_turbine_index].STATES.STOPPING
        ):
            # Efficiency is not defined when stopping
            return np.nan
        elif power_output <= 0:
            # Efficiency is 0 when gas turbine not producing power (but not off)
            return 0.0
        elif (
            self.units[self.steam_turbine_index].state
            == self.units[self.steam_turbine_index]._is_off()
        ):
            # If the steam turbine is not on, we are just running the gas turbine,
            # so efficiency is based on gas turbine power output
            return self.units[self.gas_turbine_index].calculate_efficiency(
                self.units[self.gas_turbine_index].power_output
            )
        elif self.units[self.steam_turbine_index].state != (
            self.units[self.steam_turbine_index].STATES.ON
            or self.units[self.steam_turbine_index].STATES.STOPPING
        ):
            # If the steam turbine is starting up, it might be producing power,
            # increasing the overall efficiency
            efficiency_gas = self.units[self.gas_turbine_index].calculate_efficiency(
                self.units[self.gas_turbine_index].power_output
            )
            fuel_used = (self.units[self.gas_turbine_index].power_output * 1000.0) / (
                efficiency_gas * self.units[self.gas_turbine_index].hhv
            )
            return power_output * 1000.0 / (fuel_used * self.units[self.gas_turbine_index].hhv)

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
        fuel_m3_per_s = (power_output * 1000.0) / (
            efficiency * self.units[self.gas_turbine_index].hhv
        )

        return fuel_m3_per_s
