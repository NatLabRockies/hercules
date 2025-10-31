import numpy as np

# Electrolyzer plant module
from electrolyzer.simulation.supervisor import Supervisor
from hercules.plant_components.component_base import ComponentBase


class ElectrolyzerPlant(ComponentBase):
    def __init__(self, h_dict):
        """
        Initializes the ElectrolyzerPlant class.
        Args:
            h_dict (dict): Dict containing values for the simulation
        """
        # Store the name of this component
        self.component_name = "electrolyzer"

        # Store the type of this component
        self.component_type = "ElectrolyzerPlant"

        # Call the base class init
        super().__init__(h_dict, self.component_name)

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
        elec_config = dict(electrolyzer_dict["electrolyzer"])
        elec_config.pop("allow_grid_power_consumption", None)
        elec_config.pop("log_channels", None)
        # Initialize electrolyzer plant
        self.elec_sys = Supervisor.from_dict(elec_config)

        self.n_stacks = self.elec_sys.n_stacks

        # Right now, the plant initialization power and the initial condition power are the same
        # power_in is always in kW
        power_in = h_dict[self.component_name]["initial_power_kW"]
        self.needed_inputs = {"locally_generated_power": power_in}

        # Run Electrolyzer two steps to get outputs
        for i in range(2):
            H2_produced, H2_mfr, power_left, power_curtailed = self.elec_sys.run_control(
                power_in * 1e3
            )
        # Initialize outputs for controller step
        self.stacks_on = sum([self.elec_sys.stacks[i].stack_on for i in range(self.n_stacks)])
        self.stacks_waiting = [False] * self.n_stacks
        # # TODO: How should these be initialized? - Should we do one electrolyzer step?
        #           will that make it out of step of with the other sources?
        self.curtailed_power_kw = power_curtailed / 1e3
        self.H2_output = H2_produced
        self.H2_mfr = H2_produced / self.dt
        self.power_left_kw = power_left / 1e3
        self.power_input_kw = power_in
        self.power_used_kw = self.power_input_kw - (self.curtailed_power_kw + self.power_left_kw)

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
        # Gather inputs
        local_power = h_dict["locally_generated_power"]  # TODO check what units this is in
        if "electrolyzer_signal" in h_dict[self.component_name].keys():
            power_command_kw = h_dict[self.component_name]["electrolyzer_signal"]
        elif not self.allow_grid_power_consumption:
            # Assume electrolyzer should use as much local power as possible.
            power_command_kw = np.inf
        else:
            raise ValueError("electrolyzer_signal must be specified if allowing grid charging.")

        if self.allow_grid_power_consumption:
            power_in_kw = power_command_kw
        else:
            power_in_kw = min(local_power, power_command_kw)

        # Run electrolyzer forward one step
        ######## Electrolyzer needs input in Watts ########
        H2_produced, H2_mfr, power_left_w, power_curtailed_w = self.elec_sys.run_control(
            power_in_kw * 1e3
        )

        # Collect outputs from electrolyzer step
        self.curtailed_power_kw = power_curtailed_w / 1e3
        self.power_left_kw = power_left_w / 1e3
        self.power_input_kw = power_in_kw
        self.power_used_kw = power_in_kw - (self.curtailed_power_kw + self.power_left_kw)
        self.stacks_on = sum([self.elec_sys.stacks[i].stack_on for i in range(self.n_stacks)])
        self.stacks_waiting = [self.elec_sys.stacks[i].stack_waiting for i in range(self.n_stacks)]
        self.H2_output = H2_produced
        self.H2_mfr = H2_produced / self.elec_sys.dt

        # Update the h_dict with outputs
        h_dict[self.component_name]["H2_output"] = self.H2_output
        h_dict[self.component_name]["H2_mfr"] = self.H2_mfr
        h_dict[self.component_name]["stacks_on"] = self.stacks_on
        h_dict[self.component_name]["stacks_waiting"] = self.stacks_waiting
        h_dict[self.component_name]["power_used_kw"] = self.power_used_kw
        h_dict[self.component_name]["power_input_kw"] = self.power_input_kw

        return h_dict
