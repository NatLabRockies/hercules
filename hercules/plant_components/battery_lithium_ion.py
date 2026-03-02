"""
Battery models
Author: Zack tully - zachary.tully@nlr.gov
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


def years_to_usage_rate(years, dt):
    """Convert a number of years to a usage rate.

    Args:
        years (float): Life of the storage system in years.
        dt (float): Time step of the simulation in seconds.

    Returns:
        float: Usage rate per time step.
    """
    days = years * 365
    hours = days * 24
    seconds = hours * 3600
    usage_lifetime = seconds / dt

    return 1 / usage_lifetime


def cycles_to_usage_rate(cycles):
    """Convert cycle number to degradation rate.

    Args:
        cycles (int): Number of cycles until the unit needs to be replaced.

    Returns:
        float: Degradation rate per cycle.
    """
    return 1 / cycles


class BatteryLithiumIon(ComponentBase):
    """Detailed lithium-ion battery model with equivalent circuit modeling.

    This model represents a detailed lithium-ion battery with diffusion transients
    and losses modeled as an equivalent circuit model. Calculations in this class
    are primarily from [1].

    Battery specifications:
    - Cathode Material: LiFePO4 (all 5 cells)
    - Anode Material: Graphite (all 5 cells)

    References:
        [1] M.-K. Tran et al., "A comprehensive equivalent circuit model for lithium-ion
        batteries, incorporating the effects of state of health, state of charge, and
        temperature on model parameters," Journal of Energy Storage, vol. 43, p. 103252,
        Nov. 2021, doi: 10.1016/j.est.2021.103252.
    """

    def __init__(self, h_dict):
        """Initialize the BatteryLithiumIon class.

        This model represents a detailed lithium-ion battery with diffusion transients
        and losses modeled as an equivalent circuit model.

        Args:
            h_dict (dict): Dictionary containing simulation parameters including:
                - energy_capacity: Battery energy capacity in kWh
                - charge_rate: Maximum charge rate in kW
                - discharge_rate: Maximum discharge rate in kW
                - max_SOC: Maximum state of charge (0-1)
                - min_SOC: Minimum state of charge (0-1)
                - initial_conditions: Dictionary with initial SOC
                - allow_grid_power_consumption: Optional, defaults to False
        """

        # Store the name of this component
        self.component_name = "battery"

        # Store the type of this component
        self.component_type = "BatteryLithiumIon"

        # Call the base class init
        super().__init__(h_dict, self.component_name)

        self.V_cell_nom = 3.3  # [V]
        self.C_cell = 15.756  # [Ah] mean value from [1] Table 1

        self.energy_capacity = h_dict[self.component_name]["energy_capacity"]  # [kWh]
        self.max_charge_power = h_dict[self.component_name]["charge_rate"]  # [kW]
        self.max_discharge_power = h_dict[self.component_name]["discharge_rate"]  # [kW]

        initial_conditions = h_dict[self.component_name]["initial_conditions"]
        self.SOC = initial_conditions["SOC"]  # [fraction]
        self.SOC_max = h_dict[self.component_name]["max_SOC"]
        self.SOC_min = h_dict[self.component_name]["min_SOC"]

        # Flag for allowing grid to charge the battery
        if "allow_grid_power_consumption" in h_dict[self.component_name].keys():
            self.allow_grid_power_consumption = h_dict[self.component_name][
                "allow_grid_power_consumption"
            ]
        else:
            self.allow_grid_power_consumption = False

        self.T = 25  # [C] temperature
        self.SOH = 1  # State of Health

        self.post_init()

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

        return h_dict

    def post_init(self):
        """Calculate derived battery parameters after initialization.

        This method calculates cell configuration, capacity, voltage, current limits,
        and initializes the equivalent circuit model parameters.
        """

        # Calculate the total cells and series/parallel configuration
        self.n_cells = self.energy_capacity * 1e3 / (self.V_cell_nom * self.C_cell)
        # TODO: need a systematic way to decide parallel and series cells
        # TODO: choose a default voltage to choose the series and parallel configuration.
        # TODO: allow user to specify a specific configuration
        self.n_p = np.sqrt(self.n_cells)  # number of cells in parallel
        self.n_s = np.sqrt(self.n_cells)  # number of cells in series

        # Calculate the capacity in Ah and the max charge/discharge rate in A
        # C-rate = 1 means the cell discharges fully in one hour
        self.C = self.C_cell * self.n_p  # [Ah] capacity

        C_rate_charge = self.max_charge_power / self.energy_capacity
        C_rate_discharge = self.max_discharge_power / self.energy_capacity
        self.max_C_rate = np.max([C_rate_charge, C_rate_discharge])  # [A] [capacity/hr]

        # Nominal battery voltage and current
        self.V_bat_nom = self.V_cell_nom * self.n_s  # [V]
        self.I_bat_max = self.C_cell * self.max_C_rate * self.n_p  # [A]

        # Max charge/discharge in kW
        self.P_max = self.C * self.max_C_rate * self.V_bat_nom * 1e-3  # [kW]
        self.P_min = -self.P_max  # [kW]

        # Max and min charge level in Ah
        self.charge = self.SOC * self.C  # [Ah]
        self.charge_max = self.SOC_max * self.C
        self.charge_min = self.SOC_min * self.C

        # initial state of RC branch state space
        self.x = 0
        self.V_RC = 0
        self.error_sum = 0

        # 10th order polynomial fit of the OCV curve from [1] Fig.4
        self.OCV_polynomial = np.array(
            [
                3.59292657e03,
                -1.67001912e04,
                3.29199313e04,
                -3.58557498e04,
                2.35571965e04,
                -9.56351032e03,
                2.36147233e03,
                -3.35943038e02,
                2.49233107e01,
                2.47115515e00,
            ],
            dtype=hercules_float_type,
        )
        self.poly_order = len(self.OCV_polynomial)

        # Equivalent circuit component coefficientys from [1] Table 2
        # value = c1 + c2 * SOH + c3 * T + c4 * SOC
        self.ECM_coefficients = np.array(
            [
                [10424.73, -48.2181, -114.74, -1.40433],  # R0 [micro ohms]
                [13615.54, -68.0889, -87.527, -37.1084],  # R1 [micro ohms]
                [-11116.7, 180.4576, 237.4219, 40.14711],  # C1 [F]
            ],
            dtype=hercules_float_type,
        )

        # initial state of battery outputs for hercules
        self.power_kw = 0
        self.P_reject = 0
        self.P_charge = 0

    def OCV(self):
        """Calculate cell open circuit voltage (OCV) as a function of SOC.

        Uses a 10th order polynomial fit of the OCV curve from [1] Fig.4.

        Returns:
            float: Cell open circuit voltage in volts.
        """

        ocv = 0
        for i, c in enumerate(self.OCV_polynomial):
            ocv += c * self.SOC ** (self.poly_order - i - 1)

        return ocv

    def build_SS(self):
        """Build RC branch state space matrices for equivalent circuit model.

        Constructs state space matrices for the current SOH (state of health),
        T (temperature), and SOC (state of charge) using coefficients from [1] Table 2.

        Returns:
            tuple: A, B, C, D state space matrices for the RC branch.
        """

        R_0, R_1, C_1 = self.ECM_coefficients @ np.array(
            [1, self.SOH * 100, self.T, self.SOC * 100], dtype=hercules_float_type
        )
        R_0 *= 1e-6
        R_1 *= 1e-6

        A = -1 / (R_1 * C_1)
        B = 1
        C = 1 / C_1
        D = R_0

        return A, B, C, D

    def step_cell(self, u):
        """Update the equivalent circuit model state for one time step.

        Args:
            u (float): Cell current in amperes.
        """
        # TODO: What if dt is very slow? skip this integration and return steady state value
        # update the state of the cell model
        A, B, C, D = self.build_SS()

        xd = A * self.x + B * u
        y = C * self.x + D * u

        self.x = self.integrate(self.x, xd)
        self.V_RC = y

    def integrate(self, x, xd):
        """Integrate state derivatives using Euler method.

        Args:
            x (float): Current state value.
            xd (float): State derivative.

        Returns:
            float: Updated state value.
        """
        # TODO: Use better integration method like closed form step response solution
        return x + xd * self.dt  # Euler integration

    def V_cell(self):
        """Calculate total cell voltage.

        Returns:
            float: Cell voltage in volts (OCV + RC voltage drop).
        """
        return self.OCV() + self.V_RC

    def calc_power(self, I_bat):
        """Calculate battery power from current.

        Args:
            I_bat (float): Battery current in amperes.

        Returns:
            float: Battery power in watts.
        """
        # Total battery voltage (cells in series) times current
        return self.V_cell() * self.n_s * I_bat  # [W]

    def step(self, h_dict):
        """Advance the battery simulation by one time step.

        Updates the battery state including SOC, equivalent circuit dynamics, and power output
        based on the requested power setpoint and available power.

        Args:
            h_dict (dict): Dictionary containing simulation state including:
                - battery.power_setpoint: Requested charging/discharging power [kW]
                - plant.locally_generated_power: Available power for charging [kW]

        Returns:
            dict: Updated h_dict with battery outputs:
                - power: Actual charging/discharging power [kW]
                - reject: Rejected power due to constraints [kW]
                - soc: State of charge [0-1]
        """

        P_signal = h_dict[self.component_name]["power_setpoint"]  # [kW] requested power
        if self.allow_grid_power_consumption:
            P_avail = np.inf
        else:
            P_avail = h_dict["plant"]["locally_generated_power"]  # [kW] available power

        # Calculate charging/discharging current [A] from power
        I_charge, I_reject = self.control(P_signal, P_avail)
        i_charge = I_charge / self.n_p  # [A] Cell current

        # Update charge
        self.charge += I_charge * self.dt / 3600  # [Ah]
        self.SOC = self.charge / (self.C)

        # Update RC branch dynamics
        self.step_cell(i_charge)

        # Calculate actual power
        self.power_kw = self.calc_power(I_charge) * 1e-3
        self.P_reject = P_signal - self.power_kw

        # Update power signal error integral
        if (P_signal < self.max_charge_power) & (P_signal > self.max_discharge_power):
            self.error_sum += self.P_reject * self.dt

        # Update the outputs
        h_dict[self.component_name]["power"] = self.power_kw
        h_dict[self.component_name]["reject"] = self.P_reject
        h_dict[self.component_name]["soc"] = self.SOC

        # Return the updated dictionary
        return h_dict

    def control(self, P_signal, P_avail):
        """Calculate charging/discharging current from requested power.

        Uses an iterative approach to account for errors between nominal and actual
        battery voltage. Includes integral control to correct for persistent voltage errors.

        Args:
            P_signal (float): Requested charging/discharging power in kW.
            P_avail (float): Power available for charging/discharging in kW.

        Returns:
            tuple: (I_charge, I_reject) where:
                - I_charge: Charging/discharging current in amperes that the battery can provide
                - I_reject: Current equivalent of power that cannot be provided in amperes
        """

        # Current according to nominal voltage
        I_signal = P_signal * 1e3 / self.V_bat_nom

        # Iteratively adjust setpoint to account for inherent error in V_nom
        error = P_signal - self.calc_power(I_signal) * 1e-3
        count = 0  # safety count
        tol = self.V_bat_nom * self.I_bat_max * 1e-9
        while np.abs(error) > tol:
            count += 1
            error = P_signal - self.calc_power(I_signal) * 1e-3
            I_signal += error * 1e3 / self.V_bat_nom

            if count > 100:
                # assert False, "Too many interations, breaking the while loop."
                break

        # Error integral acts like an offset correcting for persistent errors between nominal and
        # actual battery voltage.
        I_signal += self.error_sum * 1e3 / self.V_bat_nom * 0.01
        # Is this calc just as accurate as iterative?
        I_avail = P_avail * 1e3 / (self.V_cell() * self.n_s)

        # Check charging, discharging, and amperage constraints.
        I_charge, I_reject = self.constraints(I_signal, I_avail)

        return I_charge, I_reject

    def constraints(self, I_signal, I_avail):
        """Apply battery operational constraints to the requested current.

        Checks whether the requested charging/discharging action will violate battery
        charge limits, power limits, or available power. Returns the constrained current
        and any rejected current.

        Args:
            I_signal (float): Requested charging/discharging current in amperes.
            I_avail (float): Current available for charging/discharging in amperes.

        Returns:
            tuple: (I_charge, I_reject) where:
                - I_charge: Constrained charging/discharging current in amperes
                - I_reject: Rejected current due to constraints in amperes
        """

        # Charge (energy) constraint, upper. Charging current that would fill the battery up
        # completely in one time step
        c_hi1 = (self.charge_max - self.charge) / (self.dt / 3600)
        # Charge rate (power) constraint, upper.
        c_hi2 = self.I_bat_max
        # Available power
        c_hi3 = I_avail

        # Take the most restrictive upper constraint
        c_hi = np.min([c_hi1, c_hi2, c_hi3])

        # Charge (energy) constraint, lower.
        c_lo1 = (self.charge_min - self.charge) / (self.dt / 3600)
        # Discharge rate (power) constraint, lower.
        c_lo2 = -self.I_bat_max

        # Take the most restrictive lower constraint
        c_lo = np.max([c_lo1, c_lo2])

        if (I_signal >= c_lo) & (I_signal <= c_hi):
            # It is possible to fulfill the requested signal
            I_charge = I_signal
            I_reject = 0
        elif I_signal < c_lo:
            # The battery is constrained to charge/discharge higher than the requested signal
            I_charge = c_lo
            I_reject = I_signal - I_charge
        elif I_signal > c_hi:
            # The battery is constrained to charge/discharge lower than the requested signal
            I_charge = c_hi
            I_reject = I_signal - I_charge

        return I_charge, I_reject
