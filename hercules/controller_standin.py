class ControllerStandin:
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

    def __init__(self, h_dict):
        # # Get wind farm information (assumes exactly one wind farm)
        # # Assumes WindSimLongTerm is first entry in py_sims
        # self.wf_name = list(input_dict["py_sims"].keys())[0]
        pass

    def step(self, h_dict):
        num_turbines = h_dict["wind_farm"]["num_turbines"]

        # Set deratings very high for now
        for t_idx in range(num_turbines):
            h_dict["wind_farm"][f"derating_{t_idx:03d}"] = 4000

        # Lower t0 derating every other 100 seconds
        if h_dict["time"] % 200 < 100:
            h_dict["wind_farm"]["derating_000"] = 500

        return h_dict


# Can uncomment the below and work on once the ROSCO/FAST connection is
# in place and we are no longer using actuator disks.

# class Controller():

#     def __init__(self, input_dict):
#         pass

#     def step(self, main_dict):

#         pass

#     def get_controller_dict(self):

#         return {}
