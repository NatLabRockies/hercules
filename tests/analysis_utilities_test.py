"""Tests for hercules.analysis.utilities."""

import numpy as np
import pandas as pd
import pytest
from hercules.analysis import utilities

from tests.test_inputs.analysis_output import build_hercules_output

SOLAR = {"component_type": "SolarPySAMPVWatts", "capacity_rated": 150.0}
BATTERY = {"component_type": "BatteryReservoir", "energy_capacity": 200.0}


def test_POI_limit_no_excess_leaves_power_unchanged(tmp_path):
    # Below the 100 kW limit the limited columns equal the logged ones.
    ho = build_hercules_output(
        tmp_path,
        {"solar.power": [50.0, 80.0]},
        {"plant": {"interconnect_limit": 100.0}, "solar": SOLAR},
    )
    utilities.add_POI_limited_columns(ho)
    np.testing.assert_allclose(ho.df["analysis.plant.power_export_POI_limited"], [50.0, 80.0])
    np.testing.assert_allclose(ho.df["analysis.plant.power_export_POI_excess"], [0.0, 0.0])
    np.testing.assert_allclose(ho.df["analysis.solar.power_POI_limited"], [50.0, 80.0])


def test_POI_limit_single_generator_warns(tmp_path):
    # 20 kW over the limit is removed from the only generator, and the excess is reported.
    ho = build_hercules_output(
        tmp_path,
        {"solar.power": [120.0, 90.0]},
        {"plant": {"interconnect_limit": 100.0}, "solar": SOLAR},
    )
    with pytest.warns(UserWarning, match="POI limiting removed"):
        utilities.add_POI_limited_columns(ho)
    np.testing.assert_allclose(ho.df["analysis.plant.power_export_POI_limited"], [100.0, 90.0])
    np.testing.assert_allclose(ho.df["analysis.plant.power_export_POI_excess"], [20.0, 0.0])
    np.testing.assert_allclose(ho.df["analysis.solar.power_POI_limited"], [100.0, 90.0])


def test_POI_limit_proportional_split(tmp_path):
    # 90 kW solar + 30 kW battery discharge, 20 kW cut shared 3:1.
    ho = build_hercules_output(
        tmp_path,
        {"solar.power": [90.0], "battery.power": [30.0]},
        {"plant": {"interconnect_limit": 100.0}, "solar": SOLAR, "battery": BATTERY},
    )
    utilities.add_POI_limited_columns(ho, warn_fraction=1.0)
    np.testing.assert_allclose(ho.df["analysis.solar.power_POI_limited"], [75.0])
    np.testing.assert_allclose(ho.df["analysis.battery.power_POI_limited"], [25.0])


def test_POI_limit_curtailment_order(tmp_path):
    # The battery is first in the order, so it takes the whole 20 kW cut.
    ho = build_hercules_output(
        tmp_path,
        {"solar.power": [90.0], "battery.power": [30.0]},
        {"plant": {"interconnect_limit": 100.0}, "solar": SOLAR, "battery": BATTERY},
    )
    utilities.add_POI_limited_columns(ho, curtailment_order=["battery"], warn_fraction=1.0)
    np.testing.assert_allclose(ho.df["analysis.solar.power_POI_limited"], [90.0])
    np.testing.assert_allclose(ho.df["analysis.battery.power_POI_limited"], [10.0])


def test_POI_limit_charging_storage_unchanged(tmp_path):
    # A charging battery is not cut; the 10 kW excess comes from solar.
    ho = build_hercules_output(
        tmp_path,
        {"solar.power": [130.0], "battery.power": [-20.0]},
        {"plant": {"interconnect_limit": 100.0}, "solar": SOLAR, "battery": BATTERY},
    )
    utilities.add_POI_limited_columns(ho, warn_fraction=1.0)
    np.testing.assert_allclose(ho.df["analysis.solar.power_POI_limited"], [120.0])
    np.testing.assert_allclose(ho.df["analysis.battery.power_POI_limited"], [-20.0])


def test_POI_limit_bus_to_POI_efficiency(tmp_path):
    # 150 kW at the bus exports 120 kW at 0.8 efficiency; removing 20 kW at the POI
    # takes 25 kW from the bus.
    plant = {"interconnect_limit": 100.0, "efficiency_bus_to_poi": 0.8}
    ho = build_hercules_output(tmp_path, {"solar.power": [150.0]}, {"plant": plant, "solar": SOLAR})
    utilities.add_POI_limited_columns(ho, warn_fraction=1.0)
    np.testing.assert_allclose(ho.df["analysis.plant.power_export_POI_limited"], [100.0])
    np.testing.assert_allclose(ho.df["analysis.solar.power_POI_limited"], [125.0])


def test_POI_limit_unknown_component_in_order_raises(tmp_path):
    # Names in curtailment_order must be components.
    ho = build_hercules_output(
        tmp_path,
        {"solar.power": [50.0]},
        {"plant": {"interconnect_limit": 100.0}, "solar": SOLAR},
    )
    with pytest.raises(ValueError, match="unknown components"):
        utilities.add_POI_limited_columns(ho, curtailment_order=["wind_farm"])


def test_energy_defaults_to_POI_limited_export(tmp_path):
    # Energy totals add the POI-limited columns when missing: 100 + 90 kW for 1 h each.
    ho = build_hercules_output(
        tmp_path,
        {"solar.power": [120.0, 90.0]},
        {"plant": {"interconnect_limit": 100.0}, "solar": SOLAR},
        dt=3600.0,
    )
    with pytest.warns(UserWarning):
        assert utilities.compute_energy_total_MWh(ho) == pytest.approx(0.19)
    assert "analysis.solar.power_POI_limited" in ho.df.columns


def test_energy_total_annual_and_simulation_hours(tmp_path):
    # 1000 kW then 3000 kW for 1 h each: 4 MWh over 2 h, 17520 MWh per year.
    ho = build_hercules_output(
        tmp_path,
        {"solar.power": [1000.0, 3000.0]},
        {"plant": {"interconnect_limit": 5000.0}, "solar": SOLAR},
        dt=3600.0,
    )
    assert utilities.compute_simulation_hours(ho) == pytest.approx(2.0)
    np.testing.assert_allclose(utilities.compute_energy_MWh_column(ho, "solar.power"), [1, 3])
    assert utilities.compute_energy_total_MWh(ho, "solar.power") == pytest.approx(4.0)
    assert utilities.compute_energy_annual_MWh(ho, "solar.power") == pytest.approx(17520.0)


def test_energy_hourly_column(tmp_path):
    # Half-hour steps of 0.5, 0.5, 1.5, 1.5 MWh average to 0.5 and 1.5 per hour.
    ho = build_hercules_output(
        tmp_path,
        {"solar.power": [1000.0, 1000.0, 3000.0, 3000.0]},
        {"plant": {"interconnect_limit": 5000.0}, "solar": SOLAR},
        dt=1800.0,
    )
    hourly = utilities.compute_energy_hourly_MWh_column(ho, "solar.power")
    np.testing.assert_allclose(hourly, [0.5, 0.5, 1.5, 1.5])


def test_capacity_factor_ratings(tmp_path):
    # Solar averages 75 kW: CF 0.5 of its 150 kW rating and 0.75 of the 100 kW plant limit.
    ho = build_hercules_output(
        tmp_path,
        {"solar.power": [50.0, 100.0]},
        {"plant": {"interconnect_limit": 100.0}, "solar": SOLAR},
    )
    assert utilities.compute_capacity_factor(ho, "solar.power") == pytest.approx(0.5)
    assert utilities.compute_capacity_factor(ho) == pytest.approx(0.75)
    assert utilities.compute_capacity_factor(ho, "solar.power", 300.0) == pytest.approx(0.25)
    ho.metadata["h_dict"]["solar"].pop("capacity_rated")
    with pytest.raises(ValueError, match="pass capacity_rated"):
        utilities.compute_capacity_factor(ho, "solar.power")


def test_non_default_index_raises(tmp_path):
    # A reordered index would misalign columns, so it is rejected.
    ho = build_hercules_output(
        tmp_path,
        {"solar.power": [50.0, 80.0]},
        {"plant": {"interconnect_limit": 100.0}, "solar": SOLAR},
    )
    ho.df = ho.df.iloc[::-1]
    with pytest.raises(ValueError, match="RangeIndex"):
        utilities.compute_energy_total_MWh(ho, "solar.power")


def test_add_columns_checks_time_and_overwrite(tmp_path):
    # Columns are added when time_utc matches; existing columns need allow_overwrite.
    ho = build_hercules_output(
        tmp_path,
        {"solar.power": [50.0, 80.0]},
        {"plant": {"interconnect_limit": 100.0}, "solar": SOLAR},
    )
    df = pd.DataFrame({"time_utc": ho.df["time_utc"].copy(), "analysis.flag": [0, 1]})
    utilities.add_columns(ho, df)
    np.testing.assert_array_equal(ho.df["analysis.flag"], [0, 1])
    with pytest.raises(ValueError, match="already exist"):
        utilities.add_columns(ho, df)
    df.loc[0, "time_utc"] = df["time_utc"].iloc[1]
    with pytest.raises(ValueError, match="do not match"):
        utilities.add_columns(ho, df, allow_overwrite=True)
