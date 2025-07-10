# Using PySAM to predict PV power based on weather data
# code originally copied from https://github.com/NREL/pysam/blob/main/Examples/NonAnnualSimulation.ipynb

import json
import sys

import numpy as np
import pandas as pd
from hercules.python_simulators.base_pysim import PySimBase

# import PySAM.Pvsamv1Tools # keep for when this is available on PyPi
from hercules.tools.Pvsamv1Tools import size_electrical_parameters
from hercules.utilities import interpolate_df


class SolarPySAM(PySimBase):
    def __init__(self, h_dict):
        """
        Initializes the WindSimLongTerm class.
        Args:
            h_dict (dict): Dict containing values for the simulation
        """
        # Store the name of this py_sim
        self.py_sim_name = "solar_farm"

        # Store the type of this py_sim
        self.py_sim_type = "SolarPySAM"

        # Call the base class init
        super().__init__(h_dict, self.py_sim_name)

        # Add to the log outputs with specific outputs
        # Note that power is assumed in the base class
        self.log_outputs = self.log_outputs 

        # If "log_extra_outputs" is in h_dict[self.py_sim_name],
        # Save this value to self.log_extra_outputs
        if "log_extra_outputs" in h_dict[self.py_sim_name]:
            self.log_extra_outputs = h_dict[self.py_sim_name]["log_extra_outputs"]
        else:
            self.log_extra_outputs = False

        # If log_extra_outputs is True, add the extra outputs to the log outputs
        if self.log_extra_outputs:
            self.log_outputs = self.log_outputs + [
                "dni",
                "poa",
                "aoi",
            ]


        # get pysam model from input file
        if "pysam_model" in h_dict[self.py_sim_name]:
            self.pysam_model = h_dict[self.py_sim_name]["pysam_model"]
        else:
            self.pysam_model = "pvsam"
            self.logger.info("No PySAM model specified. Setting to pvsam (detailed PV model).")

        if self.pysam_model == "pvsam":
            import PySAM.Pvsamv1 as pvsam
        elif self.pysam_model == "pvwatts":
            import PySAM.Pvwattsv8 as pvwatts
        else:
            raise ValueError(
                f"Unknown PySAM model: {self.pysam_model}. "
                f"Supported models are 'pvsam' and 'pvwatts'."
            )

        # Check that either
        # 1. There is solar_input_filename that is not None and no weather_data_input dictionary
        #    or
        # 2. There is a weather_data_input dictionary and either:
        #       solar_input_filename is not in h_dict[self.py_sim_name] or is none
        if ("solar_input_filename" in h_dict[self.py_sim_name]) and (
            h_dict[self.py_sim_name]["solar_input_filename"] is not None
        ):
            if "weather_data_input" in h_dict[self.py_sim_name]:
                raise ValueError(
                    f"Cannot have both solar_input_filename and weather_data_input "
                    f"in h_dict[{self.py_sim_name}]"
                )
            else:
                if h_dict[self.py_sim_name]["solar_input_filename"].endswith(".csv"):
                    df_solar = pd.read_csv(h_dict[self.py_sim_name]["solar_input_filename"])
                elif h_dict[self.py_sim_name]["solar_input_filename"].endswith(".p"):
                    df_solar = pd.read_pickle(h_dict[self.py_sim_name]["solar_input_filename"])
                elif (h_dict[self.py_sim_name]["solar_input_filename"].endswith(".f")) | (
                    h_dict[self.py_sim_name]["solar_input_filename"].endswith(".ftr")
                ):
                    df_solar = pd.read_feather(h_dict[self.py_sim_name]["solar_input_filename"])
        else:
            if "weather_data_input" not in h_dict[self.py_sim_name]:
                raise ValueError(
                    f"Must have either solar_input_filename or weather_data_input "
                    f"in h_dict[{self.py_sim_name}]"
                )
            else:
                df_solar = pd.DataFrame.from_dict(h_dict[self.py_sim_name]["weather_data_input"])

        # Make sure the df_wi contains a column called "time"
        if "time" not in df_solar.columns:
            raise ValueError("Solar input file must contain a column called 'time'")

        # Make sure that both starttime and endtime are in the df_wi
        if not (df_solar["time"].min() <= self.starttime <= df_solar["time"].max()):
            raise ValueError(
                f"Start time {self.starttime} is not in the range of the solar input file"
            )
        if not (df_solar["time"].min() <= self.endtime - self.dt <= df_solar["time"].max()):
            raise ValueError(
                f"End time {self.endtime - self.dt} is not in the range of the solar input file"
            )

        # Solar data must contain time_utc since pysam requires time
        if "time_utc" not in df_solar.columns:
            raise ValueError("Solar input file must contain a column called 'time_utc'")

        # Make sure time_utc is a datatime
        df_solar["time_utc"] = pd.to_datetime(df_solar["time_utc"], format="ISO8601", utc=True)

        # Interpolate df_wi on to the time steps
        time_steps_all = np.arange(self.starttime, self.endtime, self.dt)
        df_solar = interpolate_df(df_solar, time_steps_all)

        # Can now save the input data as simple columns
        self.year_array = df_solar["time_utc"].dt.year.values
        self.month_array = df_solar["time_utc"].dt.month.values
        self.day_array = df_solar["time_utc"].dt.day.values
        self.hour_array = df_solar["time_utc"].dt.hour.values
        self.minute_array = df_solar["time_utc"].dt.minute.values
        self.ghi_array = self._get_solar_data_array(df_solar, "Global Horizontal Irradiance")
        self.dni_array = self._get_solar_data_array(df_solar, "Direct Normal Irradiance")
        self.dhi_array = self._get_solar_data_array(df_solar, "Diffuse Horizontal Irradiance")
        self.temp_array = self._get_solar_data_array(df_solar, "Temperature")
        self.wind_speed_array = self._get_solar_data_array(df_solar, "Wind Speed at")

        # Save the system capacity
        self.target_system_capacity = h_dict[self.py_sim_name]["target_system_capacity"]

        # set PV system model parameters
        if self.pysam_model == "pvsam":
            try:
                self.logger.info(
                    "reading initial system info from {}".format(
                        h_dict[self.py_sim_name]["system_info_file_name"]
                    )
                )
                with open(h_dict[self.py_sim_name]["system_info_file_name"], "r") as f:
                    model_params = json.load(f)
                sys_design = {
                    "ModelParams": model_params,
                    "Other": {
                        "lat": h_dict[self.py_sim_name]["lat"],
                        "lon": h_dict[self.py_sim_name]["lon"],
                        "elev": h_dict[self.py_sim_name]["elev"],
                    },
                }

            except Exception:
                self.logger.info("Error: No PV system info json file specified for pvsam model.")
                sys.exit(1)  # exit program

                # TODO: use a default if none provided
                # sys_design = pvsam.default("FlatPlatePVSingleOwner")

        elif self.pysam_model == "pvwatts":
            sys_design = {
                "ModelParams": {
                    "SystemDesign": {
                        "array_type": 3.0,  # single axis backtracking
                        "azimuth": 180.0,
                        "dc_ac_ratio": h_dict[self.py_sim_name]["target_dc_ac_ratio"],
                        "gcr": 0.29999999999999999,
                        "inv_eff": 96,
                        "losses": 14.075660688264469,
                        "module_type": 2.0,
                        "system_capacity": h_dict[self.py_sim_name]["target_system_capacity"],
                        "tilt": 0.0,
                    },
                },
                "Other": {
                    "lat": h_dict[self.py_sim_name]["lat"],
                    "lon": h_dict[self.py_sim_name]["lon"],
                    "elev": h_dict[self.py_sim_name]["elev"],
                },
            }

        self.model_params = sys_design["ModelParams"]
        self.elev = sys_design["Other"]["elev"]
        self.lat = sys_design["Other"]["lat"]
        self.lon = sys_design["Other"]["lon"]

        # Since using UTC, assume tz is always 0
        self.tz = 0

        # Save the initial condition
        self.power = h_dict[self.py_sim_name]["initial_conditions"]["power"]
        self.dc_power = h_dict[self.py_sim_name]["initial_conditions"]["power"]
        self.dni = h_dict[self.py_sim_name]["initial_conditions"]["dni"]
        self.poa = h_dict[self.py_sim_name]["initial_conditions"]["poa"]
        self.aoi = 0

        # dynamic sizing special treatment only required for pvsam model, not for pvwatts
        if self.pysam_model == "pvsam":
            self.target_system_capacity = h_dict[self.py_sim_name]["target_system_capacity"]
            self.target_dc_ac_ratio = h_dict[self.py_sim_name]["target_dc_ac_ratio"]

        # create pysam model
        if self.pysam_model == "pvsam":
            system_model = pvsam.new()
        elif self.pysam_model == "pvwatts":
            system_model = pvwatts.new()
            system_model.assign(self.model_params)

        system_model.AdjustmentFactors.adjust_constant = 0
        system_model.AdjustmentFactors.dc_adjust_constant = 0

        # Set parameters for pvsam model only (pvwatts parameters are set via assign())
        if self.pysam_model == "pvsam":
            for k, v in self.model_params.items():
                try:
                    system_model.value(k, v)
                except Exception as e:
                    error_type = type(e).__name__
                    error_message = str(e)
                    print(
                        f"Warning: pysam error with parameter '{k}': {error_type} - {error_message}"
                    )
                    print("Warning: continuing the simulation despite warning")

        # Save the system model
        self.system_model = system_model

        self.needed_inputs = {}

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

    def _get_solar_data_array(self, df_, column_substring):
        """
        Get the values of the first column in the df whose name contains the specified substring.
        Args:
            df_ (pd.DataFrame): The DataFrame to search for the column.
            column_substring (str): The substring to look for in the column names.
        Returns:
            np.ndarray: The values of the matching column as a NumPy array.
        """

        for column in df_.columns:
            if column_substring in column:
                return df_[column].values
        raise ValueError(f"Could not find column with substring {column_substring} in df_solar")

    def control(self, power_setpoint=None):
        """
        Controls the PV plant power output to meet a specified setpoint.

        This low-level controller enforces power setpoints for the PV plant by
        applying uniform curtailment across the entire plant. Note that DC power
        output is not controlled as it is not utilized elsewhere in the code.

        Args:
            power_setpoint (float, optional): Desired total PV plant output in kW.
                If None, no control is applied.

        """

        # modify power output based on setpoint
        if power_setpoint is not None:
            if self.verbose:
                self.logger.info(f"power_setpoint = {power_setpoint}")
            if self.power > power_setpoint:
                self.power = power_setpoint
                # Keep track of power that could go to charging battery
                self.excess_power = self.power - power_setpoint
            if self.verbose:
                self.logger.info(f"self.power after control = {self.power}")

    def step(self, h_dict):
        # Get the current  step
        step = h_dict["step"]
        if self.verbose:
            self.logger.info(f"step = {step} (of {self.n_steps})")

        # Assign solar resource for this step
        solar_resource_data = {
            "tz": self.tz,  # 0 for UTC
            "elev": self.elev,
            "lat": self.lat,  # latitude
            "lon": self.lon,  # longitude
            "year": tuple([self.year_array[step]]),  # year
            "month": tuple([self.month_array[step]]),  # month
            "day": tuple([self.day_array[step]]),  # day
            "hour": tuple([self.hour_array[step]]),  # hour
            "minute": tuple([self.minute_array[step]]),  # minute
            "dn": tuple([self.dni_array[step]]),  # direct normal irradiance
            "df": tuple([self.dhi_array[step]]),  # diffuse irradiance
            "gh": tuple([self.ghi_array[step]]),  # global horizontal irradiance
            "wspd": tuple([self.wind_speed_array[step]]),  # windspeed (not peak)
            "tdry": tuple([self.temp_array[step]]),  # dry bulb temperature
        }

        self.system_model.SolarResource.assign({"solar_resource_data": solar_resource_data})
        self.system_model.AdjustmentFactors.assign({"constant": 0})

        # dynamic sizing special treatment only required for pvsam model, not for pvwatts
        if self.pysam_model == "pvsam":
            target_system_capacity = self.target_system_capacity
            target_ratio = self.target_dc_ac_ratio
            n_strings, n_combiners, n_inverters, calc_sys_capacity = size_electrical_parameters(
                self.system_model, target_system_capacity, target_ratio
            )

        self.system_model.execute()

        ac = np.array(self.system_model.Outputs.gen)  # in kW
        self.power = ac[0]  # calculating one timestep at a time
        if self.verbose:
            self.logger.info(f"self.power = {self.power}")

        # Apply control, if setpoint is provided
        if "solar_setpoint" in h_dict[self.py_sim_name]:
            P_setpoint = h_dict[self.py_sim_name]["solar_setpoint"]
        elif "external_signals" in h_dict.keys():
            if "solar_power_reference" in h_dict["external_signals"].keys():
                P_setpoint = h_dict["external_signals"]["solar_power_reference"]
            else:
                P_setpoint = None
        else:
            P_setpoint = None

        # # Further the cap the P_setpoint by the room left after wind power is deducted
        # wind_farm_power = inputs['py_sims']["wind_farm_0"]["outputs"]["wind_farm_total_power"]
        # available_interconnect = self.target_system_capacity - wind_farm_power

        # if P_setpoint is None:
        #     P_setpoint = available_interconnect
        # else:
        #     P_setpoint = min(P_setpoint, available_interconnect)
        self.control(P_setpoint)

        if self.power < 0.0:
            self.power = 0.0
        # NOTE: need to talk about whether to have time step in here or not

        self.dni = self.system_model.Outputs.dn[0]  # direct normal irradiance
        self.dhi = self.system_model.Outputs.df[0]  # diffuse horizontal irradiance
        self.ghi = self.system_model.Outputs.gh[0]  # global horizontal irradiance

        if self.pysam_model == "pvsam":
            self.aoi = self.system_model.Outputs.subarray1_aoi[0]  # angle of incidence
            self.poa = self.system_model.Outputs.subarray1_poa_eff[0]  # plane of array irradiance
        elif self.pysam_model == "pvwatts":
            self.aoi = self.system_model.Outputs.aoi[0]  # angle of incidence
            self.poa = self.system_model.Outputs.poa[0]  # plane of array irradiance

        if self.verbose:
            print("self.poa = ", self.poa)

        # Update the h_dict with outputs
        h_dict[self.py_sim_name]["power"] = self.power
        h_dict[self.py_sim_name]["dni"] = self.dni
        h_dict[self.py_sim_name]["poa"] = self.poa
        h_dict[self.py_sim_name]["aoi"] = self.aoi

        return h_dict
