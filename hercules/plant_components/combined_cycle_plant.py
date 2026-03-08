"""
Multiunit combined cycle gas power plant.
This plant has both an open cycle gas turbine and steam turbine. The steam turbine is modeled
as a single unit with a power output that is a function of the open cycle gas turbine power output.
"""
import copy

import hercules.hybrid_plant as hp
from hercules.plant_components.component_base import ComponentBase
from hercules.plant_components.thermal_component_base import ThermalComponentBase


class CombinedCyclePlant(ComponentBase):
    """ """

    component_category = "generator"

    def __init__(self, h_dict, component_name):
        # Instantiate individual units from the h_dict.

        self.component_name = component_name
        self.component_type = "combined_cycle_plant"

        self.unit_names = h_dict[component_name]["unit_names"]
        generic_units = h_dict[component_name]["units"]
        if not "steam_turbine" in generic_units:
            raise ValueError("For the combined cycle plant, one of the units must be a steam turbine.")
        if not "open_cycle_gas_turbine" in generic_units:
            raise ValueError("For the combined cycle plant, one of the units must be an open cycle gas turbine.")

        for unit, unit_name in zip(generic_units, self.unit_names):
            if unit not in ["open_cycle_gas_turbine", "steam_turbine"]:
                raise ValueError("For the combined cycle plant, units must be either 'open_cycle_gas_turbine' or 'steam_turbine'.")
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
        if (self.units[self.gas_turbine_index].power_output == 0 and 
           self.units[self.steam_turbine_index].power_output > 0):
            raise ValueError(
                "Invalid initial conditions: steam turbine cannot be producing power if "
                "the open cycle gas turbine is not producing power."
            )
        
        self.gas_power_ratio = (
            self.units[self.gas_turbine_index].rated_capacity /
            (self.units[self.steam_turbine_index].rated_capacity + 
             self.units[self.gas_turbine_index].rated_capacity)
        )

        # Derive initial state from power: if power > 0 then ON, else OFF
        for unit in self.units:
            if unit.power_output > 0:
                unit.state = unit.STATES.ON
                # Set time_in_state so the unit is immediately ready to stop
                unit.time_in_state = float(unit.min_up_time)  # s
            else:
                unit.state = unit.STATES.OFF
                # Set time_in_state so the unit is immediately ready to start
                if "time_in_shutdown" in initial_conditions:
                    unit.time_in_state = float(initial_conditions["time_in_shutdown"])  # s
                else:
                    unit.time_in_state = float(unit.min_down_time)  # s

        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)

    def step(self, h_dict):
        
        power_setpoint = h_dict[self.component_name]["power_setpoint"]

         # Determine power setpoints for the units based on the overall combined cycle plant power setpoint
        power_setpoints = [0] * len(self.units)

        # TODO: look at better setpoints that make gas produce more power when steam is still down
        power_setpoints[self.gas_turbine_index] = self.gas_power_ratio * power_setpoint
        power_setpoints[self.steam_turbine_index] = (1 - self.gas_power_ratio) * power_setpoint
        
        # Check that the power setpoint is a number
        if not isinstance(power_setpoint, (int, float)):
            raise ValueError("power_setpoint must be a number")

        # Apply control
        self.power_output = sum(self.control(power_setpoints))

        # Step each unit
        for unit, unit_name, power_setpoint in zip(
            self.units, self.unit_names, power_setpoints
        ):
            h_dict_ccgt = h_dict[self.component_name]
            h_dict_ccgt[unit_name]["power_setpoint"] = power_setpoint
            h_dict_ccgt = unit.step(h_dict_ccgt)

        # Update h_dict with outputs
        h_dict[self.component_name]["power"] = self.power_output
        # h_dict[self.component_name]["state"] = self.state.value
        # h_dict[self.component_name]["efficiency"] = self.efficiency
        # h_dict[self.component_name]["fuel_volume_rate"] = self.fuel_volume_rate
        # h_dict[self.component_name]["fuel_mass_rate"] = self.fuel_mass_rate

        return h_dict

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Get initial conditions and metadata for the ccgt plant.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
        """
        for unit in self.units:
            h_dict_ccgt = h_dict[self.component_name]
            h_dict_ccgt = unit.get_initial_conditions_and_meta_data(h_dict_ccgt)

        h_dict[self.component_name]["power"] = sum(
            h_dict_ccgt[unit.component_name]["power"] for unit in self.units
        )

        # TODO: we likely want to save off data for the individual units to the
        # h_dict as well. Will need to figure out how to do that.

        return h_dict

    def control(self, power_setpoints):
        """"""
        
        # TODO: we probably want to add an actual controller for the gas turbine
        self.units[self.gas_turbine_index].power_output = self.units[self.gas_turbine_index]._control(power_setpoints[self.gas_turbine_index])

        if (self.units[self.gas_turbine_index].state == self.units[self.gas_turbine_index].STATES.ON and 
            self.units[self.steam_turbine_index].state != self.units[self.steam_turbine_index].STATES.OFF):
            self.units[self.steam_turbine_index].power_output = self.units[self.steam_turbine_index]._control(power_setpoints[self.steam_turbine_index])
        else:
            self.units[self.steam_turbine_index].power_output = self.control_steam_turbine(power_setpoints)

        return [unit.power_output for unit in self.units]

    
    def control_steam_turbine(self, power_setpoints):
        """
        What I want to do:
        - If the gas turbine is off, or starting up, the steam turbine should be off.
        - If the gas turbine goes from startup to on, the steam turbine startup process should begin.
        - Can we use self.units[].time_in_state to delay the startup until the gas turbine is turned on?
        - Current status: might actually be working already. Check what happens.
        """
        
        if self.units[self.gas_turbine_index].state == "STOPPING" and self.units[self.steam_turbine_index].power_output > 0:
            # If the gas turbine is stopping but the steam turbine is still producing power, we need to turn off the steam turbine
            self.units[self.steam_turbine_index].state = "STOPPING"
            self.units[self.steam_turbine_index]._control(0.0)
            self.units[self.steam_turbine_index].starting_now = False
        # if self.units[self.gas_turbine_index].state == (
        #     self.units[self.gas_turbine_index].STATES.HOT_STARTING or
        #     self.units[self.gas_turbine_index].STATES.WARM_STARTING or 
        #     self.units[self.gas_turbine_index].STATES.COLD_STARTING):
        #     # If the gas turbine is not on, the steam turbine should be off
        #     self.units[self.steam_turbine_index].state = self.units[self.steam_turbine_index].STATES.OFF
        #     self.units[self.steam_turbine_index]._control(0.0)
        elif (self.units[self.gas_turbine_index].state == self.units[self.gas_turbine_index].STATES.ON and 
            self.units[self.steam_turbine_index].state == self.units[self.steam_turbine_index].STATES.OFF):
            # If the gas turbine just turned on and the steam turbine is still off, we need to start up the steam turbine
            if (not self.units[self.steam_turbine_index].starting_now or
                not hasattr(self.units[self.steam_turbine_index], 'starting_now')):
                self.units[self.steam_turbine_index].time_in_state = 0.0  # Reset time in state to start the startup process
                self.units[self.steam_turbine_index].starting_now = True
            power_setpoint = (1 - self.gas_power_ratio) * sum(power_setpoints)
            self.units[self.steam_turbine_index]._control(power_setpoint)
        else:
            self.units[self.steam_turbine_index]._control(power_setpoints[self.steam_turbine_index])
            self.units[self.steam_turbine_index].starting_now = False

        return self.units[self.steam_turbine_index].power_output
        
        # self.units[self.steam_turbine_index].state = "OFF"




