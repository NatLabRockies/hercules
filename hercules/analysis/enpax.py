"""Hand-off of one Hercules simulation to the ENPAX cost and ProFAST finance workflow.

Builds the case block (``plant`` and ``components``) from POI-limited energy, revenue and
component ratings. Collating cases and sites happens outside Hercules. Does not import
``enpax``.
"""

import yaml

from hercules.analysis import capacity_market, energy_market, storage, utilities
from hercules.analysis.regions import miso
from hercules.hercules_output import HerculesOutput

_ENPAX_TYPE = {
    "SolarPySAMPVWatts": "solar",
    "BatteryDynamic": "battery",
    "BatteryReservoir": "battery",
    "BatteryLithiumIon": "battery",
}


def build_enpax_case(
    ho: HerculesOutput,
    region: dict,
    zone,
    price_year: int | None = None,
    storage_available_columns: dict[str, str] | None = None,
    hours_per_year: float = utilities.HOURS_PER_YEAR,
) -> dict:
    """Return the ENPAX case block ``{plant, components}`` for one simulation.

    Energy and energy revenue use POI-limited power. Energy revenue is two-settlement,
    using ``controller.<component>.power_cleared_DA`` when logged (otherwise all energy settles
    at the RT LMP). Accredited capacity follows the region's rules (MISO: hourly availability
    capped at the shared POI) and capacity revenue uses the ``price_year`` capacity prices.
    Field names follow ``docs/nomenclature.md``; values not available are None.

    Args:
        ho (HerculesOutput): Hercules output.
        region (dict): Region data from ``regions.load_region``.
        zone: Zone key in the region's data (e.g. MISO local resource zone 8).
        price_year (int | None): Price base year, also used for capacity prices. Defaults to
            the latest capacity price year.
        storage_available_columns (dict[str, str] | None): Passed to MISO accreditation.
            Defaults to None (rated discharge power).
        hours_per_year (float): Hours in a year. Defaults to 8760.

    Returns:
        dict: Case block with ``plant`` and ``components`` (one entry per component).

    Raises:
        ValueError: If a component type has no ENPAX type.
    """
    utilities._require_default_index(ho)
    h_dict = ho.metadata["h_dict"]
    price_year = capacity_market._price_year(region, price_year)
    case = {
        "plant": {
            "interconnect_limit_MW": float(h_dict["plant"]["interconnect_limit"]) / 1000.0,
            "energy_annual_MWh": utilities.compute_energy_annual_MWh(
                ho, hours_per_year=hours_per_year
            ),
            "price_year": int(price_year),
        },
        "components": {},
    }

    for c in utilities._component_names(ho):
        config = h_dict[c]
        enpax_type = capacity_market._lookup(
            _ENPAX_TYPE, config["component_type"], "component type for ENPAX"
        )
        power = f"analysis.{c}.power_POI_limited"
        cleared = f"controller.{c}.power_cleared_DA"
        if cleared in ho.df.columns:
            revenue_energy = energy_market.compute_revenue_two_settlement_annual(
                ho, power, cleared, hours_per_year=hours_per_year
            )[0]
        else:
            revenue_energy = energy_market.compute_revenue_RT_annual(
                ho, power, hours_per_year=hours_per_year
            )
        if region["name"] == "MISO":
            seasonal = miso.compute_capacity_accredited_seasonal_MW(
                ho, zone, c, region, storage_available_columns
            )
        else:
            seasonal = capacity_market.compute_capacity_accredited_seasonal_MW(ho, region, c)

        block = {"type": enpax_type}
        if enpax_type == "solar":
            block["DC_capacity_rated_MW"] = float(config["DC_capacity_rated"]) / 1000.0
            block["capacity_rated_MW"] = float(config["capacity_rated"]) / 1000.0
            block["energy_annual_MWh"] = utilities.compute_energy_annual_MWh(
                ho, power, hours_per_year
            )
        else:
            power_rated = float(config["power_discharge_max"])
            block["DC_capacity_rated_MW"] = None
            block["capacity_rated_MW"] = power_rated / 1000.0
            block["energy_capacity_MWh"] = float(config["energy_capacity"]) / 1000.0
            block["duration_hours"] = float(config["energy_capacity"]) / power_rated
            block["energy_discharged_annual_MWh"] = storage.compute_energy_discharged_annual_MWh(
                ho, c, hours_per_year
            )
            block["cycle_count_equivalent_annual"] = storage.compute_cycle_count_equivalent_annual(
                ho, c, hours_per_year
            )
        block["revenue_energy_annual_USD"] = float(revenue_energy)
        block["revenue_capacity_annual_USD"] = float(
            capacity_market.compute_revenue_capacity_annual(
                ho, region, zone, c, price_year, seasonal
            )
        )
        block["capacity_accredited_MW"] = float(
            capacity_market.compute_capacity_accredited_MW(ho, region, c, price_year, seasonal)
        )
        case["components"][c] = block
    return case


def write_enpax_case_yaml(ho: HerculesOutput, filename: str, region: dict, zone, **kwargs) -> dict:
    """Write the ENPAX case block of one simulation to a YAML file.

    Args:
        ho (HerculesOutput): Hercules output.
        filename (str): YAML file to write.
        region (dict): Region data from ``regions.load_region``.
        zone: Zone key in the region's data.
        **kwargs: Passed to ``build_enpax_case``.

    Returns:
        dict: The case block written.
    """
    case = build_enpax_case(ho, region, zone, **kwargs)
    with open(filename, "w") as f:
        yaml.safe_dump(case, f, sort_keys=False)
    return case
