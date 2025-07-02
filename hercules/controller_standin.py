from abc import abstractmethod


class ControllerStandinNoHelics:
    """
    This class is a pass-through stand-in for a plant-level controller.
    Actual controllers should be implemented in WHOC
    (https://github.com/NREL/wind-hybrid-open-controller). However, this
    has been left in to allow users to run Hercules without plant-level
    control, if desired.

    This assumes Hercules is running with actuator disk turbine models, and
    will be updated (to be simply a pass-through) when the ROSCO/FAST turbine
    models are incorporated.
    """

    def __init__(self, input_dict):
        # Get wind farm information (assumes exactly one wind farm)
        # Assumes WindSimLongTerm is first entry in py_sims
        self.wf_name = list(input_dict["py_sims"].keys())[0]

    @abstractmethod
    def step(self, main_dict):
        num_turbines = main_dict["py_sims"][self.wf_name]["num_turbines"]

        # Set deratings very high for now
        for t_idx in range(num_turbines):
            main_dict["py_sims"]["inputs"][f"derating_{t_idx:03d}"] = 4000

        # Lower t0 derating every other 100 seconds
        if main_dict["time"] % 200 < 100:
            main_dict["py_sims"]["inputs"]["derating_000"] = 500

        # # Set turbine yaw angles based on current AMR-Wind wind direction
        # wd = main_dict["hercules_comms"]["amr_wind"][self.wf_name]["wind_direction"]
        # main_dict["hercules_comms"]["amr_wind"][self.wf_name]["turbine_yaw_angles"] = (
        #     num_turbines * [wd]
        # )

        # TODO: does there need to be a seperate "controller" dict?
        # Might make understanding the log easier?
        return main_dict


# Can uncomment the below and work on once the ROSCO/FAST connection is
# in place and we are no longer using actuator disks.

# class Controller():

#     def __init__(self, input_dict):
#         pass

#     def step(self, main_dict):

#         pass

#     def get_controller_dict(self):

#         return {}
