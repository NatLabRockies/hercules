"""Tests for hercules.analysis.regions (region YAML loading and MISO rules)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from hercules.analysis.regions import load_region, miso

from tests.test_inputs.analysis_output import build_hercules_output

H_DICT = {
    "plant": {"interconnect_limit": 100.0},
    "solar": {"component_type": "SolarPySAMPVWatts", "capacity_rated": 150.0},
    "battery": {"component_type": "BatteryReservoir", "power_discharge_max": 50.0},
}


def test_load_region_by_name_and_path(tmp_path):
    # The built-in MISO file loads by name; an edited copy loads by path.
    region = load_region("miso")
    assert region["zones"][8]["subregion"] == "south"
    assert region["capacity_price_USD_per_MW_day"][2026][8]["summer"] == 384.10
    assert all(Path(f).is_file() for f in region["data_files"].values())

    region["capacity_price_USD_per_MW_day"][2026][8]["summer"] = 1.0
    region["data_files"] = {}
    path = tmp_path / "my_miso.yaml"
    path.write_text(yaml.safe_dump(region))
    assert load_region(str(path))["capacity_price_USD_per_MW_day"][2026][8]["summer"] == 1.0

    with pytest.raises(FileNotFoundError):
        load_region("not_a_region")


def test_miso_is_peak_column(tmp_path):
    # Zone 8 (peak zone LRZ8_9_10) has a daily peak at 2023-09-01 21:00 UTC, which starts a
    # 4 h block; hourly rows from 20:00 are flagged 21:00 through 00:00.
    start = pd.Timestamp("2023-09-01T20:00Z").timestamp()
    ho = build_hercules_output(
        tmp_path, {"solar.power": [0.0] * 6}, H_DICT, dt=3600.0, starttime_utc=start
    )
    miso.add_is_peak_column(ho, zone=8)
    np.testing.assert_array_equal(ho.df["analysis.is_peak"], [0, 1, 1, 1, 1, 0])


def test_miso_RA_hour_columns(tmp_path):
    # 2023-06-19 20:00 UTC is a summer RA hour in the south subregion only.
    start = pd.Timestamp("2023-06-19T20:00Z").timestamp()
    ho = build_hercules_output(tmp_path, {"solar.power": [0.0]}, H_DICT, starttime_utc=start)
    miso.add_RA_hour_columns(ho, zone=8)
    assert ho.df["analysis.RA_hour"][0] == 1
    assert ho.df["analysis.season"][0] == "summer"
    miso.add_RA_hour_columns(ho, zone=1)
    assert ho.df["analysis.RA_hour"][0] == 0


def test_miso_shared_POI_accreditation(tmp_path):
    # One summer RA hour: 80 kW of solar behind a 100 kW POI with a 50 kW battery served
    # first, so solar keeps min(80, 100 - 50) / min(80, 100) = 0.625 of its summer value.
    # The battery and the other seasons keep the class-level value.
    start = pd.Timestamp("2023-06-19T20:00Z").timestamp()
    columns = {"solar.power_hypothetical": [80.0], "controller.battery.offer_RT": [20.0]}
    ho = build_hercules_output(tmp_path, columns, H_DICT, starttime_utc=start)
    region = load_region("miso")
    fractions = region["accreditation_fraction"]

    solar = miso.compute_capacity_accredited_seasonal_MW(ho, 8, "solar")
    assert solar["summer"] == pytest.approx(fractions["solar"]["summer"] * 0.1 * 0.625)
    assert solar["winter"] == pytest.approx(fractions["solar"]["winter"] * 0.1)
    battery = miso.compute_capacity_accredited_seasonal_MW(ho, 8, "battery")
    assert battery["summer"] == pytest.approx(fractions["battery"]["summer"] * 0.05)

    # With the battery's logged availability (20 kW) the 80 kW of solar fits under the POI.
    solar = miso.compute_capacity_accredited_seasonal_MW(
        ho, 8, "solar", storage_available_columns={"battery": "controller.battery.offer_RT"}
    )
    assert solar["summer"] == pytest.approx(fractions["solar"]["summer"] * 0.1)
