"""Energy market revenue: real-time, day-ahead, two-settlement and TBX benchmarks.

Revenue uses POI-limited power. Offers and cleared amounts are read from logged columns,
never reconstructed.
"""

import math

import numpy as np
import pandas as pd

from hercules.analysis.utilities import (
    _annualize,
    _get_column,
    _require_default_index,
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


def _revenue_two_settlement(
    ho: HerculesOutput,
    power_column: str,
    power_cleared_DA_column: str,
    LMP_RT_column: str,
    LMP_DA_column: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Return per-step DA and RT revenue ($): cleared DA at the DA LMP, the rest at RT."""
    energy = compute_energy_MWh_column(ho, power_column).to_numpy()
    energy_DA = compute_energy_MWh_column(ho, power_cleared_DA_column).fillna(0.0).to_numpy()
    revenue_DA = energy_DA * _get_column(ho, LMP_DA_column)
    revenue_RT = (energy - energy_DA) * _get_column(ho, LMP_RT_column)
    return revenue_DA, revenue_RT


def add_revenue_two_settlement_columns(
    ho: HerculesOutput,
    power_column: str,
    power_cleared_DA_column: str,
    LMP_RT_column: str = "external_signals.LMP_RT",
    LMP_DA_column: str = "external_signals.LMP_DA",
) -> HerculesOutput:
    """Add per-step two-settlement DA and RT revenue columns ($).

    Cleared DA energy is paid at the DA LMP and the deviation (delivered minus cleared) at the
    RT LMP. Adds ``analysis.<name>_revenue_DA`` and ``analysis.<name>_revenue_RT``, where
    ``<name>`` is ``power_column`` without a leading ``analysis.``.

    Args:
        ho (HerculesOutput): Hercules output.
        power_column (str): Delivered power column (kW), e.g.
            ``analysis.battery.power_POI_limited``.
        power_cleared_DA_column (str): Logged cleared DA power column (kW), e.g.
            ``controller.battery.power_cleared_DA``. Missing values count as 0.
        LMP_RT_column (str): Real-time LMP column ($/MWh). Defaults to
            ``external_signals.LMP_RT``.
        LMP_DA_column (str): Day-ahead LMP column ($/MWh). Defaults to
            ``external_signals.LMP_DA``.

    Returns:
        HerculesOutput: ``ho`` with the revenue columns added.
    """
    revenue_DA, revenue_RT = _revenue_two_settlement(
        ho, power_column, power_cleared_DA_column, LMP_RT_column, LMP_DA_column
    )
    name = power_column.removeprefix("analysis.")
    ho.df[f"analysis.{name}_revenue_DA"] = revenue_DA
    ho.df[f"analysis.{name}_revenue_RT"] = revenue_RT
    return ho


def compute_revenue_two_settlement_total(
    ho: HerculesOutput,
    power_column: str,
    power_cleared_DA_column: str,
    LMP_RT_column: str = "external_signals.LMP_RT",
    LMP_DA_column: str = "external_signals.LMP_DA",
) -> tuple[float, float, float]:
    """Return two-settlement revenue over the simulation as ``(total, DA, RT)`` ($).

    Args:
        ho (HerculesOutput): Hercules output.
        power_column (str): Delivered power column (kW).
        power_cleared_DA_column (str): Logged cleared DA power column (kW).
        LMP_RT_column (str): Real-time LMP column ($/MWh). Defaults to
            ``external_signals.LMP_RT``.
        LMP_DA_column (str): Day-ahead LMP column ($/MWh). Defaults to
            ``external_signals.LMP_DA``.

    Returns:
        tuple[float, float, float]: Total, DA and RT revenue ($).
    """
    revenue_DA, revenue_RT = _revenue_two_settlement(
        ho, power_column, power_cleared_DA_column, LMP_RT_column, LMP_DA_column
    )
    DA, RT = float(revenue_DA.sum()), float(revenue_RT.sum())
    return DA + RT, DA, RT


def compute_revenue_two_settlement_annual(
    ho: HerculesOutput,
    power_column: str,
    power_cleared_DA_column: str,
    LMP_RT_column: str = "external_signals.LMP_RT",
    LMP_DA_column: str = "external_signals.LMP_DA",
    hours_per_year: float = HOURS_PER_YEAR,
) -> tuple[float, float, float]:
    """Return two-settlement revenue scaled to one year as ``(total, DA, RT)`` ($).

    Args:
        ho (HerculesOutput): Hercules output.
        power_column (str): Delivered power column (kW).
        power_cleared_DA_column (str): Logged cleared DA power column (kW).
        LMP_RT_column (str): Real-time LMP column ($/MWh). Defaults to
            ``external_signals.LMP_RT``.
        LMP_DA_column (str): Day-ahead LMP column ($/MWh). Defaults to
            ``external_signals.LMP_DA``.
        hours_per_year (float): Hours in a year. Defaults to 8760.

    Returns:
        tuple[float, float, float]: Annualized total, DA and RT revenue ($).
    """
    totals = compute_revenue_two_settlement_total(
        ho, power_column, power_cleared_DA_column, LMP_RT_column, LMP_DA_column
    )
    return tuple(_annualize(ho, value, hours_per_year) for value in totals)


def _TBX_daily_margin(
    prices: pd.Series,
    duration_hours: float,
    roundtrip_efficiency: float,
    allow_skip: bool,
    block_hours: float,
) -> pd.Series:
    """Return the perfect-foresight arbitrage margin per MW for each day ($/MW-day).

    Each day discharges the ``N = duration_hours / block_hours`` highest-priced blocks and
    charges the cheapest ``N / roundtrip_efficiency`` blocks (whole blocks plus a fraction of
    the next). Days without enough blocks are dropped; with ``allow_skip`` negative days
    earn 0.
    """
    n_discharge = round(duration_hours / block_hours)
    if n_discharge < 1 or not math.isclose(n_discharge * block_hours, duration_hours):
        raise ValueError("duration_hours must be a positive whole multiple of the block length.")
    n_charge = n_discharge / roundtrip_efficiency
    full = math.floor(n_charge)
    fraction = n_charge - full
    blocks_needed = n_discharge + full + (1 if fraction > 0 else 0)

    prices = prices.dropna()
    margins = {}
    for day, day_prices in prices.groupby(prices.index.normalize()):
        if len(day_prices) < blocks_needed:
            continue
        p = np.sort(day_prices.to_numpy())
        charge_cost = p[:full].sum() + (fraction * p[full] if fraction > 0 else 0.0)
        margins[day] = block_hours * (p[-n_discharge:].sum() - charge_cost)
    margin = pd.Series(margins, dtype=float)
    return margin.clip(lower=0.0) if allow_skip else margin


def compute_revenue_TBX_total(
    ho: HerculesOutput,
    power_rated: float,
    duration_hours: float = 4.0,
    roundtrip_efficiency: float = 1.0,
    allow_skip: bool = True,
    LMP_column: str = "external_signals.LMP_DA",
    block_minutes: int = 60,
    day_timezone: str | None = None,
) -> float:
    """Return the perfect-foresight TBX arbitrage benchmark over the simulation ($).

    Prices are averaged into blocks of ``block_minutes`` and grouped by calendar day. Each
    day a battery of ``power_rated`` discharges in the ``duration_hours`` most expensive
    blocks and charges in the cheapest ``duration_hours / roundtrip_efficiency`` hours; with
    ``roundtrip_efficiency = 1`` and hourly blocks this is the gross TBX spread of published
    indices (TB4 for 4 h). Independent of the simulated control.

    Args:
        ho (HerculesOutput): Hercules output.
        power_rated (float): Battery power rating (kW).
        duration_hours (float): Battery duration (h). Defaults to 4.
        roundtrip_efficiency (float): Round-trip efficiency in (0, 1]. Defaults to 1.
        allow_skip (bool): Days with a negative margin earn 0. Defaults to True.
        LMP_column (str): LMP column ($/MWh). Defaults to ``external_signals.LMP_DA``.
        block_minutes (int): Price block length (min); 60 for hourly TBX, 5 for sub-hourly
            RT. Defaults to 60.
        day_timezone (str | None): Time zone for calendar days (e.g. ``"US/Central"``).
            Defaults to None (UTC days).

    Returns:
        float: TBX revenue over the simulation ($).
    """
    _require_default_index(ho)
    times = pd.DatetimeIndex(ho.df["time_utc"])
    if day_timezone is not None:
        times = times.tz_convert(day_timezone)
    prices = pd.Series(_get_column(ho, LMP_column), index=times)
    block_prices = prices.resample(f"{block_minutes}min").mean()
    margin = _TBX_daily_margin(
        block_prices, duration_hours, roundtrip_efficiency, allow_skip, block_minutes / 60
    )
    return float(power_rated / 1000.0 * margin.sum())


def compute_revenue_TBX_annual(
    ho: HerculesOutput,
    power_rated: float,
    duration_hours: float = 4.0,
    roundtrip_efficiency: float = 1.0,
    allow_skip: bool = True,
    LMP_column: str = "external_signals.LMP_DA",
    block_minutes: int = 60,
    day_timezone: str | None = None,
    hours_per_year: float = HOURS_PER_YEAR,
) -> float:
    """Return the TBX arbitrage benchmark scaled to one year ($).

    Args:
        ho (HerculesOutput): Hercules output.
        power_rated (float): Battery power rating (kW).
        duration_hours (float): Battery duration (h). Defaults to 4.
        roundtrip_efficiency (float): Round-trip efficiency in (0, 1]. Defaults to 1.
        allow_skip (bool): Days with a negative margin earn 0. Defaults to True.
        LMP_column (str): LMP column ($/MWh). Defaults to ``external_signals.LMP_DA``.
        block_minutes (int): Price block length (min). Defaults to 60.
        day_timezone (str | None): Time zone for calendar days. Defaults to None (UTC).
        hours_per_year (float): Hours in a year. Defaults to 8760.

    Returns:
        float: Annualized TBX revenue ($).
    """
    total = compute_revenue_TBX_total(
        ho,
        power_rated,
        duration_hours,
        roundtrip_efficiency,
        allow_skip,
        LMP_column,
        block_minutes,
        day_timezone,
    )
    return _annualize(ho, total, hours_per_year)
