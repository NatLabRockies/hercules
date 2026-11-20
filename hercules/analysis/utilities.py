"""Shared post-processing utilities for a single Hercules simulation.

POI limiting (the first analysis step), index and column helpers, simulation time, energy
integration and capacity factor. Market- and region-specific logic belongs elsewhere.
"""

import warnings

import numpy as np
import pandas as pd

from hercules.hercules_output import HerculesOutput

HOURS_PER_YEAR = 8760
HOURS_PER_LEAP_YEAR = 8784

POWER_EXPORT_POI_LIMITED = "analysis.plant.power_export_POI_limited"
POWER_EXPORT_POI_EXCESS = "analysis.plant.power_export_POI_excess"


def _require_default_index(ho: HerculesOutput) -> None:
    """Raise if ``ho.df`` does not have the default ``RangeIndex(0, N)``.

    Analysis functions combine arrays taken from ``ho.df``; a filtered or reordered index
    would silently misalign them.

    Args:
        ho (HerculesOutput): Hercules output to check.

    Raises:
        ValueError: If ``ho.df.index`` is not ``RangeIndex(0, len(ho.df))``.
    """
    if not ho.df.index.equals(pd.RangeIndex(len(ho.df))):
        raise ValueError(
            "ho.df must have a default RangeIndex(0, N). Call "
            "ho.df.reset_index(drop=True) before passing ho to analysis functions."
        )


def _component_names(ho: HerculesOutput) -> list[str]:
    """Return the plant component names in the simulation's ``h_dict``."""
    h_dict = ho.metadata["h_dict"]
    return [key for key, val in h_dict.items() if isinstance(val, dict) and "component_type" in val]


def _dt_hours(ho: HerculesOutput) -> float:
    """Return the simulation time step in hours."""
    return float(ho.metadata["dt_sim"]) / 3600.0


def _get_column(ho: HerculesOutput, column: str) -> np.ndarray:
    """Return a column of ``ho.df`` as float64, adding POI-limited columns if requested.

    Args:
        ho (HerculesOutput): Hercules output.
        column (str): Column name.

    Returns:
        np.ndarray: Column values as float64.

    Raises:
        ValueError: If the column is not in ``ho.df``.
    """
    if column not in ho.df.columns and column.endswith("_POI_limited"):
        add_POI_limited_columns(ho)
    if column not in ho.df.columns:
        raise ValueError(f"Column '{column}' not found in ho.df.")
    return ho.df[column].to_numpy(dtype=np.float64)


def _annualize(ho: HerculesOutput, total: float, hours_per_year: float) -> float:
    """Scale a simulation-period total to ``hours_per_year``."""
    return total * hours_per_year / compute_simulation_hours(ho)


def _logged_curtailment_order(ho: HerculesOutput, components: list[str]) -> list[str]:
    """Return components sorted by a logged ``controller.*.curtailment_rank_<component>``.

    Hycon's ``HybridSupervisoryControllerGeneric`` logs these ranks (0 is curtailed first).
    Components without a logged rank are omitted.
    """
    ranks = {}
    for c in components:
        suffix = f".curtailment_rank_{c}"
        columns = [
            col for col in ho.df.columns if col.startswith("controller.") and col.endswith(suffix)
        ]
        if columns:
            values = ho.df[columns[0]].dropna()
            if not values.empty:
                ranks[c] = values.iloc[0]
    return sorted(ranks, key=ranks.get)


def add_POI_limited_columns(
    ho: HerculesOutput,
    curtailment_order: list[str] | None = None,
    warn_fraction: float = 1e-3,
) -> HerculesOutput:
    """Limit plant export to the interconnect limit and share the cut among components.

    Hercules lets ``plant.power_export`` exceed ``plant.interconnect_limit``; analysis
    assumes delivered power never does. The excess at the POI is converted to the bus with
    ``plant.efficiency_bus_to_poi`` and removed only from components with positive power
    (generators and discharging storage). Components in the curtailment order are cut
    first, in order (first entry cut first, as in Hycon's
    ``HybridSupervisoryControllerGeneric``). Any remaining cut is shared in proportion to
    each component's remaining positive power. Charging storage and loads are unchanged.

    Adds (in kW) ``analysis.plant.power_export_POI_limited``,
    ``analysis.plant.power_export_POI_excess`` and ``analysis.<component>.power_POI_limited``
    for every component. Calling again overwrites them.

    Args:
        ho (HerculesOutput): Hercules output; every component must have a logged ``power``.
        curtailment_order (list[str] | None): Component names in curtailment order.
            Defaults to None: the order logged by Hycon
            (``controller.*.curtailment_rank_<component>``) if present, else proportional
            only.
        warn_fraction (float): Warn when the energy removed exceeds this fraction of the
            exported energy. Defaults to 1e-3.

    Returns:
        HerculesOutput: ``ho`` with the POI-limited columns added.

    Raises:
        ValueError: If ``curtailment_order`` names an unknown component or a component
            ``power`` column is missing.
    """
    _require_default_index(ho)
    plant = ho.metadata["h_dict"]["plant"]
    limit = float(plant["interconnect_limit"])
    efficiency = float(plant.get("efficiency_bus_to_poi", 1.0))
    components = _component_names(ho)

    order = list(curtailment_order or [])
    if curtailment_order is None:
        order = _logged_curtailment_order(ho, components)
    unknown = sorted(set(order) - set(components))
    if unknown:
        raise ValueError(f"curtailment_order has unknown components {unknown}.")

    export = _get_column(ho, "plant.power_export")
    excess = np.maximum(export - limit, 0.0)
    cut = excess / efficiency
    power = {c: _get_column(ho, f"{c}.power").copy() for c in components}

    for c in order:
        cut_c = np.minimum(cut, np.maximum(power[c], 0.0))
        power[c] -= cut_c
        cut -= cut_c

    positive_total = np.zeros_like(export)
    for p in power.values():
        positive_total += np.maximum(p, 0.0)
    share = np.divide(cut, positive_total, out=np.zeros_like(cut), where=positive_total > 0)
    for c in components:
        power[c] -= np.maximum(power[c], 0.0) * share

    ho.df[POWER_EXPORT_POI_LIMITED] = export - excess
    ho.df[POWER_EXPORT_POI_EXCESS] = excess
    for c in components:
        ho.df[f"analysis.{c}.power_POI_limited"] = power[c]

    removed_MWh = excess.sum() * _dt_hours(ho) / 1000.0
    exported_MWh = np.maximum(export, 0.0).sum() * _dt_hours(ho) / 1000.0
    if removed_MWh > warn_fraction * exported_MWh:
        warnings.warn(
            f"POI limiting removed {removed_MWh:.3f} MWh of {exported_MWh:.3f} MWh exported "
            f"(max excess {excess.max():.1f} kW).",
            stacklevel=2,
        )
    return ho


def add_columns(
    ho: HerculesOutput,
    df_to_add: pd.DataFrame,
    column_subset: list[str] | None = None,
    allow_overwrite: bool = False,
) -> HerculesOutput:
    """Add columns from a DataFrame to ``ho.df``, checking that ``time_utc`` matches.

    Args:
        ho (HerculesOutput): Hercules output to modify.
        df_to_add (pd.DataFrame): Columns to add, with a ``time_utc`` column equal to
            ``ho.df["time_utc"]`` and the same index.
        column_subset (list[str] | None): Columns to add. Defaults to all except
            ``time_utc``.
        allow_overwrite (bool): Overwrite existing columns instead of raising. Defaults
            to False.

    Returns:
        HerculesOutput: ``ho`` with the columns added.

    Raises:
        ValueError: If ``time_utc`` or the index do not match, or a column exists and
            ``allow_overwrite`` is False.
    """
    _require_default_index(ho)
    if "time_utc" not in df_to_add.columns:
        raise ValueError("df_to_add must contain a 'time_utc' column.")
    if not df_to_add.index.equals(ho.df.index):
        raise ValueError(
            "df_to_add.index does not match ho.df.index. Call "
            "df_to_add.reset_index(drop=True) before calling add_columns."
        )
    if not df_to_add["time_utc"].equals(ho.df["time_utc"]):
        raise ValueError("time_utc values in df_to_add do not match ho.df.")

    if column_subset is None:
        column_subset = [col for col in df_to_add.columns if col != "time_utc"]
    existing = [col for col in column_subset if col in ho.df.columns]
    if existing and not allow_overwrite:
        raise ValueError(
            f"Columns {existing} already exist. Set allow_overwrite=True to overwrite."
        )
    for col in column_subset:
        ho.df[col] = df_to_add[col]
    return ho


def compute_simulation_hours(ho: HerculesOutput) -> float:
    """Return the simulated duration in hours.

    Args:
        ho (HerculesOutput): Hercules output.

    Returns:
        float: Simulated duration in hours.
    """
    return float(ho.metadata["total_simulation_time"]) / 3600.0


def compute_energy_MWh_column(
    ho: HerculesOutput,
    power_column: str = POWER_EXPORT_POI_LIMITED,
) -> pd.Series:
    """Return the energy in each time step (MWh) from a power column.

    Args:
        ho (HerculesOutput): Hercules output.
        power_column (str): Power column (kW). Defaults to
            ``analysis.plant.power_export_POI_limited``.

    Returns:
        pd.Series: Energy per time step in MWh.
    """
    _require_default_index(ho)
    power = _get_column(ho, power_column)
    return pd.Series(power * _dt_hours(ho) / 1000.0, index=ho.df.index)


def compute_energy_hourly_MWh_column(
    ho: HerculesOutput,
    power_column: str = POWER_EXPORT_POI_LIMITED,
) -> pd.Series:
    """Return the hourly mean of the per-step energy (MWh), held over each hour.

    The values are constant within each clock hour and sum to the same total as
    ``compute_energy_MWh_column`` when every hour is complete.

    Args:
        ho (HerculesOutput): Hercules output.
        power_column (str): Power column (kW). Defaults to
            ``analysis.plant.power_export_POI_limited``.

    Returns:
        pd.Series: Hourly mean energy per time step in MWh, indexed by ``time_utc``.

    Raises:
        ValueError: If ``time_utc`` is not monotonically increasing.
    """
    _require_default_index(ho)
    if not ho.df["time_utc"].is_monotonic_increasing:
        raise ValueError("ho.df['time_utc'] must be monotonically increasing.")
    energy = compute_energy_MWh_column(ho, power_column)
    energy.index = ho.df["time_utc"]
    return energy.resample("h").mean().reindex(energy.index, method="ffill")


def compute_energy_total_MWh(
    ho: HerculesOutput,
    power_column: str = POWER_EXPORT_POI_LIMITED,
) -> float:
    """Return the total energy over the simulation (MWh).

    Args:
        ho (HerculesOutput): Hercules output.
        power_column (str): Power column (kW). Defaults to
            ``analysis.plant.power_export_POI_limited``.

    Returns:
        float: Total energy in MWh.
    """
    return float(compute_energy_MWh_column(ho, power_column).sum())


def compute_energy_annual_MWh(
    ho: HerculesOutput,
    power_column: str = POWER_EXPORT_POI_LIMITED,
    hours_per_year: float = HOURS_PER_YEAR,
) -> float:
    """Return the total energy scaled to one year (MWh).

    Args:
        ho (HerculesOutput): Hercules output.
        power_column (str): Power column (kW). Defaults to
            ``analysis.plant.power_export_POI_limited``.
        hours_per_year (float): Hours in a year. Defaults to 8760.

    Returns:
        float: Annualized energy in MWh.
    """
    return _annualize(ho, compute_energy_total_MWh(ho, power_column), hours_per_year)


def compute_capacity_factor(
    ho: HerculesOutput,
    power_column: str = POWER_EXPORT_POI_LIMITED,
    capacity_rated: float | None = None,
) -> float:
    """Return the capacity factor of a power column.

    If ``capacity_rated`` is not given, it is taken from ``h_dict`` for the column's owner:
    ``plant.interconnect_limit`` for plant columns, else the component's
    ``capacity_rated`` or, for storage, ``power_discharge_max``.

    Args:
        ho (HerculesOutput): Hercules output.
        power_column (str): Power column (kW). Defaults to
            ``analysis.plant.power_export_POI_limited``.
        capacity_rated (float | None): Rated power in kW. Defaults to None.

    Returns:
        float: Capacity factor (fraction).

    Raises:
        ValueError: If ``capacity_rated`` is not given and no rating is found.
    """
    if capacity_rated is None:
        owner = power_column.removeprefix("analysis.").split(".")[0]
        config = ho.metadata["h_dict"].get(owner, {})
        if owner == "plant":
            capacity_rated = config["interconnect_limit"]
        elif "capacity_rated" in config:
            capacity_rated = config["capacity_rated"]
        elif "power_discharge_max" in config:
            capacity_rated = config["power_discharge_max"]
        else:
            raise ValueError(f"No rating found for '{power_column}'; pass capacity_rated.")
    hours = compute_simulation_hours(ho)
    return compute_energy_total_MWh(ho, power_column) / (float(capacity_rated) * hours / 1000.0)
