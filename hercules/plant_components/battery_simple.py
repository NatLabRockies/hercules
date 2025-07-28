"""
Battery models
Author: Zack tully - zachary.tully@nrel.gov
March 2024

References:
[1] M.-K. Tran et al., “A comprehensive equivalent circuit model for lithium-ion
batteries, incorporating the effects of state of health, state of charge, and
temperature on model parameters,” Journal of Energy Storage, vol. 43, p. 103252,
Nov. 2021, doi: 10.1016/j.est.2021.103252.
"""

import numpy as np
import rainflow
from hercules.plant_components.component_base import ComponentBase


def kJ2kWh(kWh):
    """Convert a value in kWh to kJ"""
    return kWh / 3600


def kWh2kJ(kJ):
    """Convert a value in kJ to kWh"""
    return kJ * 3600


def years_to_usage_rate(years, dt):
    """Convert a number of years to a usage rate
    inputs:
        years: life of the storage system in years
        dt: time step of the simulation, in seconds
    """
    days = years * 365
    hours = days * 24
    seconds = hours * 3600
    usage_lifetime = seconds / dt

    return 1 / usage_lifetime


def cycles_to_usage_rate(cycles):
    """Convert cycle number to degradation rate
    inputs:
        cycles: number of cycles until the unit needs to be replaced
        dt: time step of the simulation, in seconds
    """
    return 1 / cycles


class BatterySimple(ComponentBase):
    # TODO: keep consistent units. Everything in kW or everything in MW but not both
    def __init__(self, h_dict):
        """
        Initializes the BatterySimple class.

        This model represents a simple battery with energy storage and power constraints.
        It tracks state of charge and applies efficiency losses.

        Args:
            h_dict (dict): Dict containing values for the simulation
        """
        # Store the name of this component
        self.component_name = "battery"

        # Store the type of this component
        self.component_type = "BatterySimple"

        # Call the base class init
        super().__init__(h_dict, self.component_name)

        # size = h_dict[self.component_name]["size"]
        self.energy_capacity = h_dict[self.component_name]["energy_capacity"] * 1e3  # [kWh]
        initial_conditions = h_dict[self.component_name]["initial_conditions"]
        self.SOC = initial_conditions["SOC"]  # [fraction]

        self.SOC_max = h_dict[self.component_name]["max_SOC"]
        self.SOC_min = h_dict[self.component_name]["min_SOC"]

        # Charge (Energy) limits [kJ]
        self.E_min = kWh2kJ(self.SOC_min * self.energy_capacity)
        self.E_max = kWh2kJ(self.SOC_max * self.energy_capacity)

        charge_rate = h_dict[self.component_name]["charge_rate"] * 1e3  # [kW]
        discharge_rate = h_dict[self.component_name]["discharge_rate"] * 1e3  # [kW]

        # Charge/discharge (Power) limits [kW]
        self.P_min = -discharge_rate
        self.P_max = charge_rate

        # Ramp up/down limits [kW/s]
        self.R_min = -np.inf
        self.R_max = np.inf

        # Flag for allowing grid to charge the battery
        if "allow_grid_power_consumption" in h_dict[self.component_name].keys():
            self.allow_grid_power_consumption = h_dict[self.component_name][
                "allow_grid_power_consumption"
            ]
        else:
            self.allow_grid_power_consumption = False

        # Efficiency and self-discharge parameters
        if "roundtrip_efficiency" in h_dict[self.component_name].keys():
            self.eta_charge = np.sqrt(h_dict[self.component_name]["roundtrip_efficiency"])
            self.eta_discharge = np.sqrt(h_dict[self.component_name]["roundtrip_efficiency"])
        else:
            self.eta_charge = 1
            self.eta_discharge = 1

        if "self_discharge_time_constant" in h_dict[self.component_name].keys():
            self.tau_self_discharge = h_dict[self.component_name]["self_discharge_time_constant"]
        else:
            self.tau_self_discharge = np.inf

        if "track_usage" in h_dict[self.component_name].keys():
            if h_dict[self.component_name]["track_usage"]:
                self.track_usage = True
                # Set usage tracking parameters
                if "usage_calc_interval" in h_dict[self.component_name].keys():
                    self.usage_calc_interval = (
                        h_dict[self.component_name]["usage_calc_interval"] / self.dt
                    )
                else:
                    self.usage_calc_interval = 100 / self.dt  # timesteps

                if "usage_lifetime" in h_dict[self.component_name].keys():
                    usage_lifetime = h_dict[self.component_name]["usage_lifetime"]
                    self.usage_time_rate = years_to_usage_rate(usage_lifetime, self.dt)
                else:
                    self.usage_time_rate = 0
                if "usage_cycles" in h_dict[self.component_name].keys():
                    usage_cycles = h_dict[self.component_name]["usage_cycles"]
                    self.usage_cycles_rate = cycles_to_usage_rate(usage_cycles)
                else:
                    self.usage_cycles_rate = 0

                # TODO: add the ability to impact efficiency of the battery operation

            else:
                self.track_usage = False
                self.usage_calc_interval = np.inf
        else:
            self.track_usage = False
            self.usage_calc_interval = np.inf

        # Degradation and state storage
        self.P_charge_storage = []
        self.E_store = []
        self.total_cycle_usage = 0
        self.cycle_usage_perc = 0
        self.total_time_usage = 0
        self.time_usage_perc = 0
        self.step_counter = 0
        # TODO there should be a better way to dynamically store these than to append a list

        self.build_SS()
        self.x = np.array([[initial_conditions["SOC"] * self.energy_capacity * 3600]])
        self.y = None

        # self.total_battery_capacity = 3600 * self.energy_capacity / self.dt
        self.current_batt_state = self.SOC * self.energy_capacity
        self.E = kWh2kJ(self.current_batt_state)

        self.power_kw = 0
        self.P_reject = 0
        self.P_charge = 0

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Add any initial conditions or meta data to the h_dict.

        Meta data is data not explicitly in the input yaml but still useful for other
        modules.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Dictionary containing simulation parameters with initial conditions and meta data.
        """

        # Add what we want later

        return h_dict

    def step(self, h_dict):
        self.step_counter += 1

        # power available for the battery to use for charging (should be >=0)
        P_signal = h_dict[self.component_name]["battery_signal"]
        # power signal desired by the controller
        if self.allow_grid_power_consumption:
            P_avail = np.inf
        else:
            P_avail = h_dict["locally_generated_power"]  # [kW] available power

        P_charge, P_reject = self.control(P_avail, P_signal)

        # Update energy state
        # self.E += self.P_charge * self.dt
        self.step_SS(P_charge)
        self.E = self.x[0, 0]  # TODO find a better way to make self.x 1-D

        self.current_batt_state = kJ2kWh(self.E)

        self.power_kw = P_charge
        self.SOC = self.current_batt_state / self.energy_capacity

        self.P_charge_storage.append(P_charge)
        self.E_store.append(self.E)

        if self.step_counter >= self.usage_calc_interval:
            # reset step_counter
            self.step_counter = 0
            self.calc_usage()

        # Update the outputs
        h_dict[self.component_name]["power"] = self.power_kw
        h_dict[self.component_name]["reject"] = P_reject
        h_dict[self.component_name]["soc"] = self.SOC
        h_dict[self.component_name]["usage_in_time"] = self.time_usage_perc
        h_dict[self.component_name]["usage_in_cycles"] = self.cycle_usage_perc
        h_dict[self.component_name]["total_cycles"] = self.total_cycle_usage

        # Return the updated dictionary
        return h_dict

    def control(self, P_avail, P_signal):
        """
        Low-level controller to enforce charging and energy constraints

        Inputs
        - P_avail: [kW] the available power for charging
        - P_signal: [kW] the desired charging power

        Outputs
        - P_charge: [kW] (positive of negative) the charging/discharging power
        - P_reject: [kW] (positive or negative) either the extra power that the
                    battery cannot absorb (positive) or the power required but
                    not provided for the battery to charge/discharge without violating
                    constraints (negative)
        """

        # TODO remove ramp rate constraints because they are never used?

        # Upper constraints [kW]
        # c_hi1 = (self.E_max - self.E) / self.dt  # energy
        c_hi1 = self.SS_input_function_inverse((self.E_max - self.x[0, 0]) / self.dt)
        c_hi2 = self.P_max  # power
        c_hi3 = self.R_max * self.dt + self.P_charge  # ramp rate
        c_hi4 = P_avail

        # Lower constraints [kW]
        # c_lo1 = (self.E_min - self.E) / self.dt  # energy
        c_lo1 = self.SS_input_function_inverse((self.E_min - self.x[0, 0]) / self.dt)
        c_lo2 = self.P_min  # power
        c_lo3 = self.R_min * self.dt + self.P_charge  # ramp rate

        # High constraint is the most restrictive of the high constraints
        c_hi = np.min([c_hi1, c_hi2, c_hi3, c_hi4])
        c_hi = np.max([c_hi, 0])

        # Low constraint is the most restrictive of the low constraints
        c_lo = np.max([c_lo1, c_lo2, c_lo3])
        c_lo = np.min([c_lo, 0])

        # TODO: force low constraint to be no higher than lowest high constraint
        if (P_signal >= c_lo) & (P_signal <= c_hi):
            P_charge = P_signal
            P_reject = 0
        elif P_signal < c_lo:
            P_charge = c_lo
            P_reject = P_signal - P_charge
        elif P_signal > c_hi:
            P_charge = c_hi
            P_reject = P_signal - P_charge

        self.P_charge = P_charge
        self.P_reject = P_reject

        return P_charge, P_reject

    def build_SS(self):
        self.A = np.array([[-1 / self.tau_self_discharge]])
        # B is the function in
        self.C = np.array([[1, 0]]).T
        self.D = np.array([[0, 1]]).T

    def SS_input_function(self, P_charge):
        # P_in is the amount of power that actually gets stored in the state E
        # P_charge is the amount of power given to the charging physics

        if P_charge >= 0:
            P_in = self.eta_charge * P_charge
        else:
            P_in = P_charge / self.eta_discharge
        return P_in

    def SS_input_function_inverse(self, P_in):
        if P_in >= 0:
            P_charge = P_in / self.eta_charge
        else:
            P_charge = P_in * self.eta_discharge
        return P_charge

    def step_SS(self, u):
        # Advance the state-space loop
        xd = self.A * self.x + self.SS_input_function(u)
        y = self.C * self.x + self.D * u

        self.x = self.integrate(self.x, xd)
        self.y = y

    def integrate(self, x, xd):
        # better integration -> use the closed form step response solution?
        return x + xd * self.dt  # Euler integration

    def calc_usage(self):
        # Count rainflow cycles
        # This step uses sthe rainflow algorithm to count how many cycles exist in the
        #   storage operation using the three-point technique (ASTM Standard E 1049-85)
        #   The algorithm returns the size (amplitude) of the cycle, and the number of cycles at
        #       that amplitude at that point in the signal
        ranges_counts = rainflow.count_cycles(self.E_store)
        ranges = np.array([rc[0] for rc in ranges_counts])
        counts = np.array([rc[1] for rc in ranges_counts])
        self.total_cycle_usage = (ranges * counts).sum() / self.E_max
        self.cycle_usage_perc = self.total_cycle_usage * self.usage_cycles_rate * 100

        # Calculate time usage
        self.total_time_usage += self.usage_calc_interval * self.dt
        self.time_usage_perc = self.total_time_usage * self.usage_time_rate * 100

        # self.apply_degradation(this_period_degradation)

    def apply_degradation(self, degradation):
        # total_degradation_effect = self.total_degradation*self.degradation_rate
        # print('degradation penalty', total_degradation_effect, np.sqrt(total_degradation_effect))
        # self.eta_charge = self.eta_charge - np.sqrt(total_degradation_effect)
        # self.eta_discharge = self.eta_discharge - np.sqrt(total_degradation_effect)
        raise NotImplementedError(
            "Degradation impacts on real-time efficiency have not yet been implemented."
        )
