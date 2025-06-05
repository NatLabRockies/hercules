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

    return 1/usage_lifetime

def cycles_to_usage_rate(cycles):
    """Convert cycle number to degradation rate
    inputs: 
        cycles: number of cycles until the unit needs to be replaced
        dt: time step of the simulation, in seconds
    """
    return 1/cycles


class Battery:
    def __init__(self, input_dict, dt):
        if input_dict["py_sim_type"] == "SimpleBattery":
            self.battery = SimpleBattery(input_dict, dt)
        elif input_dict["py_sim_type"] == "LIB":
            self.battery = LIB(input_dict, dt)
        self.needed_inputs = self.battery.needed_inputs

    def step(self, inputs):
        return self.battery.step(inputs)

    def return_outputs(self):
        return self.battery.return_outputs()


class LIB:
    """
    Calculations in this class are primarily from [1]

    Cathode Material LiFePO4 (all 5 cells)
    Anode Material Graphite (all 5 cells)
    """

    def __init__(self, input_dict: dict, dt: float):
        """
        Initialize with parameters from input dict from hercules setup

        Inputs:
        - input_dict: dictionary of specific battery parameters. Must have:
            energy_capacity: total capcity of the battery in MWh
            charge_rate: charge rate of the battery in MW
            discharge_rate: discharge rate of the battery in MW
            max_SOC: upper boundary on battery SOC between 0 and 1
            min_SOC: lower boundary on battery SOC between 0 and 1
            allow_grid_power_consumption: boolean flag for allowing grid to charge the battery
            initial_conditions: {SOC: iniital SOC between 0 and 1}
        """

        self.dt = dt
        self.V_cell_nom = 3.3  # [V]
        self.C_cell = 15.756  # [Ah] mean value from [1] Table 1

        self.energy_capacity = input_dict["energy_capacity"] * 1e3  # [kWh]
        self.max_charge_power = input_dict["charge_rate"] * 1e3  # [kW]
        self.max_discharge_power = input_dict["discharge_rate"] * 1e3  # [kW]

        inititial_conditions = input_dict["initial_conditions"]
        self.SOC = inititial_conditions["SOC"]  # [fraction]
        self.SOC_max = input_dict["max_SOC"]
        self.SOC_min = input_dict["min_SOC"]

        # Flag for allowing grid to charge the battery
        if "allow_grid_power_consumption" in input_dict.keys():
            self.allow_grid_power_consumption = input_dict["allow_grid_power_consumption"]
        else:
            self.allow_grid_power_consumption = False

        self.T = 25  # [C] temperature
        self.SOH = 1  # State of Health

        self.needed_inputs = {"battery_signal": 0.0}

        self.post_init()

    def post_init(self):
        """
        Calculations for other battery variables not specified in the initialization
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
            ]
        )
        self.poly_order = len(self.OCV_polynomial)

        # Equivalent circuit component coefficientys from [1] Table 2
        # value = c1 + c2 * SOH + c3 * T + c4 * SOC
        self.ECM_coefficients = np.array(
            [
                [10424.73, -48.2181, -114.74, -1.40433],  # R0 [micro ohms]
                [13615.54, -68.0889, -87.527, -37.1084],  # R1 [micro ohms]
                [-11116.7, 180.4576, 237.4219, 40.14711],  # C1 [F]
            ]
        )

        # initial state of battery outputs for hercules emulator
        self.power_kw = 0
        self.P_reject = 0
        self.P_charge = 0

    def OCV(self):
        """
        Calculate cell open circuit voltage (OCV) as a function of SOC

        Returns:
        - OCV: Cell open circuit voltage [V]
        """

        ocv = 0
        for i, c in enumerate(self.OCV_polynomial):
            ocv += c * self.SOC ** (self.poly_order - i - 1)

        return ocv

    def build_SS(self):
        """
        Return RC branch state space matrices for the current SOH (state of health),
        T (temperature), and SOC (state of charge).

        Returns:
            - A, B, C, D: RC branch state space matrices
        """

        R_0, R_1, C_1 = self.ECM_coefficients @ np.array(
            [1, self.SOH * 100, self.T, self.SOC * 100]
        )
        R_0 *= 1e-6
        R_1 *= 1e-6

        A = -1 / (R_1 * C_1)
        B = 1
        C = 1 / C_1
        D = R_0

        return A, B, C, D

    def step_cell(self, u):
        """
        Inputs:
        - u: cell current (i [A])
        """
        # TODO: What if dt is very slow? skip this integration and return steady state value
        # update the state of the cell model
        A, B, C, D = self.build_SS()

        xd = A * self.x + B * u
        y = C * self.x + D * u

        self.x = self.integrate(self.x, xd)
        self.V_RC = y

    def integrate(self, x, xd):
        # better integration -> use the closed form step response solution?
        return x + xd * self.dt  # Euler integration

    def V_cell(self):
        """Return cell voltage"""
        return self.OCV() + self.V_RC

    def calc_power(self, I_bat):
        """Return battery power in kW"""
        # NOTE: this might be in watts, ask Zack!
        return self.V_cell() * self.n_s * I_bat  # [kW]

    def step(self, inputs: dict):
        """
        Perform all of the internal update calculations as the simulation advances a time step.

        Inputs:
        - inputs: dictionary of inputs for the current time step which must have:
            - py_sims:{inputs:{battery_signal: ___ }} [kW] charging/discharging power desired
            - py_sims:{inputs:{locally_generated_power: ___ }} [kW] power available for
                 charging/discharging that was generated onsite (not from grid)

        Outputs:
        - outptuts: see return_outputs() method
        """

        P_signal = inputs["py_sims"]["inputs"]["battery_signal"]  # [kW] requested power
        if self.allow_grid_power_consumption:
            P_avail = np.inf
        else:
            P_avail = inputs["py_sims"]["inputs"]["locally_generated_power"]  # [kW] available power

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

        return self.return_outputs()

    def return_outputs(self):
        return {"power": self.power_kw, "reject": self.P_reject, "soc": self.SOC,
                "power_kW": -self.power_kw}

    def control(self, P_signal, P_avail):
        """
        Calculate the charging/discharging current from the requested charging/discharging power.
        There is an iterative update to the charging current to account for errors between the
        nominal and actual battery voltage.

        Inputs:
        - P_signal: [kW] requested charging/discharging power
        - P_avail: [kW] power available for charging/discharging

        Returns:
        - I_charge: [A] charging/discharging current for P_signal if the battery is able
        - I_reject: [A] current needed to meet P_signal if the batter is not able
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
        """
        Check whether the requested charging/discharging action will violate the battery charge or
        amperage limits. If it does not, charge the battery as requested. If it does, charge the
        battery according to the most restrictive constraint.

        Inputs:
        - I_avail: [A] current available for charging/discharging
        - I_signal: [A] charging/discharging current requested of battery.

        Returns:
        - I_charge: [A] the closest charging/discharging current that satisfies all constraints
        - I_reject: [A] the additional current needed to charge at I_avail
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


class SimpleBattery:
    # TODO: keep consistent units. Everything in kW or everything in MW but not both
    def __init__(self, input_dict, dt):
        self.dt = dt

        # size = input_dict["size"]
        self.energy_capacity = input_dict["energy_capacity"] * 1e3  # [kWh]
        inititial_conditions = input_dict["initial_conditions"]
        self.SOC = inititial_conditions["SOC"]  # [fraction]

        self.SOC_max = input_dict["max_SOC"]
        self.SOC_min = input_dict["min_SOC"]

        # Charge (Energy) limits [kJ]
        self.E_min = kWh2kJ(self.SOC_min * self.energy_capacity)
        self.E_max = kWh2kJ(self.SOC_max * self.energy_capacity)

        charge_rate = input_dict["charge_rate"] * 1e3  # [kW]
        discharge_rate = input_dict["discharge_rate"] * 1e3  # [kW]

        # Charge/discharge (Power) limits [kW]
        self.P_min = -discharge_rate
        self.P_max = charge_rate

        # Ramp up/down limits [kW/s]
        self.R_min = -np.inf
        self.R_max = np.inf

        # Flag for allowing grid to charge the battery
        if "allow_grid_power_consumption" in input_dict.keys():
            self.allow_grid_power_consumption = input_dict["allow_grid_power_consumption"]
        else:
            self.allow_grid_power_consumption = False

        # Efficiency and self-discharge parameters
        if "roundtrip_efficiency" in input_dict.keys():
            self.eta_charge = np.sqrt(input_dict["roundtrip_efficiency"])
            self.eta_discharge = np.sqrt(input_dict["roundtrip_efficiency"])
        else:
            self.eta_charge = 1
            self.eta_discharge = 1

        if "self_discharge_time_constant" in input_dict.keys():
            self.tau_self_discharge = input_dict["self_discharge_time_constant"]
        else:
            self.tau_self_discharge = np.inf

        if "track_usage" in input_dict.keys():
            if input_dict["track_usage"]:
                self.track_usage = True
                # Set usage tracking parameters
                if "usage_calc_interval" in input_dict.keys():
                    self.usage_calc_interval = input_dict["usage_calc_interval"] / self.dt
                else:
                    self.usage_calc_interval = 100 / self.dt # timesteps
                
                if "usage_lifetime" in input_dict.keys():
                    usage_lifetime = input_dict["usage_lifetime"]
                    self.usage_time_rate = years_to_usage_rate(usage_lifetime, self.dt)
                else:
                    self.usage_time_rate = 0 
                if "usage_cycles" in input_dict.keys():
                    usage_cycles = input_dict["usage_cycles"]
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
        self.x = np.array([[inititial_conditions["SOC"] * self.energy_capacity * 3600]])
        self.y = None

        # self.total_battery_capacity = 3600 * self.energy_capacity / self.dt
        self.current_batt_state = self.SOC * self.energy_capacity
        self.E = kWh2kJ(self.current_batt_state)

        self.power_kw = 0
        self.P_reject = 0
        self.P_charge = 0

        self.needed_inputs = {"battery_signal": 0.0}

    def step(self, inputs):

        self.step_counter += 1

        # power available for the battery to use for charging (should be >=0)
        P_signal = inputs["py_sims"]["inputs"]["battery_signal"]
        # power signal desired by the controller
        if self.allow_grid_power_consumption:
            P_avail = np.inf
        else:
            P_avail = inputs["py_sims"]["inputs"]["locally_generated_power"]  # [kW] available power

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

        return self.return_outputs()

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

    def return_outputs(self):
        return {"power": self.power_kw, "reject": self.P_reject, "soc": self.SOC,
                "usage_in_time": self.time_usage_perc, "usage_in_cycles": self.cycle_usage_perc,
                "total_cycles":self.total_cycle_usage, "power_kW": -self.power_kw}
