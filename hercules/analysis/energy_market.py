"""Energy market revenue: real-time, day-ahead, two-settlement and TBX benchmarks.

Revenue uses POI-limited power. Offers and cleared amounts are read from logged columns,
never reconstructed.
"""

from hercules.analysis.utilities import (
    _annualize,
    _get_column,
    compute_energy_MWh_column,
    HOURS_PER_YEAR,
    POWER_EXPORT_POI_LIMITED,
)
from hercules.hercules_output import HerculesOutput


def _compute_revenue_total(ho: HerculesOutput, power_column: str, LMP_column: str) -> float:
    """Return the sum of energy (MWh) times LMP ($/MWh) over all time steps ($)."""
    energy = compute_energy_MWh_column(ho, power_column).to_numpy()
    return float((energy * _get_column(ho, LMP_column)).sum())


def compute_revenue_RT_total(
    ho: HerculesOutput,
    power_column: str = POWER_EXPORT_POI_LIMITED,
    LMP_RT_column: str = "external_signals.LMP_RT",
) -> float:
    """Return revenue if all energy is settled at the real-time LMP ($).

    Negative power (charging) is charged at the same price.

    Args:
        ho (HerculesOutput): Hercules output.
        power_column (str): Power column (kW). Defaults to
            ``analysis.plant.power_export_POI_limited``.
        LMP_RT_column (str): Real-time LMP column ($/MWh). Defaults to
            ``external_signals.LMP_RT``.

    Returns:
        float: Real-time revenue over the simulation ($).
    """
    return _compute_revenue_total(ho, power_column, LMP_RT_column)


def compute_revenue_RT_annual(
    ho: HerculesOutput,
    power_column: str = POWER_EXPORT_POI_LIMITED,
    LMP_RT_column: str = "external_signals.LMP_RT",
    hours_per_year: float = HOURS_PER_YEAR,
) -> float:
    """Return real-time revenue scaled to one year ($).

    Args:
        ho (HerculesOutput): Hercules output.
        power_column (str): Power column (kW). Defaults to
            ``analysis.plant.power_export_POI_limited``.
        LMP_RT_column (str): Real-time LMP column ($/MWh). Defaults to
            ``external_signals.LMP_RT``.
        hours_per_year (float): Hours in a year. Defaults to 8760.

    Returns:
        float: Annualized real-time revenue ($).
    """
    total = compute_revenue_RT_total(ho, power_column, LMP_RT_column)
    return _annualize(ho, total, hours_per_year)


def compute_revenue_DA_total(
    ho: HerculesOutput,
    power_column: str = POWER_EXPORT_POI_LIMITED,
    LMP_DA_column: str = "external_signals.LMP_DA",
) -> float:
    """Return revenue if all energy is settled at the day-ahead LMP ($).

    Negative power (charging) is charged at the same price.

    Args:
        ho (HerculesOutput): Hercules output.
        power_column (str): Power column (kW). Defaults to
            ``analysis.plant.power_export_POI_limited``.
        LMP_DA_column (str): Day-ahead LMP column ($/MWh). Defaults to
            ``external_signals.LMP_DA``.

    Returns:
        float: Day-ahead revenue over the simulation ($).
    """
    return _compute_revenue_total(ho, power_column, LMP_DA_column)


def compute_revenue_DA_annual(
    ho: HerculesOutput,
    power_column: str = POWER_EXPORT_POI_LIMITED,
    LMP_DA_column: str = "external_signals.LMP_DA",
    hours_per_year: float = HOURS_PER_YEAR,
) -> float:
    """Return day-ahead revenue scaled to one year ($).

    Args:
        ho (HerculesOutput): Hercules output.
        power_column (str): Power column (kW). Defaults to
            ``analysis.plant.power_export_POI_limited``.
        LMP_DA_column (str): Day-ahead LMP column ($/MWh). Defaults to
            ``external_signals.LMP_DA``.
        hours_per_year (float): Hours in a year. Defaults to 8760.

    Returns:
        float: Annualized day-ahead revenue ($).
    """
    total = compute_revenue_DA_total(ho, power_column, LMP_DA_column)
    return _annualize(ho, total, hours_per_year)
