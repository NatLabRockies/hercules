"""Simple battery energy storage model."""

import numpy as np
from hercules.plant_components.component_base import ComponentBase

_REMOVED_KEYS = ("track_usage", "usage_calc_interval", "usage_lifetime", "usage_cycles")


class BatterySimple(ComponentBase):
    """Simple battery energy storage model.

    Energy-reservoir model with power and energy limits. Roundtrip efficiency losses
    are applied entirely on charging, so stored energy equals the energy deliverable
    at the terminals. A full discharge at ``discharge_rate`` lasts
    ``energy_capacity / discharge_rate`` and a full charge at ``charge_rate`` lasts
    ``energy_capacity / (roundtrip_efficiency * charge_rate)``.

    Note:
        Within this class positive power is charging. ``HybridPlant`` inverts the sign
        so that positive power is discharging at the plant level.
    """

    component_category = "storage"

    def __init__(self, h_dict, component_name):
        """Initialize the BatterySimple class.

        Args:
            h_dict (dict): Dictionary containing simulation parameters. The component
                section requires:
                - energy_capacity (float): Deliverable energy capacity in kWh.
                - charge_rate (float): Maximum charge power in kW.
                - discharge_rate (float): Maximum discharge power in kW.
                - initial_conditions (dict): Initial ``SOC`` (0-1).
                And optionally:
                - max_SOC (float): Maximum state of charge (0-1). Defaults to 1.0.
                - min_SOC (float): Minimum state of charge (0-1). Defaults to 0.0.
                - roundtrip_efficiency (float): Roundtrip efficiency (0-1), applied
                  on charging. Defaults to 1.0.
                - self_discharge_time_constant (float): Self-discharge time constant
                  in s. Defaults to inf (no self-discharge).
                - allow_grid_power_consumption (bool): Allow charging beyond locally
                  generated power. Defaults to False.
            component_name (str): Unique name for this instance (the YAML top-level key).

        Raises:
            ValueError: If removed usage-tracking keys are specified.
        """
        super().__init__(h_dict, component_name)
        params = h_dict[component_name]

        removed = [k for k in _REMOVED_KEYS if k in params]
        if removed:
            raise ValueError(
                f"{component_name}: {removed} are no longer supported by BatterySimple. "
                "Usage tracking was removed; compute cycle metrics from the outputs instead."
            )

        self.energy_capacity = params["energy_capacity"]  # [kWh]
        self.charge_rate = params["charge_rate"]  # [kW]
        self.discharge_rate = params["discharge_rate"]  # [kW]
        self.SOC_max = params.get("max_SOC", 1.0)
        self.SOC_min = params.get("min_SOC", 0.0)
        self.roundtrip_efficiency = params.get("roundtrip_efficiency", 1.0)
        self.tau_self_discharge = params.get("self_discharge_time_constant", np.inf)  # [s]
        self.allow_grid_power_consumption = params.get("allow_grid_power_consumption", False)

        self.E_max = self.SOC_max * self.energy_capacity  # [kWh]
        self.E_min = self.SOC_min * self.energy_capacity  # [kWh]
        # Per-step retention from the exact solution of dE/dt = -E / tau (AI)
        self.decay = np.exp(-self.dt / self.tau_self_discharge)

        self.SOC = params["initial_conditions"]["SOC"]
        self.E = self.SOC * self.energy_capacity  # [kWh]
        self.power_kw = 0.0

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
        h_dict[self.component_name]["power"] = 0
        h_dict[self.component_name]["soc"] = self.SOC

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
                - power: Actual power in kW (positive is charging).
                - soc: State of charge (0-1).
        """
        power_setpoint = h_dict[self.component_name]["power_setpoint"]
        if np.isnan(power_setpoint):
            raise ValueError(f"{self.component_name}: power_setpoint is NaN")

        if self.allow_grid_power_consumption:
            P_avail = np.inf
        else:
            P_avail = h_dict["plant"]["locally_generated_power"]  # [kW]

        hours = self.dt / 3600
        E_decayed = self.E * self.decay  # [kWh]

        # Charge and discharge limits [kW]
        P_hi = min(
            self.charge_rate,
            P_avail,
            (self.E_max - E_decayed) / (hours * self.roundtrip_efficiency),
        )
        P_lo = max(-self.discharge_rate, (self.E_min - E_decayed) / hours)
        P = min(max(power_setpoint, min(P_lo, 0.0)), max(P_hi, 0.0))

        self.E = E_decayed + (self.roundtrip_efficiency * P if P > 0 else P) * hours
        self.SOC = self.E / self.energy_capacity
        self.power_kw = P

        h_dict[self.component_name]["power"] = self.power_kw
        h_dict[self.component_name]["soc"] = self.SOC

        return h_dict
