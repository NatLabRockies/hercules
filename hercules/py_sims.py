from hercules.python_simulators.simple_battery import SimpleBattery
from hercules.python_simulators.lib import LIB
from hercules.python_simulators.electrolyzer_plant import ElectrolyzerPlant
from hercules.python_simulators.simple_solar import SimpleSolar
from hercules.python_simulators.solar_pysam import SolarPySAM
from hercules.python_simulators.wind_sim_long_term import WindSimLongTerm
from hercules.utilities import get_available_py_sim_names


class PySims:
    def __init__(self, h_dict):
        # get a list of possible py_sim
        all_py_sim_names = get_available_py_sim_names()

        # Make a list of py_sim names that are in the h_dict
        h_dict["py_sim_names"] = [
            py_sim_name for py_sim_name in all_py_sim_names if py_sim_name in h_dict
        ]

        # Add in the number of py_sims
        h_dict["n_py_sim"] = len(self.py_sims)

        # Save the py_sim names and number of py_sims
        self.py_sim_names = h_dict["py_sim_names"]
        self.n_py_sim = h_dict["n_py_sim"]

        # Collect the py_sim objects and attach to the h_dict
        for py_sim_name in self.py_sim_names:
            h_dict[py_sim_name]["object"] = self.get_py_sim(py_sim_name, h_dict)

        return h_dict

    def get_py_sim(self, py_sim_name, h_dict):
        if h_dict[py_sim_name]["py_sim_type"] == "SimpleSolar":
            return SimpleSolar(h_dict)

        if h_dict[py_sim_name]["py_sim_type"] == "SolarPySAM":
            return SolarPySAM(h_dict)
        
        if h_dict[py_sim_name]["py_sim_type"] == "LIB":
            return LIB(h_dict)
        
        if h_dict[py_sim_name]["py_sim_type"] == "SimpleBattery":
            return SimpleBattery(h_dict)


        if h_dict[py_sim_name]["py_sim_type"] == "ElectrolyzerPlant":
            return ElectrolyzerPlant(h_dict)

        if h_dict[py_sim_name]["py_sim_type"] == "WindSimLongTerm":
            return WindSimLongTerm(h_dict)

        raise Exception("Unknown py_sim_type: ", h_dict[py_sim_name]["py_sim_type"])

    def step(self, h_dict):
        # Collect the py_sim objects
        for py_sim_name in self.py_sim_names:
            # Update h_dict by calling the step method of each py_sim object
            h_dict = h_dict[py_sim_name]["object"].step(h_dict)

            # TODO: Replace whatever this is doing...
        #     if "Solar" in self.py_sim_dict[py_sim_name]["py_sim_type"]:
        #         # TODO: Remove try/except once all solar module options have same outputs
        #         try:
        #             solar_power = self.py_sim_dict[py_sim_name]["outputs"]["power_mw"]*1000
        #         except KeyError:
        #             solar_power = self.py_sim_dict[py_sim_name]["outputs"]["power"]*1000
        #         locally_generated_power += solar_power

        # self.py_sim_dict["inputs"]["locally_generated_power"] = locally_generated_power

    def calculate_plant_outputs(self, main_dict):
        for py_sim_name in self.py_sim_names:
            if "Electrolyzer" in self.py_sim_dict[py_sim_name]["py_sim_type"]:
                main_dict["py_sims"]["inputs"]["plant_outputs"]["hydrogen"] = self.py_sim_dict[
                    py_sim_name
                ]["outputs"]["H2_output"]
                main_dict["py_sims"]["inputs"]["plant_outputs"]["electricity"] -= self.py_sim_dict[
                    py_sim_name
                ]["outputs"]["power_used_kw"]
            else:
                main_dict["py_sims"]["inputs"]["plant_outputs"]["electricity"] += self.py_sim_dict[
                    py_sim_name
                ]["outputs"]["power_kW"]
