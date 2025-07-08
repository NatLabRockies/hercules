# Very simple solar farm model
from hercules.python_simulators.base_pysim import PySimBase


class SimpleSolar(PySimBase):
    def __init__(self, h_dict):
        """
        Initializes the SimpleSolar class.
        Args:
            h_dict (dict): Dict containing values for the simulation
        """
        # Need dt, plant capacity and efficiency
        # Using base value of 1000 W/m^2 irradiance for sizing

        # Store the name of this py_sim
        self.py_sim_name = "solar_farm"

        # Store the type of this py_sim
        self.py_sim_type = "SimpleSolar"

        # Call the base class init
        super().__init__(h_dict, self.py_sim_name)

        # Efficiency currently denotes the kind of solar panel you have
        # need a realistic efficiency for a solar panel
        self.efficiency = h_dict[self.py_sim_name]["efficiency"]
        self.capacity = h_dict[self.py_sim_name]["capacity"]

        # Total area of solar panels
        base_irradiance = 1000  # W/m^2
        self.area = self.capacity / (self.efficiency * base_irradiance)  # in m^2

        # Save the initial condition
        self.power = h_dict[self.py_sim_name]["initial_conditions"]["power"]
        self.irradiance = h_dict[self.py_sim_name]["initial_conditions"]["irradiance"]

    def step(self, h_dict):
        # TODO add tilt tracking - haven't gotten to this yet
        # right now, just static
        # https://www.sciencedirect.com/science/article/pii/S1364032106001134

        # Note: irradiance is measured in W/m^2, so the power is calculated in Watts,
        #           and then scaled to kW
        # self.power = 0.0

        # Assume model generates its own irradiance
        irradiance = 1000.0

        # Save this as an output for now
        self.irradiance = irradiance

        # Gather inputs
        # irradiance = inputs['irradiance']

        self.power = irradiance * self.area * self.efficiency / 1e3 * self.dt
        if self.power < 0.0:
            self.power = 0.0

        # NOTE: need to talk about whether to have time step in here or not
        # Need to put outputs into input/output structure

        # Update the h_dict with outputs
        h_dict[self.py_sim_name]["power"] = self.power
        h_dict[self.py_sim_name]["irradiance"] = self.irradiance

        return h_dict
