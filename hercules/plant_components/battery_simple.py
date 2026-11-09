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
from hercules.plant_components.component_base import ComponentBase
from hercules.utilities import hercules_float_type

_REMOVED_KEYS = ("track_usage", "usage_calc_interval", "usage_lifetime", "usage_cycles")


def kJ2kWh(kJ):
    """Convert a value in kJ to kWh.

    Args:
        kJ (float): Energy value in kilojoules.

    Returns:
        float: Energy value in kilowatt-hours.
    """
    return kJ / 3600


def kWh2kJ(kWh):
    """Convert a value in kWh to kJ.

    Args:
        kWh (float): Energy value in kilowatt-hours.

    Returns:
        float: Energy value in kilojoules.
    """
    return kWh * 3600


class BatterySimple(ComponentBase):
    """Simple battery energy storage model.

    This model represents a basic battery with energy storage and power constraints.
    It tracks state of charge and applies roundtrip efficiency losses on charging.

    Note:
        All power units are in kW and energy units are in kWh.
    """

    component_category = "storage"

    def __init__(self, h_dict, component_name):
        """Initialize the BatterySimple class.

        This model represents a simple battery with energy storage and power constraints.
        It tracks state of charge and applies efficiency losses.

        Args:
            h_dict (dict): Dictionary containing simulation parameters including:
                - energy_capacity: Deliverable energy capacity in kWh (energy
                    discharged at the terminals from SOC 1 to 0)
                - charge_rate: Maximum charge rate in kW
                - discharge_rate: Maximum discharge rate in kW
                - max_SOC: Optional maximum state of charge (0-1, default 1.0).
                    Values below 1.0 indicate a deviation from nameplate
                    performance (e.g., degradation) and reduce deliverable energy.
                - min_SOC: Optional minimum state of charge (0-1, default 0.0).
                    Values above 0.0 indicate a deviation from nameplate
                    performance (e.g., degradation) and reduce deliverable energy.
                - initial_conditions: Dictionary with initial SOC
                - allow_grid_power_consumption: Optional, defaults to False
                - roundtrip_efficiency: Optional roundtrip efficiency (0-1), applied
                    on charging
                - self_discharge_time_constant: Optional self-discharge time constant
                    in seconds
            component_name (str): Unique name for this instance (the YAML top-level key).

        Raises:
            ValueError: If removed usage-tracking keys are specified.
        """

        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)

        removed = [k for k in _REMOVED_KEYS if k in h_dict[self.component_name]]
        if removed:
            raise ValueError(
                f"{self.component_name}: {removed} are no longer supported by BatterySimple. "
                "Usage tracking was removed; compute cycle metrics from the outputs instead."
            )

        self.energy_capacity = h_dict[self.component_name]["energy_capacity"]  # [kWh]
        initial_conditions = h_dict[self.component_name]["initial_conditions"]
        self.SOC = initial_conditions["SOC"]  # [fraction]

        # SOC limits default to 0 and 1 (full nameplate capacity). Values other
        # than 0/1 represent a deviation from nameplate performance such as
        # degradation, and will reduce the deliverable energy below the rated
        # energy_capacity / discharge_rate duration.
        self.SOC_max = h_dict[self.component_name].get("max_SOC", 1.0)
        self.SOC_min = h_dict[self.component_name].get("min_SOC", 0.0)

        charge_rate = h_dict[self.component_name]["charge_rate"]  # [kW]
        discharge_rate = h_dict[self.component_name]["discharge_rate"]  # [kW]

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

        # Roundtrip efficiency is applied entirely on charging, so stored energy equals
        # deliverable energy and discharge duration = energy_capacity / discharge_rate.
        self.eta_charge = h_dict[self.component_name].get("roundtrip_efficiency", 1.0)
        self.eta_discharge = 1.0

        # Charge (Energy) limits [kJ]
        self.E_min = kWh2kJ(self.SOC_min * self.energy_capacity)
        self.E_max = kWh2kJ(self.SOC_max * self.energy_capacity)

        if "self_discharge_time_constant" in h_dict[self.component_name].keys():
            self.tau_self_discharge = h_dict[self.component_name]["self_discharge_time_constant"]
        else:
            self.tau_self_discharge = np.inf

        self.build_SS()
        self.x = np.array(
            [[initial_conditions["SOC"] * self.energy_capacity * 3600]],
            dtype=hercules_float_type,
        )
        self.y = None

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
        h_dict[self.component_name]["power"] = 0
        h_dict[self.component_name]["soc"] = self.SOC

        return h_dict

    def step(self, h_dict):
        """Advance the battery simulation by one time step.

        Updates the battery state including SOC, energy storage, and power output
        based on the requested power setpoint and available power.

        Args:
            h_dict (dict): Dictionary containing simulation state including:
                - battery.power_setpoint: Requested charging/discharging power [kW]
                - plant.locally_generated_power: Available power for charging [kW]

        Returns:
            dict: Updated h_dict with battery outputs stored under self.component_name:
                - power: Actual charging/discharging power [kW]
                - reject: Rejected power due to constraints [kW]
                - soc: State of charge [0-1]
        """
        # Power available for the battery to use for charging (should be >=0)
        power_setpoint = h_dict[self.component_name]["power_setpoint"]
        if np.isnan(power_setpoint):
            raise ValueError(f"{self.component_name}: power_setpoint is NaN")
        # Power signal desired by the controller
        if self.allow_grid_power_consumption:
            P_avail = np.inf
        else:
            P_avail = h_dict["plant"]["locally_generated_power"]  # [kW] available power

        P_charge, P_reject = self.control(P_avail, power_setpoint)

        # Update energy state
        # self.E += self.P_charge * self.dt
        self.step_SS(P_charge)
        self.E = self.x[0, 0]  # TODO find a better way to make self.x 1-D

        self.current_batt_state = kJ2kWh(self.E)

        self.power_kw = P_charge
        self.SOC = self.current_batt_state / self.energy_capacity

        # Update the outputs
        h_dict[self.component_name]["power"] = self.power_kw
        h_dict[self.component_name]["reject"] = P_reject
        h_dict[self.component_name]["soc"] = self.SOC

        # Return the updated dictionary
        return h_dict

    def control(self, P_avail, power_setpoint):
        """Apply battery operational constraints to requested power.

        Low-level controller that enforces energy, power, and ramp rate constraints.
        Determines the actual charging/discharging power and any rejected power.

        Args:
            P_avail (float): Available power for charging in kW.
            power_setpoint (float): Desired charging/discharging power in kW.

        Returns:
            tuple: (P_charge, P_reject) where:
                - P_charge: Actual charging/discharging power in kW (positive for charging)
                - P_reject: Rejected power due to constraints in kW (positive when
                  power cannot be absorbed, negative when required power unavailable)
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
        if (power_setpoint >= c_lo) & (power_setpoint <= c_hi):
            P_charge = power_setpoint
            P_reject = 0
        elif power_setpoint < c_lo:
            P_charge = c_lo
            P_reject = power_setpoint - P_charge
        elif power_setpoint > c_hi:
            P_charge = c_hi
            P_reject = power_setpoint - P_charge

        self.P_charge = P_charge
        self.P_reject = P_reject

        return P_charge, P_reject

    def build_SS(self):
        """Build state-space model matrices for battery dynamics.

        Constructs the state-space representation that includes self-discharge
        and efficiency losses.
        """
        self.A = np.array([[-1 / self.tau_self_discharge]], dtype=hercules_float_type)
        # B matrix is handled by the SS_input_function
        self.C = np.array([[1, 0]], dtype=hercules_float_type).T
        self.D = np.array([[0, 1]], dtype=hercules_float_type).T

    def SS_input_function(self, P_charge):
        """Apply efficiency losses to charging/discharging power.

        Converts the commanded power to actual power stored/released from
        the battery considering efficiency losses.

        Args:
            P_charge (float): Commanded charging/discharging power in kW.

        Returns:
            float: Actual power stored/released considering efficiency in kW.
        """
        # P_in is the amount of power that actually gets stored in the state E
        # P_charge is the amount of power given to the charging physics

        if P_charge >= 0:
            P_in = self.eta_charge * P_charge
        else:
            P_in = P_charge / self.eta_discharge
        return P_in

    def SS_input_function_inverse(self, P_in):
        """Calculate required commanded power for desired stored power.

        Inverse of SS_input_function to determine the commanded power needed
        to achieve a desired power storage/release rate.

        Args:
            P_in (float): Desired power to be stored/released in kW.

        Returns:
            float: Required commanded power considering efficiency in kW.
        """
        if P_in >= 0:
            P_charge = P_in / self.eta_charge
        else:
            P_charge = P_in * self.eta_discharge
        return P_charge

    def step_SS(self, u):
        """Advance the state-space model by one time step.

        Updates the battery energy state considering self-discharge and
        efficiency losses.

        Args:
            u (float): Input power command in kW.
        """
        # Advance the state-space loop
        xd = self.A * self.x + self.SS_input_function(u)
        y = self.C * self.x + self.D * u

        self.x = self.integrate(self.x, xd)
        self.y = y

    def integrate(self, x, xd):
        """Integrate state derivatives using Euler method.

        Args:
            x (np.ndarray): Current state vector.
            xd (np.ndarray): State derivative vector.

        Returns:
            np.ndarray: Updated state vector.
        """
        # TODO: Use better integration method like closed form step response solution
        return x + xd * self.dt  # Euler integration
