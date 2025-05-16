# Using PySAM to predict PV power based on weather data
# code originally copied from https://github.com/NREL/pysam/blob/main/Examples/NonAnnualSimulation.ipynb

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
#import PySAM.Pvsamv1Tools # keep for when this is available on PyPi
from hercules.tools.Pvsamv1Tools import size_electrical_parameters
from hercules.utilities import interpolate_df


class SolarPySAM:
    def __init__(self, input_dict, dt, starttime, endtime):
        """
        Initializes the SolarPySAM class.
        Args:
            input_dict (dict): Input dictionary containing parameters for the solar simulation.
            dt (float): Time step for the simulation.
            starttime (float): Start time for the simulation.
            endtime (float): End time for the simulation.
        """
        # Check if log_file_name is defined in the input_dict
        if "log_file_name" in input_dict:
            self.log_file_name = input_dict["log_file_name"]
        else:
            self.log_file_name = "outputs/log_solar_sim.log"

        # Set up logging
        self.logger = self._setup_logging(self.log_file_name)

        self.logger.info("trying to read in verbose flag")
        if "verbose" in input_dict:
            self.verbose = input_dict["verbose"]
            self.logger.info(f"read in verbose flag = {self.verbose}")
        else:
            self.verbose = True  # default value

        # get pysam model from input file
        if "pysam_model" in input_dict:
            self.pysam_model = input_dict["pysam_model"]
        else:
            self.pysam_model = "pvsam"
            self.logger.info("No PySAM model specified. Setting to pvsam (detailed PV model).")

        if self.pysam_model == "pvsam":
            import PySAM.Pvsamv1 as pvsam
        elif self.pysam_model == "pvwatts":
            import PySAM.Pvwattsv8 as pvwatts

        # Save the time information
        self.dt = dt
        self.starttime = starttime
        self.endtime = endtime

        # Compute the number of time steps
        self.n_steps = int((self.endtime - self.starttime) / self.dt)

        # Check that either
        # 1. There is solar_input_filename that is not None and no weather_data_input dictionary
        #    or
        # 2. There is a weather_data_input dictionary and either:
        #       solar_input_filename is not in input_dict or is none
        if ("solar_input_filename" in input_dict) and (
            input_dict["solar_input_filename"] is not None
        ):
            if "weather_data_input" in input_dict:
                raise ValueError(
                    "Cannot have both solar_input_filename and weather_data_input in input_dict"
                )
            else:
                if input_dict["solar_input_filename"].endswith(".csv"):
                    df_solar = pd.read_csv(input_dict["solar_input_filename"])
                elif input_dict["solar_input_filename"].endswith(".p"):
                    df_solar = pd.read_pickle(input_dict["solar_input_filename"])
                elif (input_dict["solar_input_filename"].endswith(".f")) | (
                    input_dict["solar_input_filename"].endswith(".ftr")
                ):
                    df_solar = pd.read_feather(input_dict["solar_input_filename"])
        else:
            if "weather_data_input" not in input_dict:
                raise ValueError(
                    "Must have either solar_input_filename or weather_data_input in input_dict"
                )
            else:
                df_solar = pd.DataFrame.from_dict(input_dict["weather_data_input"])

        # Make sure the df_wi contains a column called "time"
        if "time" not in df_solar.columns:
            raise ValueError("Solar input file must contain a column called 'time'")

        # Make sure that both starttime and endtime are in the df_wi
        if not (df_solar["time"].min() <= self.starttime <= df_solar["time"].max()):
            raise ValueError(
                f"Start time {self.starttime} is not in the range of the solar input file"
            )
        if not (df_solar["time"].min() <= self.endtime - dt <= df_solar["time"].max()):
            raise ValueError(
                f"End time {self.endtime - dt} is not in the range of the solar input file"
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

        # set PV system model parameters
        if self.pysam_model == "pvsam":
            try:
                self.logger.info(
                    "reading initial system info from {}".format(
                        input_dict["system_info_file_name"]
                    )
                )
                with open(input_dict["system_info_file_name"], "r") as f:
                    model_params = json.load(f)
                sys_design = {
                    "ModelParams": model_params,
                    "Other": {
                        "lat": input_dict["lat"],
                        "lon": input_dict["lon"],
                        "elev": input_dict["elev"],
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
                        "dc_ac_ratio": input_dict["target_dc_ac_ratio"],
                        "gcr": 0.29999999999999999,
                        "inv_eff": 96,
                        "losses": 14.075660688264469,
                        "module_type": 2.0,
                        "system_capacity": input_dict["target_system_capacity_kW"],
                        "tilt": 0.0,
                    },
                },
                "Other": {
                    "lat": input_dict["lat"],
                    "lon": input_dict["lon"],
                    "elev": input_dict["elev"],
                },
            }

        self.model_params = sys_design["ModelParams"]
        self.elev = sys_design["Other"]["elev"]
        self.lat = sys_design["Other"]["lat"]
        self.lon = sys_design["Other"]["lon"]

        # Since using UTC, assume tz is always 0
        self.tz = 0

        # Save the initial condition
        self.power_mw = input_dict["initial_conditions"]["power"]
        self.dc_power_mw = input_dict["initial_conditions"]["power"]
        self.dni = input_dict["initial_conditions"]["dni"]
        self.poa = input_dict["initial_conditions"]["poa"]
        self.aoi = 0

        # dynamic sizing special treatment only required for pvsam model, not for pvwatts
        if self.pysam_model == "pvsam":
            self.target_system_capacity = input_dict["target_system_capacity_kW"]
            self.target_dc_ac_ratio = input_dict["target_dc_ac_ratio"]

        # create pysam model
        if self.pysam_model == "pvsam":
            system_model = pvsam.new()
        elif self.pysam_model == "pvwatts":
            system_model = pvwatts.new()
            system_model.assign(self.model_params)

        system_model.AdjustmentFactors.adjust_constant = 0
        system_model.AdjustmentFactors.dc_adjust_constant = 0

        # TODO: What does this do?
        for k, v in self.model_params.items():
            try:
                system_model.value(k, v)
            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)
                print(f"Warning: pysam error with parameter '{k}': {error_type} - {error_message}")
                print("Warning: continuing the simulation despite warning")

        # Save the system model
        self.system_model = system_model

        self.needed_inputs = {}

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

    def return_outputs(self):
        return {
            "power_mw": self.power_mw,
            "dni": self.dni,
            "poa": self.poa,
            "aoi": self.aoi,
        }

    def control(self, power_setpoint_mw=None):
        """
        Controls the PV plant power output to meet a specified setpoint.

        This low-level controller enforces power setpoints for the PV plant by
        applying uniform curtailment across the entire plant. Note that DC power
        output is not controlled as it is not utilized elsewhere in the code.

        Args:
            power_setpoint_mw (float, optional): Desired total PV plant output in MW.
                If None, no control is applied.

        """

        # modify power output based on setpoint
        if power_setpoint_mw is not None:
            if self.verbose:
                self.logger.info(f"power_setpoint = {power_setpoint_mw}")
            if self.power_mw > power_setpoint_mw:
                self.power_mw = power_setpoint_mw
                # Keep track of power that could go to charging battery
                self.excess_power = self.power_mw - power_setpoint_mw
            if self.verbose:
                self.logger.info(f"self.power_mw after control = {self.power_mw}")

    def step(self, inputs):
        # Get the current  step
        step = inputs["step"]
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

        ac = np.array(self.system_model.Outputs.gen) / 1000  # in MW
        self.power_mw = ac[0]  # calculating one timestep at a time
        if self.verbose:
            self.logger.info(f"self.power_mw = {self.power_mw}")

        # Apply control, if setpoint is provided
        if "py_sims" in inputs and "solar_setpoint_mw" in inputs["py_sims"]["inputs"]:
            P_setpoint = inputs["py_sims"]["inputs"]["solar_setpoint_mw"]
        elif "external_signals" in inputs.keys():
            if "solar_power_reference_mw" in inputs["external_signals"].keys():
                P_setpoint = inputs["external_signals"]["solar_power_reference_mw"]
            else:
                P_setpoint = None
        else:
            P_setpoint = None
        self.control(P_setpoint)

        if self.power_mw < 0.0:
            self.power_mw = 0.0
        # NOTE: need to talk about whether to have time step in here or not

        self.dni = self.system_model.Outputs.dn[0]  # direct normal irradiance
        self.dhi = self.system_model.Outputs.df[0]  # diffuse horizontal irradiance
        self.ghi = self.system_model.Outputs.gh[0]  # global horizontal irradiance

        if self.pysam_model == "pvsam":
            self.aoi = self.system_model.Outputs.subarray1_aoi[0]  # angle of incidence
            self.poa = self.system_model.Outputs.subarray1_poa_eff[0]  # plane of array irradiance (f(dni, dhi, ghi))
        elif self.pysam_model == "pvwatts":
            self.aoi = self.system_model.Outputs.aoi[0]  # angle of incidence
            self.poa = self.system_model.Outputs.poa[0]  # plane of array irradiance (f(dni, dhi, ghi))

        if self.verbose:
            print("self.poa = ", self.poa)

        return self.return_outputs()

    def _setup_logging(self, log_file_name):
        """
        Sets up logging for the solar pysam.

        This method configures a logger named "solar_sim" to log messages to a specified file.
        It ensures the log directory exists, clears any existing handlers to avoid duplicates,
        and formats log messages with timestamps, log levels, and messages.
        Args:
            log_file_name (str): The full path to the log file where log messages will be written.
        Returns:
            logging.Logger: Configured logger instance for the solar simulator.
        """

        # Split the logfile into directory and filename
        log_dir = Path(log_file_name).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Get the logger for solar, note that root logger already in use
        logger = logging.getLogger("solar_sim")
        logger.setLevel(logging.INFO)

        # Clear any existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Add file handler
        file_handler = logging.FileHandler(log_file_name)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(file_handler)

        return logger
