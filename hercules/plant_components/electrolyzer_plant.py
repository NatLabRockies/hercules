import electrolyzer.tools.validation as val
import numpy as np

# Electrolyzer plant module
from electrolyzer.simulation.supervisor import Supervisor
from hercules.plant_components.component_base import ComponentBase


class ElectrolyzerPlant(ComponentBase):
    """Electrolyzer plant component for hydrogen production.

    This component models an electrolyzer system that converts electrical power
    into hydrogen using the electrolyzer module simulation.
    The Electrolyzer plant uses the electrolyzer model from https://github.com/NREL/electrolyzer

    Within this class consumed power is positive; ``HybridPlant`` negates
    ``consumer_sign_outputs`` (and ``power_setpoint``) so that consumption is negative
    outside the component.
    """

    component_category = "load"
    consumer_sign_outputs = ("power", "power_allocated")

    def __init__(self, h_dict, component_name):
        """Initialize the ElectrolyzerPlant class.

        Args:
            h_dict (dict): Dictionary containing simulation parameters including:
            - general: General simulation parameters.
            - electrolyzer: Electrolyzer plant specific parameters including:
                - initialize: boolean. Whether to initialize the electrolyzer.
                - initial_power_kW: Initial power input to the electrolyzer [kW].
                - supervisor:
                    - system_rating_MW: Total system rating in MW.
                    - n_stacks: Number of electrolyzer stacks in the plant.
                - stack: Electrolyzer stack parameters including:
                    - cell_type: Type of electrolyzer cell (e.g., PEM, Alkaline).
                    - max_current: Maximum current of the stack [A].
                    - temperature: Stack operating temperature [degC].
                    - n_cells: Number of cells per stack.
                    - min_power: Minimum power for electrolyzer operation [kW].
                    - stack_rating_kW: Stack rated power [kW].
                    - include_degradation_penalty: *Optional* boolean, Whether to include
                        degradation penalty.
                    - hydrogen_degradation_penalty: *Optional* boolean, whether degradation is
                        applied to hydrogen (True) or power (False)
                cell_params: Electrolyzer cell parameters including:
                    - cell_area: Area of individual cells in the stack [cm^2].
                    - turndown_ratio: Minimum turndown ratio for stack operation [between 0 and 1].
                    - max current_density: Maximum current density [A/cm^2].
                    - p_anode: Anode operating pressure [bar].
                    - p_cathode: Cathode operating pressure [bar].
                    - alpha_a: anode charge transfer coefficient.
                    - alpha_c: cathode charge transfer coefficient.
                    - i_0_a: anode exchange current density [A/cm^2].
                    - i_0_c: cathode exchange current density [A/cm^2].
                    - e_m: membrane thickness [cm].
                    - R_ohmic_elec: electrolyte resistance [A*cm^2].
                    - f_1: Faradaic coefficient [mA^2/cm^4].
                    - f_2: Faradaic coefficient [mA^2/cm^4].
                degradation: Electrolyzer degradation parameters including:
                    - eol_eff_percent_loss: End of life efficiency percent loss [%].
                    - PEM_params or ALK_params: Degradation parameters specific to PEM or Alkaline
                         cells:
                        - rate_steady: Rate of voltage degradation under steady operation alone
                        - rate_fatigue: Rate of voltage degradation under variable operation alone
                        - rate_onoff: Rate of voltage degradation per on/off cycle
                - controller: Electrolyzer control parameters including:
                    - control_type: Controller type for electrolyzer plant operation.
                - costs: *Optional* Cost parameters for the electrolyzer plant including:
                    - plant_params:
                        - plant_life: integer, Plant life in years
                        - pem_location: Location of the PEM electrolyzer. Options are
                            [onshore, offshore, in-turbine]
                        - grid_connected: boolean, Whether the plant is connected to the grid or not
                    - feedstock: Parameters related to the feedstock including:
                        - water_feedstock_cost: Cost of water per kg of water
                        - water_per_kgH2: Amount of water required per kg of hydrogen produced
                    - opex: Operational expenditure parameters including:
                        - var_OM: Variable operation and maintenance cost per kW
                        - fixed_OM: Fixed operation and maintenance cost per kW-year
                    - stack_replacement: Parameters related to stack replacement costs including:
                        - d_eol: End of life cell voltage value [V]
                        - stack_replacement_percent: Stack replacement cost as a percentage of CapEx
                            [0,1]
                    - capex: Capital expenditure parameters including:
                        - capex_learning_rate: Capital expenditure learning rate.
                        - ref_cost_bop: Reference cost of balance of plant per kW.
                        - ref_size_bop: Reference size of balance of plant in kW.
                        - ref_cost_pem: Reference cost of PEM electrolyzer stack per kW.
                        - ref_size_pem: Reference size of PEM electrolyzer stack in kW.
                    - finances: Financial parameters including:
                        - discount_rate: Discount rate for financial calculations [%].
                        - install_factor: Installation factor for capital expenditure [0,1].
            component_name (str): Unique name for this instance (the YAML top-level key).
        """

        # Call the base class init (sets self.component_name and self.component_type)
        super().__init__(h_dict, component_name)

        electrolyzer_dict = {}
        # Check if general key exists in electrolyzer section, otherwise use top-level general
        if "general" in h_dict[self.component_name]:
            electrolyzer_dict["general"] = h_dict[self.component_name]["general"]
        elif "general" in h_dict:
            electrolyzer_dict["general"] = h_dict["general"]
        else:
            electrolyzer_dict["general"] = {"verbose": False}

        electrolyzer_dict["electrolyzer"] = h_dict[self.component_name]
        electrolyzer_dict["electrolyzer"]["dt"] = self.dt

        if "allow_grid_power_consumption" in h_dict[self.component_name].keys():
            self.allow_grid_power_consumption = h_dict[self.component_name][
                "allow_grid_power_consumption"
            ]
        else:
            self.allow_grid_power_consumption = False

        # Remove keys not expected by Supervisor
        elec_config = {}
        elec_config["electrolyzer"] = dict(electrolyzer_dict["electrolyzer"]["electrolyzer"])

        elec_config["electrolyzer"]["dt"] = self.dt

        # Validate electrolyzer config
        elec_config = val.validate_with_defaults(elec_config, val.fschema_model)

        # Initialize electrolyzer plant
        self.elec_sys = Supervisor.from_dict(elec_config["electrolyzer"])

        self.n_stacks = self.elec_sys.n_stacks

        # Right now, the plant initialization power and the initial condition power are the same
        power_allocated = elec_config["electrolyzer"]["initial_power_kW"]
        self.needed_inputs = {"locally_generated_power": power_allocated}

        self.logger.info(
            "Initializing ElectrolyzerPlant with power input of %.2f kW", power_allocated
        )

        # Run Electrolyzer two steps to get outputs
        # Note that power is converted to Watts for electrolyzer input
        for i in range(6):
            H2_produced, H2_MFR, power_left_W, power_curtailed_W = self.elec_sys.run_control(
                power_allocated * 1e3
            )
        # Initialize outputs for controller step
        self.stack_count_on = sum([self.elec_sys.stacks[i].stack_on for i in range(self.n_stacks)])
        self.stacks_waiting = [False] * self.n_stacks
        # # TODO: How should these be initialized? - Should we do one electrolyzer step?
        #           will that make it out of step of with the other sources?
        self.power_curtailed = power_curtailed_W / 1e3
        self.H2_output = H2_produced
        self.H2_MFR = H2_produced / self.dt
        self.power_left = power_left_W / 1e3
        self.power_allocated = power_allocated
        self.power_consumed = self.power_allocated - (self.power_curtailed + self.power_left)

        if self.verbose:
            self.logger.info(
                "ElectrolyzerPlant initialized: H2_MFR=%.4f kg/s, power_consumed=%.2f kW, "
                "stack_count_on=%d",
                self.H2_MFR,
                self.power_consumed,
                self.stack_count_on,
            )
        # Update the user
        self.logger.info(f"Initialized ElectrolyzerPlant with {self.n_stacks} stacks")

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Add any initial conditions or meta data to the h_dict.

        Meta data is data not explicitly in the input yaml but still useful for other
        modules.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Dictionary containing simulation parameters with initial conditions and meta data.
        """
        self._update_outputs(h_dict)

        return h_dict

    def _update_outputs(self, h_dict):
        """Write outputs to the h_dict (consumption positive).

        Args:
            h_dict (dict): Dictionary containing simulation state.
        """
        h_dict[self.component_name]["H2_output"] = self.H2_output
        h_dict[self.component_name]["H2_MFR"] = self.H2_MFR
        h_dict[self.component_name]["stack_count_on"] = self.stack_count_on
        h_dict[self.component_name]["stacks_waiting"] = self.stacks_waiting
        h_dict[self.component_name]["power"] = self.power_consumed
        h_dict[self.component_name]["power_allocated"] = self.power_allocated

    def step(self, h_dict):
        """Advance the electrolyzer simulation by one time step.

        Updates the electrolyzer state including hydrogen production, power consumption,
        and stack status based on available power and control signals.

        Args:
            h_dict (dict): Dictionary containing simulation state including:
                - plant.locally_generated_power: Available power for electrolyzer [kW]
                - <component_name>.power_setpoint: Optional power to consume [kW]
                  (positive inside the component)

        Returns:
            dict: Updated h_dict with electrolyzer outputs (consumption positive):
                - H2_output: Hydrogen produced in this time step [kg]
                - H2_MFR: Hydrogen mass flow rate [kg/s]
                - stack_count_on: Number of active stacks
                - stacks_waiting: List of stack waiting states
                - power: Power consumed by electrolyzer [kW]
                - power_allocated: Power allocated to electrolyzer [kW]
        """
        if "electrolyzer_signal" in h_dict[self.component_name]:
            raise ValueError(
                f"{self.component_name}: electrolyzer_signal was renamed to power_setpoint "
                "(negative for consumption) in Hercules v3, see docs/nomenclature.md"
            )

        # Gather inputs
        locally_generated_power = h_dict["plant"]["locally_generated_power"]  # kW
        if "power_setpoint" in h_dict[self.component_name]:
            power_setpoint = h_dict[self.component_name]["power_setpoint"]
        elif not self.allow_grid_power_consumption:
            # Assume electrolyzer should use as much local power as possible.
            power_setpoint = np.inf
        else:
            raise ValueError("power_setpoint must be specified if allowing grid charging.")

        if self.allow_grid_power_consumption:
            power_allocated = power_setpoint
        else:
            power_allocated = min(locally_generated_power, power_setpoint)

        if self.verbose:
            self.logger.info(
                "ElectrolyzerPlant step at time %.2f s with locally_generated_power=%.2f kW, "
                "power_setpoint=%.2f kW, power_allocated=%.2f kW",
                h_dict["time"],
                locally_generated_power,
                power_setpoint,
                power_allocated,
            )

        # Run electrolyzer forward one step
        ######## Electrolyzer needs input in Watts ########
        H2_produced, H2_MFR, power_left_W, power_curtailed_W = self.elec_sys.run_control(
            power_allocated * 1e3
        )

        # Collect outputs from electrolyzer step
        self.power_curtailed = power_curtailed_W / 1e3
        self.power_left = power_left_W / 1e3
        self.power_allocated = power_allocated
        self.power_consumed = power_allocated - (self.power_curtailed + self.power_left)
        self.stack_count_on = sum([self.elec_sys.stacks[i].stack_on for i in range(self.n_stacks)])
        self.stacks_waiting = [self.elec_sys.stacks[i].stack_waiting for i in range(self.n_stacks)]
        self.H2_output = H2_produced
        self.H2_MFR = H2_produced / self.elec_sys.dt

        if self.verbose:
            self.logger.info(
                "ElectrolyzerPlant step: H2_MFR=%.4f kg/s, power_consumed=%.2f kW, "
                "stack_count_on=%d",
                self.H2_MFR,
                self.power_consumed,
                self.stack_count_on,
            )

        self._update_outputs(h_dict)

        return h_dict
