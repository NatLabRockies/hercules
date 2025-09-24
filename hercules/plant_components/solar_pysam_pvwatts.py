"""PVWatts-based solar simulator using simplified PV model."""

import numpy as np
import PySAM.Pvwattsv8 as pvwatts
from hercules.plant_components.solar_pysam_base import SolarPySAMBase


class SolarPySAMPVWatts(SolarPySAMBase):
    """Solar simulator using PySAM's simplified PV model (Pvwattsv8)."""

    def __init__(self, h_dict):
        """Initialize the PVWatts solar simulator.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
        """
        # Store the type of this component
        self.component_type = "SolarPySAMPVWatts"

        # Call the base class init
        super().__init__(h_dict)

        # Set up PV system model parameters
        self._setup_model_parameters(h_dict)

        # Create and configure the PySAM model
        self._create_system_model()

        # Pre-compute the full power array for all time steps
        self._precompute_power_array()

    def _setup_model_parameters(self, h_dict):
        """Set up the PV system model parameters.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.
        """
        # First, set location parameters needed for the conversion function
        self.elev = h_dict[self.component_name]["elev"]
        self.lat = h_dict[self.component_name]["lat"]
        self.lon = h_dict[self.component_name]["lon"]

        # Convert nameplate DC capacity to PVWatts system_capacity
        pvwatts_system_capacity = self._nameplate_to_pvwatts_system_capacity(
            h_dict[self.component_name]["nameplate_dc_capacity"]
        )

        sys_design = {
            "ModelParams": {
                "SystemDesign": {
                    "array_type": 3.0,  # single axis backtracking
                    "azimuth": 180.0,
                    "dc_ac_ratio": 1.0,  # Force to 1.0
                    "losses": h_dict[self.component_name]["losses"],
                    "module_type": 2.0,
                    "system_capacity": pvwatts_system_capacity,
                    "tilt": 0.0,
                },
            },
        }

        self.model_params = sys_design["ModelParams"]

    def _nameplate_to_pvwatts_system_capacity(self, nameplate_dc_capacity):
        """Convert nameplate DC capacity to PVWatts system_capacity parameter.

        PVWatts system_capacity represents the nameplate capacity under Standard Test
        Conditions (STC), but under maximum irradiance conditions with tracking, the
        actual output can be much higher. This function calculates what PVWatts
        system_capacity should be set to so that the maximum possible DC output
        equals the desired nameplate_dc_capacity.

        All calculations are performed in kW units as per Hercules standards.

        Args:
            nameplate_dc_capacity (float): Desired maximum DC capacity in kW.

        Returns:
            float: PVWatts system_capacity parameter in kW.
        """
        # Create a reference PVWatts model to determine the scaling relationship
        import PySAM.Pvwattsv8 as pvwatts

        # Use a reference capacity to determine the scaling factor
        reference_capacity = 100.0  # kW

        reference_model = pvwatts.new()
        reference_model.SystemDesign.system_capacity = reference_capacity
        reference_model.SystemDesign.dc_ac_ratio = 1.0
        reference_model.SystemDesign.array_type = 3.0  # single axis backtracking
        reference_model.SystemDesign.azimuth = 180.0
        reference_model.SystemDesign.tilt = 0.0
        reference_model.SystemDesign.losses = 0.0  # No losses for maximum output
        reference_model.SystemDesign.module_type = 2.0

        # Define maximum solar conditions
        max_solar_resource = {
            "tz": 0,
            "elev": self.elev,
            "lat": self.lat,
            "lon": self.lon,
            "year": (2018,),
            "month": (5,),
            "day": (10,),
            "hour": (12,),
            "minute": (31,),
            "dn": (1000.0,),  # High direct normal irradiance
            "df": (100.0,),  # Moderate diffuse irradiance
            "gh": (1000.0,),  # High global horizontal irradiance
            "wspd": (0.44,),  # Wind speed
            "tdry": (12.0,),  # Temperature
        }

        reference_model.SolarResource.assign({"solar_resource_data": max_solar_resource})
        reference_model.AdjustmentFactors.assign({"constant": 0})
        reference_model.execute()

        # Get the maximum DC output for the reference capacity
        max_dc_output = reference_model.Outputs.dc[0] / 1000.0  # Convert W to kW

        # Calculate the scaling factor: how much more power does PVWatts produce
        # than its system_capacity under max conditions
        scaling_factor = max_dc_output / reference_capacity

        # To get the desired nameplate_dc_capacity as maximum output,
        # we need to set system_capacity to nameplate_dc_capacity / scaling_factor
        pvwatts_system_capacity = nameplate_dc_capacity / scaling_factor

        return pvwatts_system_capacity

    def _create_system_model(self):
        """Create and configure the PySAM system model."""
        # Create pysam model
        system_model = pvwatts.new()
        system_model.assign(self.model_params)

        system_model.AdjustmentFactors.adjust_constant = 0
        system_model.AdjustmentFactors.dc_adjust_constant = 0

        # Save the system model
        self.system_model = system_model

    def _precompute_power_array(self):
        """Pre-compute the full power array for all time steps."""
        # Prepare solar resource data for all time steps
        solar_resource_data = {
            "tz": self.tz,  # 0 for UTC
            "elev": self.elev,
            "lat": self.lat,  # latitude
            "lon": self.lon,  # longitude
            "year": tuple(self.year_array),  # year array
            "month": tuple(self.month_array),  # month array
            "day": tuple(self.day_array),  # day array
            "hour": tuple(self.hour_array),  # hour array
            "minute": tuple(self.minute_array),  # minute array
            "dn": tuple(self.dni_array),  # direct normal irradiance array
            "df": tuple(self.dhi_array),  # diffuse irradiance array
            "gh": tuple(self.ghi_array),  # global horizontal irradiance array
            "wspd": tuple(self.wind_speed_array),  # windspeed array
            "tdry": tuple(self.temp_array),  # dry bulb temperature array
        }

        # Assign the full solar resource data
        self.system_model.SolarResource.assign({"solar_resource_data": solar_resource_data})
        self.system_model.AdjustmentFactors.assign({"constant": 0})

        # Execute the model once for all time steps
        self.system_model.execute()

        # Store the pre-computed power array (convert from W to kW immediately)
        # No scaling needed since PVWatts system_capacity was already adjusted
        # in _setup_model_parameters
        self.power_uncurtailed = np.array(self.system_model.Outputs.dc) / 1000.0  # Convert W to kW

        # Store other outputs as arrays for efficient access
        self.dni_array_output = np.array(self.system_model.Outputs.dn)
        self.dhi_array_output = np.array(self.system_model.Outputs.df)
        self.ghi_array_output = np.array(self.system_model.Outputs.gh)
        self.aoi_array_output = np.array(self.system_model.Outputs.aoi)
        self.poa_array_output = np.array(self.system_model.Outputs.poa)

    def _get_step_outputs(self, step):
        """Get the outputs for a specific step from pre-computed arrays.

        Args:
            step (int): Current simulation step.
        """
        # Extract outputs specific to PVWatts model for this step
        self.dni = self.dni_array_output[step]  # direct normal irradiance
        self.dhi = self.dhi_array_output[step]  # diffuse horizontal irradiance
        self.ghi = self.ghi_array_output[step]  # global horizontal irradiance
        self.aoi = self.aoi_array_output[step]  # angle of incidence
        self.poa = self.poa_array_output[step]  # plane of array irradiance
