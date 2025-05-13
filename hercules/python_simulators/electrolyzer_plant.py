# Electrolyzer plant module
from electrolyzer.simulation.supervisor import Supervisor


class ElectrolyzerPlant:
    def __init__(self, input_dict, dt):
        electrolyzer_dict = {}
        electrolyzer_dict["general"] = input_dict["general"]
        electrolyzer_dict["electrolyzer"] = input_dict["electrolyzer"]
        electrolyzer_dict["electrolyzer"]["dt"] = dt

        if "allow_grid_charging" in input_dict.keys():
            self.allow_grid_charging = input_dict["allow_grid_charging"]
        else:
            self.allow_grid_charging = True

        # Initialize electrolyzer plant
        self.elec_sys = Supervisor.from_dict(electrolyzer_dict["electrolyzer"])

        self.n_stacks = self.elec_sys.n_stacks

        # Right now, the plant initialization power and the initial condition power are the same
        # power_in is always in MW
        power_in = input_dict["electrolyzer"]["initial_power_kW"] / 1e3
        self.needed_inputs = {"locally_generated_power": power_in}

        # Run Electrolyzer two steps to get outputs
        for i in range(2):
            H2_produced, H2_mfr, power_left, power_curtailed = self.elec_sys.run_control(
                power_in * 1e6
            )
        # Initialize outputs for controller step
        self.stacks_on = sum([self.elec_sys.stacks[i].stack_on for i in range(self.n_stacks)])
        self.stacks_waiting = [False] * self.n_stacks
        # # TODO: How should these be initialized? - Should we do one electrolyzer step?
        #           will that make it out of step of with the other sources?
        self.curtailed_power = power_curtailed / 1e6
        self.H2_output = H2_produced

    def return_outputs(self):
        # return {'power_curtailed': self.curtailed_power, 'stacks_on': self.stacks_on, \
        #     'stacks_waiting': self.stacks_waiting, 'H2_output': self.H2_output}

        return {"H2_output": self.H2_output, "stacks_on": self.stacks_on}

    def step(self, inputs):
        # Gather inputs
        local_power = inputs["py_sims"]["inputs"][
            "locally_generated_power"
        ]  # TODO check what units this is in
        power_command = inputs["py_sims"]["inputs"]["electrolyzer_signal"]

        if self.allow_grid_charging:
            power_in = power_command
        else:
            power_in = min(local_power, power_command)

        # Run electrolyzer forward one step
        ######## Electrolyzer needs input in Watts ########
        H2_produced, H2_mfr, power_left, power_curtailed = self.elec_sys.run_control(power_in * 1e3)

        # Collect outputs from electrolyzer step
        self.curtailed_power = power_curtailed / 1e6
        self.stacks_on = sum([self.elec_sys.stacks[i].stack_on for i in range(self.n_stacks)])
        self.stacks_waiting = [self.elec_sys.stacks[i].stack_waiting for i in range(self.n_stacks)]
        self.H2_output = H2_produced

        return self.return_outputs()
