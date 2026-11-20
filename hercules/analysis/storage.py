"""Physical metrics of storage components: energy discharged, cycles and SOC statistics.

Uses the raw logged signals rather than POI-limited power, since the POI cut does not change
what the equipment did. Revenue belongs in ``energy_market``.
"""

import numpy as np

from hercules.analysis.utilities import (
    _annualize,
    _get_column,
    _require_default_index,
    compute_energy_MWh_column,
    HOURS_PER_YEAR,
)
from hercules.hercules_output import HerculesOutput


def compute_energy_discharged_total_MWh(ho: HerculesOutput, component: str = "battery") -> float:
    """Return the AC energy discharged over the simulation (MWh).

    Sums the positive part of ``<component>.power``.

    Args:
        ho (HerculesOutput): Hercules output.
        component (str): Storage component name. Defaults to ``"battery"``.

    Returns:
        float: Energy discharged in MWh.
    """
    return float(compute_energy_MWh_column(ho, f"{component}.power").clip(lower=0.0).sum())


def compute_energy_discharged_annual_MWh(
    ho: HerculesOutput,
    component: str = "battery",
    hours_per_year: float = HOURS_PER_YEAR,
) -> float:
    """Return the AC energy discharged, scaled to one year (MWh).

    Args:
        ho (HerculesOutput): Hercules output.
        component (str): Storage component name. Defaults to ``"battery"``.
        hours_per_year (float): Hours in a year. Defaults to 8760.

    Returns:
        float: Annualized energy discharged in MWh.
    """
    total = compute_energy_discharged_total_MWh(ho, component)
    return _annualize(ho, total, hours_per_year)


def compute_cycle_count_equivalent_total(ho: HerculesOutput, component: str = "battery") -> float:
    """Return equivalent full cycles: AC energy discharged / ``energy_capacity``.

    Args:
        ho (HerculesOutput): Hercules output.
        component (str): Storage component name. Defaults to ``"battery"``.

    Returns:
        float: Equivalent full cycles over the simulation.
    """
    energy_capacity_MWh = float(ho.metadata["h_dict"][component]["energy_capacity"]) / 1000.0
    return compute_energy_discharged_total_MWh(ho, component) / energy_capacity_MWh


def compute_cycle_count_equivalent_annual(
    ho: HerculesOutput,
    component: str = "battery",
    hours_per_year: float = HOURS_PER_YEAR,
) -> float:
    """Return equivalent full cycles (energy discharged / capacity), scaled to one year.

    Args:
        ho (HerculesOutput): Hercules output.
        component (str): Storage component name. Defaults to ``"battery"``.
        hours_per_year (float): Hours in a year. Defaults to 8760.

    Returns:
        float: Annualized equivalent full cycles.
    """
    total = compute_cycle_count_equivalent_total(ho, component)
    return _annualize(ho, total, hours_per_year)


def compute_cycle_count_equivalent_SOC_total(
    ho: HerculesOutput, component: str = "battery"
) -> float:
    """Return SOC-based equivalent full cycles: the sum of SOC decreases.

    Counts only discharge motion, so a trajectory 0 -> 1 -> 0 is one cycle. Unlike
    ``compute_cycle_count_equivalent_total`` it includes conversion losses and
    self-discharge.

    Args:
        ho (HerculesOutput): Hercules output.
        component (str): Storage component name. Defaults to ``"battery"``.

    Returns:
        float: SOC-based equivalent full cycles over the simulation.
    """
    _require_default_index(ho)
    SOC = _get_column(ho, f"{component}.SOC")
    return float(-np.minimum(np.diff(SOC), 0.0).sum())


def compute_cycle_count_equivalent_SOC_annual(
    ho: HerculesOutput,
    component: str = "battery",
    hours_per_year: float = HOURS_PER_YEAR,
) -> float:
    """Return SOC-based equivalent full cycles, scaled to one year.

    Args:
        ho (HerculesOutput): Hercules output.
        component (str): Storage component name. Defaults to ``"battery"``.
        hours_per_year (float): Hours in a year. Defaults to 8760.

    Returns:
        float: Annualized SOC-based equivalent full cycles.
    """
    total = compute_cycle_count_equivalent_SOC_total(ho, component)
    return _annualize(ho, total, hours_per_year)


def compute_SOC_mileage_total(ho: HerculesOutput, component: str = "battery") -> float:
    """Return the sum of absolute SOC changes (0 -> 1 -> 0 gives 2.0).

    Args:
        ho (HerculesOutput): Hercules output.
        component (str): Storage component name. Defaults to ``"battery"``.

    Returns:
        float: SOC mileage over the simulation (SOC fraction).
    """
    _require_default_index(ho)
    SOC = _get_column(ho, f"{component}.SOC")
    return float(np.abs(np.diff(SOC)).sum())


def compute_SOC_mileage_annual(
    ho: HerculesOutput,
    component: str = "battery",
    hours_per_year: float = HOURS_PER_YEAR,
) -> float:
    """Return the SOC mileage, scaled to one year.

    Args:
        ho (HerculesOutput): Hercules output.
        component (str): Storage component name. Defaults to ``"battery"``.
        hours_per_year (float): Hours in a year. Defaults to 8760.

    Returns:
        float: Annualized SOC mileage (SOC fraction).
    """
    return _annualize(ho, compute_SOC_mileage_total(ho, component), hours_per_year)


def compute_SOC_mean(ho: HerculesOutput, component: str = "battery") -> float:
    """Return the mean SOC over the simulation.

    Args:
        ho (HerculesOutput): Hercules output.
        component (str): Storage component name. Defaults to ``"battery"``.

    Returns:
        float: Mean SOC (fraction).
    """
    _require_default_index(ho)
    return float(_get_column(ho, f"{component}.SOC").mean())


def _rainflow_cycles(SOC: np.ndarray) -> list[tuple[float, float, float]]:
    """Rainflow-decompose an SOC series into ``(range, mean, count)`` cycles.

    ASTM E1049-85 four-point method on the turning points. Closed cycles count 1.0 and
    residual half-cycles 0.5.

    Args:
        SOC (np.ndarray): SOC values (fraction).

    Returns:
        list[tuple[float, float, float]]: Cycles as ``(range, mean, count)``.
    """
    x = np.asarray(SOC, dtype=float)
    if x.size >= 2:
        x = x[np.concatenate(([True], x[1:] != x[:-1]))]
    if x.size >= 3:
        d = np.sign(np.diff(x))
        x = x[np.concatenate(([True], d[:-1] != d[1:], [True]))]

    cycles = []
    stack = []
    for xi in x.tolist():
        stack.append(xi)
        while len(stack) >= 3:
            x_range = abs(stack[-1] - stack[-2])
            y_range = abs(stack[-2] - stack[-3])
            if x_range < y_range:
                break
            mean = 0.5 * (stack[-2] + stack[-3])
            if len(stack) == 3:
                cycles.append((y_range, mean, 0.5))
                stack.pop(0)
            else:
                cycles.append((y_range, mean, 1.0))
                del stack[-3:-1]
    for i in range(len(stack) - 1):
        cycles.append((abs(stack[i + 1] - stack[i]), 0.5 * (stack[i + 1] + stack[i]), 0.5))
    return cycles


def compute_rainflow_damage_total(
    ho: HerculesOutput,
    component: str = "battery",
    depth_exponent: float = 2.0,
) -> float:
    """Return rainflow cycle damage ``sum(count * depth ** depth_exponent)`` of the SOC.

    With ``depth_exponent = 2`` this is the cycle-depth stress form of Xu, Saxena and
    Kirschen (IEEE Trans. Smart Grid, 2018). Unitless, not calibrated to a chemistry.

    Args:
        ho (HerculesOutput): Hercules output.
        component (str): Storage component name. Defaults to ``"battery"``.
        depth_exponent (float): Exponent on cycle depth. Defaults to 2.0.

    Returns:
        float: Cycle damage over the simulation.
    """
    _require_default_index(ho)
    cycles = _rainflow_cycles(_get_column(ho, f"{component}.SOC"))
    return float(sum(count * depth**depth_exponent for depth, _, count in cycles))


def compute_rainflow_damage_annual(
    ho: HerculesOutput,
    component: str = "battery",
    depth_exponent: float = 2.0,
    hours_per_year: float = HOURS_PER_YEAR,
) -> float:
    """Return rainflow cycle damage, scaled to one year.

    Args:
        ho (HerculesOutput): Hercules output.
        component (str): Storage component name. Defaults to ``"battery"``.
        depth_exponent (float): Exponent on cycle depth. Defaults to 2.0.
        hours_per_year (float): Hours in a year. Defaults to 8760.

    Returns:
        float: Annualized cycle damage.
    """
    total = compute_rainflow_damage_total(ho, component, depth_exponent)
    return _annualize(ho, total, hours_per_year)
