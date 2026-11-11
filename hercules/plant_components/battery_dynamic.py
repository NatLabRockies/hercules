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


class BatteryDynamic(ComponentBase):
    """Simple battery energy storage model.

    This model represents a basic battery with energy storage and power constraints.
    It tracks state of charge and applies roundtrip efficiency losses on charging.

    Note:
        All power units are in kW and energy units are in kWh. Within this class
        charging is positive; ``HybridPlant`` negates ``consumer_sign_outputs`` so that
        discharging is positive outside the component.
    """

    component_category = "storage"
    consumer_sign_outputs = ("power", "DC_power", "power_reject")

    def __init__(self, h_dict, component_name):
        """Initialize the BatteryDynamic class.

        This model represents a simple battery with energy storage and power constraints.
        It tracks state of charge and applies efficiency losses.

        Args:
            h_dict (dict): Dictionary containing simulation parameters including:
                - energy_capacity: Deliverable energy capacity in kWh (energy
                    discharged at the terminals from SOC 1 to 0)
                - power_charge_max: Maximum charge power in kW
                - power_discharge_max: Maximum discharge power in kW
                - SOC_max: Optional maximum state of charge (0-1, default 1.0).
                    Values below 1.0 indicate a deviation from nameplate
                    performance (e.g., degradation) and reduce deliverable energy.
                - SOC_min: Optional minimum state of charge (0-1, default 0.0).
                    Values above 0.0 indicate a deviation from nameplate
                    performance (e.g., degradation) and reduce deliverable energy.
                - initial_conditions: Dictionary with initial SOC
                - allow_grid_power_consumption: Optional, defaults to False
                - efficiency_roundtrip: Optional roundtrip efficiency (0-1), applied
                    on charging
                - time_constant_self_discharge: Optional self-discharge time constant
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
                f"{self.component_name}: {removed} are no longer supported by BatteryDynamic. "
                "Usage tracking was removed; compute cycle metrics from the outputs instead."
            )

        self.energy_capacity = h_dict[self.component_name]["energy_capacity"]  # [kWh]
        initial_conditions = h_dict[self.component_name]["initial_conditions"]
        self.SOC = initial_conditions["SOC"]  # [fraction]

        # SOC limits default to 0 and 1 (full nameplate capacity). Values other
        # than 0/1 represent a deviation from nameplate performance such as
        # degradation, and will reduce the deliverable energy below the rated
        # energy_capacity / power_discharge_max duration.
        self.SOC_max = h_dict[self.component_name].get("SOC_max", 1.0)
        self.SOC_min = h_dict[self.component_name].get("SOC_min", 0.0)

        power_charge_max = h_dict[self.component_name]["power_charge_max"]  # [kW]
        power_discharge_max = h_dict[self.component_name]["power_discharge_max"]  # [kW]

        # Charge-positive power limits [kW]
        self.power_min = -power_discharge_max
        self.power_max = power_charge_max

        # Ramp up/down limits [kW/s]
        self.ramp_rate_min = -np.inf
        self.ramp_rate_max = np.inf

        # Flag for allowing grid to charge the battery
        if "allow_grid_power_consumption" in h_dict[self.component_name].keys():
            self.allow_grid_power_consumption = h_dict[self.component_name][
                "allow_grid_power_consumption"
            ]
        else:
            self.allow_grid_power_consumption = False

        # Roundtrip efficiency is applied entirely on charging, so stored energy equals
        # deliverable energy and discharge duration = energy_capacity / power_discharge_max.
        self.efficiency_charge = h_dict[self.component_name].get("efficiency_roundtrip", 1.0)
        self.efficiency_discharge = 1.0

        # Energy limits [kJ]
        self.energy_min_kJ = kWh2kJ(self.SOC_min * self.energy_capacity)
        self.energy_max_kJ = kWh2kJ(self.SOC_max * self.energy_capacity)

        self.time_constant_self_discharge = h_dict[self.component_name].get(
            "time_constant_self_discharge", np.inf
        )

        self.build_SS()
        # float64 so small increments are not lost against a large stored energy (AI)
        self.x = np.array(
            [[initial_conditions["SOC"] * self.energy_capacity * 3600]],
            dtype=np.float64,
        )
        self.y = None

        self.energy = self.SOC * self.energy_capacity  # [kWh]
        self.energy_kJ = kWh2kJ(self.energy)

        self.power_charge = 0
        self.DC_power_charge = 0
        self.power_reject_charge = 0

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Add any initial conditions or meta data to the h_dict.

        Meta data is data not explicitly in the input yaml but still useful for other
        modules.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Dictionary containing simulation parameters with initial conditions and meta data.
        """
        h_dict[self.component_name]["power"] = 0
        h_dict[self.component_name]["DC_power"] = 0
        h_dict[self.component_name]["power_reject"] = 0
        h_dict[self.component_name]["SOC"] = self.SOC

        return h_dict

    def step(self, h_dict):
        """Advance the battery simulation by one time step.

        Updates the battery state including SOC, energy storage, and power output
        based on the requested power setpoint and available power.

        Args:
            h_dict (dict): Dictionary containing simulation state including:
                - <component_name>.power_setpoint: Requested power in kW (positive is
                  charging)
                - plant.locally_generated_power: Available power for charging [kW]

        Returns:
            dict: Updated h_dict with battery outputs stored under self.component_name
                (positive is charging):
                - power: Actual AC power [kW]
                - DC_power: Power into storage after efficiency losses [kW]
                - power_reject: power_setpoint minus power [kW]
                - SOC: State of charge [0-1]
        """
        power_setpoint = h_dict[self.component_name]["power_setpoint"]
        if np.isnan(power_setpoint):
            raise ValueError(f"{self.component_name}: power_setpoint is NaN")

        if self.allow_grid_power_consumption:
            power_charge_available = np.inf
        else:
            power_charge_available = h_dict["plant"]["locally_generated_power"]  # [kW]

        power_charge, power_reject_charge = self.control(power_charge_available, power_setpoint)

        # Update energy state
        self.step_SS(power_charge)
        self.energy_kJ = self.x[0, 0]  # TODO find a better way to make self.x 1-D

        self.energy = kJ2kWh(self.energy_kJ)

        self.DC_power_charge = self.SS_input_function(power_charge)
        self.SOC = self.energy / self.energy_capacity

        # Update the outputs
        h_dict[self.component_name]["power"] = power_charge
        h_dict[self.component_name]["DC_power"] = self.DC_power_charge
        h_dict[self.component_name]["power_reject"] = power_reject_charge
        h_dict[self.component_name]["SOC"] = self.SOC

        # Return the updated dictionary
        return h_dict

    def control(self, power_charge_available, power_setpoint):
        """Apply battery operational constraints to requested power.

        Low-level controller that enforces energy, power, and ramp rate constraints.
        Determines the actual charging/discharging power and any rejected power.

        Args:
            power_charge_available (float): Available power for charging in kW.
            power_setpoint (float): Desired power in kW (positive is charging).

        Returns:
            tuple: (power_charge, power_reject_charge) where:
                - power_charge: Actual power in kW (positive for charging)
                - power_reject_charge: Rejected power due to constraints in kW (positive when
                  power cannot be absorbed, negative when required power unavailable)
        """

        # TODO remove ramp rate constraints because they are never used?

        # Upper constraints [kW]
        c_hi1 = self.SS_input_function_inverse((self.energy_max_kJ - self.x[0, 0]) / self.dt)
        c_hi2 = self.power_max  # power
        c_hi3 = self.ramp_rate_max * self.dt + self.power_charge  # ramp rate
        c_hi4 = power_charge_available

        # Lower constraints [kW]
        c_lo1 = self.SS_input_function_inverse((self.energy_min_kJ - self.x[0, 0]) / self.dt)
        c_lo2 = self.power_min  # power
        c_lo3 = self.ramp_rate_min * self.dt + self.power_charge  # ramp rate

        # High constraint is the most restrictive of the high constraints
        c_hi = np.min([c_hi1, c_hi2, c_hi3, c_hi4])
        c_hi = np.max([c_hi, 0])

        # Low constraint is the most restrictive of the low constraints
        c_lo = np.max([c_lo1, c_lo2, c_lo3])
        c_lo = np.min([c_lo, 0])

        # TODO: force low constraint to be no higher than lowest high constraint
        if (power_setpoint >= c_lo) & (power_setpoint <= c_hi):
            power_charge = power_setpoint
            power_reject_charge = 0
        elif power_setpoint < c_lo:
            power_charge = c_lo
            power_reject_charge = power_setpoint - power_charge
        elif power_setpoint > c_hi:
            power_charge = c_hi
            power_reject_charge = power_setpoint - power_charge

        self.power_charge = power_charge
        self.power_reject_charge = power_reject_charge

        return power_charge, power_reject_charge

    def build_SS(self):
        """Build state-space model matrices for battery dynamics.

        Constructs the state-space representation that includes self-discharge
        and efficiency losses.
        """
        self.A = np.array([[-1 / self.time_constant_self_discharge]], dtype=hercules_float_type)
        # B matrix is handled by the SS_input_function
        self.C = np.array([[1, 0]], dtype=hercules_float_type).T
        self.D = np.array([[0, 1]], dtype=hercules_float_type).T

    def SS_input_function(self, power_charge):
        """Apply efficiency losses to charging/discharging power.

        Converts the AC power to the DC power stored/released from the battery
        considering efficiency losses.

        Args:
            power_charge (float): AC charging/discharging power in kW.

        Returns:
            float: DC power stored/released considering efficiency in kW.
        """
        if power_charge >= 0:
            DC_power_charge = self.efficiency_charge * power_charge
        else:
            DC_power_charge = power_charge / self.efficiency_discharge
        return DC_power_charge

    def SS_input_function_inverse(self, DC_power_charge):
        """Calculate required AC power for desired stored power.

        Inverse of SS_input_function to determine the AC power needed
        to achieve a desired power storage/release rate.

        Args:
            DC_power_charge (float): Desired DC power to be stored/released in kW.

        Returns:
            float: Required AC power considering efficiency in kW.
        """
        if DC_power_charge >= 0:
            power_charge = DC_power_charge / self.efficiency_charge
        else:
            power_charge = DC_power_charge * self.efficiency_discharge
        return power_charge

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
