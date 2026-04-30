"""Tests for the use_native_solar_dt path in SolarPySAMPVWatts.

These tests exercise the new feature added to ``SolarPySAMBase`` /
``SolarPySAMPVWatts`` that runs PySAM once on the native-resolution weather
grid (when coarser than the Hercules dt) and upsamples its outputs to the
Hercules grid. They verify:

1. Numerical agreement with the feature-off path for slowly-varying weather
   (the "approach 2" claim from the design discussion: i_to_i + a_to_i is
   numerically equivalent to the existing path in the linear-PVWatts limit).
2. The toggle correctly drives ``_compute_dt``.
3. The fallback path (``dt_solar == dt``) is a no-op.
"""

import numpy as np
import pandas as pd
import pytest
from hercules.plant_components.solar_pysam_pvwatts import SolarPySAMPVWatts


def _build_synthetic_solar_file(path, starttime_utc, endtime_utc, dt_seconds):
    """Write a synthetic solar feather file with slowly-varying weather.

    The weather is a smooth half-sine envelope so PVWatts is approximately
    linear over each native interval (this is what makes approach 2
    numerically agree with the existing path).

    Args:
        path (Path): Destination file path (feather format).
        starttime_utc (pd.Timestamp): UTC start time of the file.
        endtime_utc (pd.Timestamp): UTC end time the file must cover.
        dt_seconds (float): Native time-step of the synthetic file in seconds.

    Returns:
        pd.DataFrame: The written DataFrame (also persisted to ``path``).
    """
    duration = (endtime_utc - starttime_utc).total_seconds()
    n_rows = int(np.ceil(duration / dt_seconds)) + 1
    t = np.arange(n_rows) * dt_seconds
    time_utc = pd.date_range(
        start=starttime_utc, periods=n_rows, freq=f"{int(dt_seconds)}s", tz="UTC"
    )

    envelope = np.sin(np.pi * t / duration)
    ghi = 700.0 + 30.0 * envelope
    dni = 800.0 + 20.0 * envelope
    dhi = 100.0 + 10.0 * envelope
    temp = 25.0 + 0.5 * envelope
    wspd = 2.0 + 0.1 * envelope

    df = pd.DataFrame(
        {
            "time_utc": time_utc,
            "SRRL BMS Global Horizontal Irradiance (W/m^2_irr)": ghi.astype(np.float32),
            "SRRL BMS Direct Normal Irradiance (W/m^2_irr)": dni.astype(np.float32),
            "SRRL BMS Diffuse Horizontal Irradiance (W/m^2_irr)": dhi.astype(np.float32),
            "SRRL BMS Dry Bulb Temperature (C)": temp.astype(np.float32),
            "SRRL BMS Wind Speed at 19' (m/s)": wspd.astype(np.float32),
        }
    )
    df.to_feather(path)
    return df


def _build_h_dict(solar_input_filename, starttime_utc, endtime_utc, dt, use_native_solar_dt):
    """Build a minimal h_dict for instantiating SolarPySAMPVWatts.

    Args:
        solar_input_filename (Path or str): Path to the solar weather file.
        starttime_utc (pd.Timestamp): Simulation start (UTC).
        endtime_utc (pd.Timestamp): Simulation end (UTC).
        dt (float): Hercules time step in seconds.
        use_native_solar_dt (bool): Value of the new YAML toggle.

    Returns:
        dict: An h_dict suitable for ``SolarPySAMPVWatts`` construction.
    """
    endtime_seconds = (endtime_utc - starttime_utc).total_seconds()
    return {
        "dt": dt,
        "starttime": 0.0,
        "endtime": endtime_seconds,
        "starttime_utc": starttime_utc,
        "endtime_utc": endtime_utc,
        "verbose": False,
        "step": 0,
        "time": 0.0,
        "plant": {"interconnect_limit": 60000.0},
        "solar_farm": {
            "component_type": "SolarPySAMPVWatts",
            "solar_input_filename": str(solar_input_filename),
            "lat": 39.7442,
            "lon": -105.1778,
            "elev": 1829,
            "system_capacity": 30000.0,
            "tilt": 0,
            "losses": 0,
            "use_native_solar_dt": use_native_solar_dt,
            "log_channels": ["power"],
            "initial_conditions": {"power": 0.0, "dni": 0.0, "poa": 0.0},
        },
    }


def test_native_dt_matches_full_resolution_within_tolerance(tmp_path):
    """Approach 2 should agree closely with the feature-off path.

    With slowly-varying weather (linear-PVWatts limit), the PVWatts-once-at-
    native-dt + upsample path is numerically equivalent to the existing
    PVWatts-at-Hercules-dt path. The only residual difference comes from
    PVWatts' internal sun-position half-step shift moving from
    ``dt_hercules / 2`` to ``dt_compute / 2``, which is small for short
    sim windows away from sunrise/sunset.
    """
    starttime_utc = pd.to_datetime("2024-06-24T17:00:00Z")
    endtime_utc = pd.to_datetime("2024-06-24T17:10:00Z")
    dt = 1.0
    dt_native = 60.0

    solar_input = tmp_path / "solar_input.ftr"
    _build_synthetic_solar_file(solar_input, starttime_utc, endtime_utc, dt_native)

    h_dict_native = _build_h_dict(
        solar_input, starttime_utc, endtime_utc, dt, use_native_solar_dt=True
    )
    spv_native = SolarPySAMPVWatts(h_dict_native, "solar_farm")

    h_dict_full = _build_h_dict(
        solar_input, starttime_utc, endtime_utc, dt, use_native_solar_dt=False
    )
    spv_full = SolarPySAMPVWatts(h_dict_full, "solar_farm")

    assert spv_native._compute_dt == pytest.approx(dt_native)
    assert spv_full._compute_dt == pytest.approx(dt)

    expected_n = int((spv_native.endtime - spv_native.starttime) / dt)
    assert spv_native.ac_power_available_array.shape[0] == expected_n
    assert spv_full.ac_power_available_array.shape[0] == expected_n

    # Approach-2 numerical equivalence: AC and DC arrays match closely.
    # The atol absorbs float32 rounding and the small sun-position-half-step
    # bias on ~30 MW magnitudes.
    np.testing.assert_allclose(
        spv_native.ac_power_available_array,
        spv_full.ac_power_available_array,
        rtol=1e-3,
        atol=10.0,
    )
    np.testing.assert_allclose(
        spv_native.dc_power_available_array,
        spv_full.dc_power_available_array,
        rtol=1e-3,
        atol=10.0,
    )


def test_native_dt_is_no_op_when_dt_solar_equals_dt(tmp_path):
    """The fallback path should behave exactly like the pre-feature code.

    When the weather file's native dt equals the Hercules dt, ``_compute_dt``
    must collapse to ``dt`` and the compute grid must coincide with the
    Hercules grid; the upsample helper is then a no-op and outputs are
    indexed directly by Hercules step.
    """
    starttime_utc = pd.to_datetime("2024-06-24T17:00:00Z")
    endtime_utc = pd.to_datetime("2024-06-24T17:00:30Z")
    dt = 1.0
    dt_native = 1.0

    solar_input = tmp_path / "solar_input.ftr"
    _build_synthetic_solar_file(solar_input, starttime_utc, endtime_utc, dt_native)

    h_dict = _build_h_dict(solar_input, starttime_utc, endtime_utc, dt, use_native_solar_dt=True)
    spv = SolarPySAMPVWatts(h_dict, "solar_farm")

    assert spv._compute_dt == pytest.approx(dt)
    expected_n = int((spv.endtime - spv.starttime) / dt)
    assert spv.ac_power_available_array.shape[0] == expected_n
    assert spv._compute_time_steps is spv._hercules_time_steps


def test_use_native_solar_dt_false_forces_fallback(tmp_path):
    """Explicit opt-out forces the existing path even on coarse-native data.

    With ``use_native_solar_dt: False``, ``_compute_dt`` must equal ``dt``
    regardless of how coarse the input file is.
    """
    starttime_utc = pd.to_datetime("2024-06-24T17:00:00Z")
    endtime_utc = pd.to_datetime("2024-06-24T17:01:00Z")
    dt = 1.0
    dt_native = 60.0

    solar_input = tmp_path / "solar_input.ftr"
    _build_synthetic_solar_file(solar_input, starttime_utc, endtime_utc, dt_native)

    h_dict = _build_h_dict(solar_input, starttime_utc, endtime_utc, dt, use_native_solar_dt=False)
    spv = SolarPySAMPVWatts(h_dict, "solar_farm")

    assert spv._compute_dt == pytest.approx(dt)
    assert spv.dt_solar == pytest.approx(dt_native)


def test_native_dt_uses_native_timestamp_alignment_for_offset_start(tmp_path):
    """Native path should anchor compute stamps to weather-file boundaries.

    With an offset simulation start and coarse native weather timestamps, the
    compute grid should use the native stamp immediately before starttime and
    the native stamp at/after endtime (rather than start + n * dt_native).
    """
    file_start_utc = pd.to_datetime("2024-06-24T17:00:00Z")
    sim_start_utc = pd.to_datetime("2024-06-24T17:00:30Z")
    sim_end_utc = pd.to_datetime("2024-06-24T17:05:30Z")
    dt = 1.0
    dt_native = 60.0

    solar_input = tmp_path / "solar_input.ftr"
    _build_synthetic_solar_file(solar_input, file_start_utc, sim_end_utc, dt_native)

    h_dict_native = _build_h_dict(
        solar_input, sim_start_utc, sim_end_utc, dt, use_native_solar_dt=True
    )
    spv_native = SolarPySAMPVWatts(h_dict_native, "solar_farm")

    assert spv_native._compute_dt == pytest.approx(dt_native)
    assert spv_native._compute_time_steps[0] == pytest.approx(-30.0)
    assert spv_native._compute_time_steps[-1] == pytest.approx(330.0)
    np.testing.assert_allclose(np.diff(spv_native._compute_time_steps), dt_native)


def test_native_dt_matches_full_resolution_with_offset_start_within_tolerance(tmp_path):
    """Native path should still match feature-off path with offset start/end.

    This regression guards interval-alignment behavior when simulation start is
    not on the weather file's native reporting boundary.
    """
    file_start_utc = pd.to_datetime("2024-06-24T17:00:00Z")
    sim_start_utc = pd.to_datetime("2024-06-24T17:00:30Z")
    sim_end_utc = pd.to_datetime("2024-06-24T17:10:30Z")
    dt = 1.0
    dt_native = 60.0

    solar_input = tmp_path / "solar_input.ftr"
    _build_synthetic_solar_file(solar_input, file_start_utc, sim_end_utc, dt_native)

    h_dict_native = _build_h_dict(
        solar_input, sim_start_utc, sim_end_utc, dt, use_native_solar_dt=True
    )
    spv_native = SolarPySAMPVWatts(h_dict_native, "solar_farm")

    h_dict_full = _build_h_dict(
        solar_input, sim_start_utc, sim_end_utc, dt, use_native_solar_dt=False
    )
    spv_full = SolarPySAMPVWatts(h_dict_full, "solar_farm")

    expected_n = int((spv_native.endtime - spv_native.starttime) / dt)
    assert spv_native.ac_power_available_array.shape[0] == expected_n
    assert spv_full.ac_power_available_array.shape[0] == expected_n

    np.testing.assert_allclose(
        spv_native.ac_power_available_array,
        spv_full.ac_power_available_array,
        rtol=1e-3,
        atol=10.0,
    )
    np.testing.assert_allclose(
        spv_native.dc_power_available_array,
        spv_full.dc_power_available_array,
        rtol=1e-3,
        atol=10.0,
    )
