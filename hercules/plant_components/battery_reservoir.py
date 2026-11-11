"""Energy-reservoir battery storage model."""

import numpy as np
from hercules.plant_components.component_base import ComponentBase


class BatteryReservoir(ComponentBase):
    """Energy-reservoir battery storage model.

    Energy-reservoir model with power and energy limits. Roundtrip efficiency losses
    are applied entirely on charging, so stored energy equals the energy deliverable
    at the terminals. A full discharge at ``power_discharge_max`` lasts
    ``energy_capacity / power_discharge_max`` and a full charge at ``power_charge_max``
    lasts ``energy_capacity / (efficiency_roundtrip * power_charge_max)``.

    Note:
        Within this class positive power is charging. ``HybridPlant`` negates
        ``consumer_sign_outputs`` so that positive power is discharging outside the
        component.
    """

    component_category = "storage"
    consumer_sign_outputs = ("power", "DC_power")

    def __init__(self, h_dict, component_name):
        """Initialize the BatteryReservoir class.

        Args:
            h_dict (dict): Dictionary containing simulation parameters. The component
                section requires:
                - energy_capacity (float): Deliverable energy capacity in kWh.
                - power_charge_max (float): Maximum charge power in kW.
                - power_discharge_max (float): Maximum discharge power in kW.
                - initial_conditions (dict): Initial ``SOC`` (0-1).
                And optionally:
                - SOC_max (float): Maximum state of charge (0-1). Defaults to 1.0.
                - SOC_min (float): Minimum state of charge (0-1). Defaults to 0.0.
                - efficiency_roundtrip (float): Roundtrip efficiency (0-1), applied
                  on charging. Defaults to 1.0.
                - time_constant_self_discharge (float): Self-discharge time constant
                  in s. Defaults to inf (no self-discharge).
                - allow_grid_power_consumption (bool): Allow charging beyond locally
                  generated power. Defaults to False.
            component_name (str): Unique name for this instance (the YAML top-level key).
        """
        super().__init__(h_dict, component_name)
        params = h_dict[component_name]

        self.energy_capacity = params["energy_capacity"]  # [kWh]
        self.power_charge_max = params["power_charge_max"]  # [kW]
        self.power_discharge_max = params["power_discharge_max"]  # [kW]
        self.SOC_max = params.get("SOC_max", 1.0)
        self.SOC_min = params.get("SOC_min", 0.0)
        self.efficiency_roundtrip = params.get("efficiency_roundtrip", 1.0)
        self.time_constant_self_discharge = params.get("time_constant_self_discharge", np.inf)
        self.allow_grid_power_consumption = params.get("allow_grid_power_consumption", False)

        self.energy_max = self.SOC_max * self.energy_capacity  # [kWh]
        self.energy_min = self.SOC_min * self.energy_capacity  # [kWh]
        # Per-step retention from the exact solution of dE/dt = -E / tau (AI)
        self.retention = np.exp(-self.dt / self.time_constant_self_discharge)

        self.SOC = params["initial_conditions"]["SOC"]
        self.energy = self.SOC * self.energy_capacity  # [kWh]
        self.power_charge = 0.0
        self.DC_power_charge = 0.0

    def get_initial_conditions_and_meta_data(self, h_dict):
        """Add any initial conditions or meta data to the h_dict.

        Meta data is data not explicitly in the input yaml but still useful for other
        modules.

        Args:
            h_dict (dict): Dictionary containing simulation parameters.

        Returns:
            dict: Dictionary containing simulation parameters with initial conditions and meta data.
        """
        h_dict[self.component_name]["power"] = 0
        h_dict[self.component_name]["DC_power"] = 0
        h_dict[self.component_name]["SOC"] = self.SOC

        return h_dict

    def step(self, h_dict):
        """Advance the battery simulation by one time step.

        Self-discharge is applied first, then the power setpoint is clipped to the
        power, energy and available-power limits and integrated into the stored energy.

        Args:
            h_dict (dict): Dictionary containing simulation state including:
                - <component_name>.power_setpoint: Requested power in kW (positive
                  is charging).
                - plant.locally_generated_power: Power available for charging in kW.

        Returns:
            dict: Updated h_dict with outputs stored under self.component_name:
                - power: Actual AC power in kW (positive is charging).
                - DC_power: Power into storage after efficiency losses in kW (positive
                  is charging).
                - SOC: State of charge (0-1).
        """
        power_setpoint = h_dict[self.component_name]["power_setpoint"]
        if np.isnan(power_setpoint):
            raise ValueError(f"{self.component_name}: power_setpoint is NaN")

        if self.allow_grid_power_consumption:
            power_charge_available = np.inf
        else:
            power_charge_available = h_dict["plant"]["locally_generated_power"]  # [kW]

        hours = self.dt / 3600
        energy_retained = self.energy * self.retention  # [kWh]

        # Charge-positive power limits [kW]
        power_hi = min(
            self.power_charge_max,
            power_charge_available,
            (self.energy_max - energy_retained) / (hours * self.efficiency_roundtrip),
        )
        power_lo = max(-self.power_discharge_max, (self.energy_min - energy_retained) / hours)
        power_charge = min(max(power_setpoint, min(power_lo, 0.0)), max(power_hi, 0.0))

        if power_charge > 0:
            self.DC_power_charge = self.efficiency_roundtrip * power_charge
        else:
            self.DC_power_charge = power_charge
        self.energy = energy_retained + self.DC_power_charge * hours
        self.SOC = self.energy / self.energy_capacity
        self.power_charge = power_charge

        h_dict[self.component_name]["power"] = self.power_charge
        h_dict[self.component_name]["DC_power"] = self.DC_power_charge
        h_dict[self.component_name]["SOC"] = self.SOC

        return h_dict
