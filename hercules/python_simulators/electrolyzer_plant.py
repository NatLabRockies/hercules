import numpy as np

# Electrolyzer plant module
from electrolyzer.simulation.supervisor import Supervisor


class ElectrolyzerPlant:
    def __init__(self, input_dict, dt):
        electrolyzer_dict = {}
        electrolyzer_dict["general"] = input_dict["general"]
        electrolyzer_dict["electrolyzer"] = input_dict["electrolyzer"]
        electrolyzer_dict["electrolyzer"]["dt"] = dt

        if "allow_grid_power_consumption" in input_dict.keys():
            self.allow_grid_power_consumption = input_dict["allow_grid_power_consumption"]
        else:
            self.allow_grid_power_consumption = False

        # Initialize electrolyzer plant
        self.elec_sys = Supervisor.from_dict(electrolyzer_dict["electrolyzer"])

        self.n_stacks = self.elec_sys.n_stacks

        # Right now, the plant initialization power and the initial condition power are the same
        # power_in is always in MW
        power_in = input_dict["electrolyzer"]["initial_power_kW"]
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
        self.H2_mfr = H2_produced / dt
        self.power_left_kw = power_left / 1e3
        self.power_input_kw = power_in
        self.power_used_kw = self.power_input_kw - (self.curtailed_power_kw + self.power_left_kw)

    def return_outputs(self):
        # return {'power_curtailed': self.curtailed_power, 'stacks_on': self.stacks_on, \
        #     'stacks_waiting': self.stacks_waiting, 'H2_output': self.H2_output}

        return {"H2_output": self.H2_output, "H2_mfr":self.H2_mfr, "stacks_on": self.stacks_on, 
                "stacks_waiting": self.stacks_waiting, "power_used_kw": self.power_used_kw,
                "power_input_kw": self.power_input_kw}

    def step(self, inputs):
        # Gather inputs
        local_power = inputs["py_sims"]["inputs"][
            "locally_generated_power"
        ]  # TODO check what units this is in
        if "electrolyzer_signal" in inputs["py_sims"]["inputs"].keys():
            power_command_kw = inputs["py_sims"]["inputs"]["electrolyzer_signal"]
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

        return self.return_outputs()
