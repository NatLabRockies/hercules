"""Accredited capacity and capacity market outcomes.

Region-agnostic: region data (accreditation fractions, capacity prices, seasons) is passed in
as a dict from ``regions.load_region``. Region-specific rules (e.g. MISO's hourly availability
at a shared POI) live in the region modules and can pass their seasonal accreditation in.
"""

import calendar

from hercules.hercules_output import HerculesOutput

_RESOURCE_CLASS = {
    "SolarPySAMPVWatts": "solar",
    "WindFarm": "wind",
    "WindFarmSCADAPower": "wind",
    "BatteryDynamic": "battery",
    "BatteryReservoir": "battery",
    "BatteryLithiumIon": "battery",
}


def _lookup(table: dict, key, what: str):
    """Return ``table[key]`` or raise a ValueError listing the available keys."""
    if key not in table:
        raise ValueError(f"Unknown {what} '{key}'. Available: {sorted(table)}")
    return table[key]


def _resource_class(ho: HerculesOutput, component: str) -> str:
    """Return the accreditation resource class of a component (e.g. ``"solar"``)."""
    component_type = ho.metadata["h_dict"][component]["component_type"]
    return _lookup(_RESOURCE_CLASS, component_type, "component type for accreditation")


def _rating_kW(ho: HerculesOutput, component: str) -> float:
    """Return a component's rated AC power (kW), capped at the interconnect limit."""
    h_dict = ho.metadata["h_dict"]
    config = h_dict[component]
    rating = config.get("capacity_rated", config.get("power_discharge_max"))
    if rating is None:
        raise ValueError(f"No capacity_rated or power_discharge_max for '{component}'.")
    return min(float(rating), float(h_dict["plant"]["interconnect_limit"]))


def _days_per_season(region: dict, year: int) -> dict[str, int]:
    """Return the number of days in each season of ``year`` (February of ``year``)."""
    return {
        season: sum(calendar.monthrange(year, month)[1] for month in months)
        for season, months in region["seasons"].items()
    }


def _price_year(region: dict, year: int | None) -> int:
    """Return ``year``, or the latest year in the region's capacity prices."""
    return max(region["capacity_price_USD_per_MW_day"]) if year is None else year


def compute_capacity_accredited_seasonal_MW(
    ho: HerculesOutput,
    region: dict,
    component: str,
    resource_class: str | None = None,
) -> dict[str, float]:
    """Return a component's accredited capacity by season (MW).

    Accredited capacity is the region's seasonal accreditation fraction for the resource
    class times the component's rated AC power, capped at the interconnect limit.

    Args:
        ho (HerculesOutput): Hercules output.
        region (dict): Region data from ``regions.load_region``.
        component (str): Component name.
        resource_class (str | None): Accreditation class (e.g. ``"solar"``). Defaults to
            None, which maps the component type.

    Returns:
        dict[str, float]: Accredited capacity (MW) by season.
    """
    resource_class = resource_class or _resource_class(ho, component)
    fractions = _lookup(region["accreditation_fraction"], resource_class, "resource class")
    rating_MW = _rating_kW(ho, component) / 1000.0
    return {season: fractions[season] * rating_MW for season in region["seasons"]}


def compute_capacity_accredited_MW(
    ho: HerculesOutput,
    region: dict,
    component: str,
    year: int | None = None,
    accredited_seasonal_MW: dict[str, float] | None = None,
) -> float:
    """Return the day-weighted mean of a component's seasonal accredited capacity (MW).

    Args:
        ho (HerculesOutput): Hercules output.
        region (dict): Region data from ``regions.load_region``.
        component (str): Component name.
        year (int | None): Year for the season day counts. Defaults to the latest capacity
            price year.
        accredited_seasonal_MW (dict[str, float] | None): Seasonal accredited capacity (MW),
            e.g. from a region module. Defaults to
            ``compute_capacity_accredited_seasonal_MW``.

    Returns:
        float: Annual accredited capacity (MW).
    """
    if accredited_seasonal_MW is None:
        accredited_seasonal_MW = compute_capacity_accredited_seasonal_MW(ho, region, component)
    days = _days_per_season(region, _price_year(region, year))
    total = sum(accredited_seasonal_MW[season] * days[season] for season in days)
    return total / sum(days.values())


def compute_revenue_capacity_annual(
    ho: HerculesOutput,
    region: dict,
    zone,
    component: str,
    year: int | None = None,
    accredited_seasonal_MW: dict[str, float] | None = None,
) -> float:
    """Return annual capacity revenue: accredited MW x price ($/MW-day) x days, summed over seasons.

    Args:
        ho (HerculesOutput): Hercules output.
        region (dict): Region data from ``regions.load_region``.
        zone: Zone key in the region's capacity prices (e.g. MISO local resource zone 8).
        component (str): Component name.
        year (int | None): Capacity price year. Defaults to the latest available.
        accredited_seasonal_MW (dict[str, float] | None): Seasonal accredited capacity (MW),
            e.g. from a region module. Defaults to
            ``compute_capacity_accredited_seasonal_MW``.

    Returns:
        float: Annual capacity revenue ($).
    """
    year = _price_year(region, year)
    prices_by_zone = _lookup(region["capacity_price_USD_per_MW_day"], year, "price year")
    prices = _lookup(prices_by_zone, zone, "zone")
    if accredited_seasonal_MW is None:
        accredited_seasonal_MW = compute_capacity_accredited_seasonal_MW(ho, region, component)
    days = _days_per_season(region, year)
    return sum(accredited_seasonal_MW[s] * prices[s] * days[s] for s in days)
