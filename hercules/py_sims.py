import numpy as np

from hercules.python_simulators.battery import Battery
from hercules.python_simulators.electrolyzer_plant import ElectrolyzerPlant
from hercules.python_simulators.simple_solar import SimpleSolar
from hercules.python_simulators.solar_pysam import SolarPySAM
from hercules.python_simulators.wind_sim_long_term import WindSimLongTerm


class PySims:
    def __init__(self, input_dict):
        # Save time information
        self.dt = input_dict["dt"]
        self.starttime = input_dict["starttime"]
        self.endtime = input_dict["endtime"]
        

        # Grab py sim details
        self.py_sim_dict = input_dict["py_sims"]

        # If None n_py_sim = 0
        if input_dict["py_sims"] is None:
            self.n_py_sim = 0
            self.py_sim_names = []

        else:
            self.n_py_sim = len(self.py_sim_dict)
            self.py_sim_names = np.copy(list(self.py_sim_dict.keys()))
            self.py_sim_dict["inputs"] = {}
            self.py_sim_dict["inputs"][
                "available_power"
            ] = 0  # Always calculate available power for py_sims

            # Collect the py_sim objects, inputs and outputs
            for py_sim_name in self.py_sim_names:
                self.py_sim_dict[py_sim_name]["object"] = self.get_py_sim(
                    self.py_sim_dict[py_sim_name]
                )
                self.py_sim_dict[py_sim_name]["outputs"] = self.py_sim_dict[py_sim_name][
                    "object"
                ].return_outputs()
                self.py_sim_dict[py_sim_name]["inputs"] = {}
                for needed_input in self.py_sim_dict[py_sim_name]["object"].needed_inputs.keys():
                    self.py_sim_dict["inputs"][needed_input] = self.py_sim_dict[py_sim_name][
                        "object"
                    ].needed_inputs[needed_input]


    def get_py_sim(self, py_sim_obj_dict):
        if py_sim_obj_dict["py_sim_type"] == "SimpleSolar":
            return SimpleSolar(py_sim_obj_dict, self.dt, self.starttime, self.endtime)

        if py_sim_obj_dict["py_sim_type"] == "SolarPySAM":
            return SolarPySAM(py_sim_obj_dict, self.dt, self.starttime, self.endtime)

        if py_sim_obj_dict["py_sim_type"] in [ "SimpleBattery", "LIB"]:
            return Battery(py_sim_obj_dict, self.dt, self.starttime, self.endtime)

        if py_sim_obj_dict["py_sim_type"] == "ElectrolyzerPlant":
            return ElectrolyzerPlant(py_sim_obj_dict, self.dt, self.starttime, self.endtime)
        
        if py_sim_obj_dict["py_sim_type"] == 'WindSimLongTerm':
            return WindSimLongTerm(py_sim_obj_dict, self.dt, self.starttime, self.endtime)

        raise Exception("Unknown py_sim_type: ", py_sim_obj_dict["py_sim_type"])

    def get_py_sim_dict(self):
        return self.py_sim_dict

    def step(self, main_dict):
        # Collect the py_sim objects
        py_sims_available_power = 0.0
        for py_sim_name in self.py_sim_names:

            self.py_sim_dict[py_sim_name]["outputs"] = self.py_sim_dict[py_sim_name]["object"].step(
                main_dict
            )
            if "Solar" in self.py_sim_dict[py_sim_name]["py_sim_type"]:
                # TODO: Remove try/except once all solar module options have same outputs
                try:
                    solar_power = self.py_sim_dict[py_sim_name]["outputs"]["power_mw"]*1000
                except KeyError:
                    solar_power = self.py_sim_dict[py_sim_name]["outputs"]["power"]*1000
                py_sims_available_power += solar_power

        self.py_sim_dict["inputs"]["available_power"] = py_sims_available_power
