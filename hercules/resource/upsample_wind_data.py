"""
This module contains functions for generating wind time series at turbine locations by
a) spatially interpolating wind data at grid locations and
b) temporally upsampling the time series and adding turbulence.
"""

import os
from itertools import chain
from pathlib import Path

import numpy as np
import pandas as pd
import utm
from scipy.interpolate import CloughTocher2DInterpolator
from shapely.geometry import MultiPoint


def _spatially_interpolate_wind_data(
    x_locs_orig: np.ndarray,
    y_locs_orig: np.ndarray,
    wind_values: np.ndarray,
    x_locs_interp: np.ndarray,
    y_locs_interp: np.ndarray,
) -> np.ndarray:
    """Spatially interpolate wind data using 2D Clough-Tocher interpolation.

    Args:
        x_locs_orig (np.ndarray): x locations of points at which wind data are provided (meters).
        y_locs_orig (np.ndarray): y locations of points at which wind data are provided (meters).
        wind_values (np.ndarray): N x M array of wind variable values to spatially interpolate,
            where N is the number of time steps and M is the number of locations.
        x_locs_interp (np.ndarray): x locations for spatially interpolated wind time series
            (meters).
        y_locs_interp (np.ndarray): y locations for spatially interpolated wind time series
            (meters).

    Returns:
        np.ndarray: P x N array of spatially interpolated wind variable values, where P is the
            number of interpolated locations and N is the number of time steps.
    """

    N = len(wind_values)

    wind_interp_values = np.zeros((len(x_locs_interp), N))

    points = list(zip(x_locs_orig, y_locs_orig))

    # Interpolate for each time index
    for i in range(N):
        interp = CloughTocher2DInterpolator(points, wind_values[i, :])

        wind_interp_values[:, i] = interp(x_locs_interp, y_locs_interp)

    return wind_interp_values


def _upsample_Nyquist(
    base_values: np.ndarray, timestep_base: int, timestep_upsample: int = 1
) -> np.ndarray:
    """Upsample time series by adding frequency content up to the Nyquist frequency.

    Creates smoothly interpolated time series without adding higher frequency content.

    Args:
        base_values (np.ndarray): M x N array containing M time series of length N to be upsampled.
        timestep_base (int): Time step of the original data to be upsampled (seconds).
        timestep_upsample (int, optional): Time step of the new upsampled time series (seconds).
            This must be defined so that timestep_base is an integer multiple of timestep_upsample.
            Defaults to 1.

    Returns:
        np.ndarray: M x P array of M temporally upsampled time series of length P,
            where P = N * timestep_base / timestep_upsample.
    """

    up_factor = timestep_base // timestep_upsample

    num_points = np.size(base_values, 0)
    N = np.size(base_values, 1)

    upsampled_values = np.zeros((num_points, up_factor * N))

    for i in range(num_points):
        x = base_values[i, :]

        xf = np.fft.fft(x)
        xupf = up_factor * np.hstack(
            [
                xf[: N // 2],
                xf[N // 2] / 2,
                np.zeros((up_factor - 1) * N - 1),
                xf[N // 2] / 2,
                xf[-(N // 2 - 1) :],
            ]
        )

        upsampled_values[i, :] = np.real(np.fft.ifft(xupf))

    return upsampled_values


def _psd_kaimal(f: np.ndarray, Vhub: float, sigma: float = 1.0, L: float = 340.2):
    """Generate the Kaimal turbulence power spectral density.

    Args:
        f (np.ndarray): Array of frequencies for which the Kaimal PSD will be returned (Hz).
        Vhub (float): Hub height wind speed (m/s).
        sigma (float, optional): Wind speed standard deviation (m/s). Defaults to 1.
        L (float, optional): Turbulence length scale (m). Defaults to 340.2 m,
            the value specified in the IEC standard.

    Returns:
        np.ndarray: 1D array of power spectral density values.
    """
    return (sigma**2) * f * (L / Vhub) / ((1 + 6 * f * L / Vhub) ** (5 / 3))


def _generate_uncorrelated_kaimal_stochastic_turbulence(
    N_points: int,
    N_samples: int,
    timestep: int,
    turbulence_Uhub: float,
    turbulence_L: float = 340.2,
    ws_std: float = 1.0,
) -> np.ndarray:
    """Generate spatially uncorrelated zero-mean stochastic wind speed time series.

    Uses the Kaimal turbulence spectrum.

    Args:
        N_points (int): Number of turbulence time series to generate.
        N_samples (int): Number of samples in the turbulence time series.
            An even number of samples must be specified.
        timestep (int): Time step of the turbulence time series (seconds).
        turbulence_Uhub (float): Mean hub-height wind speed for the Kaimal turbulence
            spectrum (m/s).
        turbulence_L (float, optional): Turbulence length scale for the Kaimal turbulence
            spectrum (m). Defaults to 340.2 m, the value specified in the IEC standard.
        ws_std (float, optional): Standard deviation of the stochastic wind speed time series
            (m/s). Defaults to 1 m/s.

    Returns:
        np.ndarray: N_points x N_samples array of zero-mean stochastic wind speed turbulence
            time series.
    """

    fs = 1.0 / timestep  # Sampling frequency

    freqs = np.arange(0.0, 0.5 * fs + 0.5 * fs / N_samples, fs / N_samples)  # Frequency array

    freq_mat = np.zeros((N_points, N_samples), dtype=complex)  # Matrix of frequency components

    # Add phases for uncorrelated components
    freq_mat[:, 1 : int(N_samples / 2 + 1)] = np.exp(
        np.random.uniform(high=2 * np.pi, size=(N_points, int(N_samples / 2))) * 1.0j
    )

    # Simply add phase component of 1 for the Nyquist frequency
    freq_mat[:, int(N_samples / 2 + 1)] = np.ones(N_points)

    # Add magnitude of spectrum
    psd_1side = _psd_kaimal(freqs, turbulence_Uhub, ws_std, turbulence_L)

    freq_mat[:, 0 : int(N_samples / 2) + 1] *= np.tile(np.sqrt(psd_1side), (N_points, 1))

    # Copy phase information to negative frequencies
    freq_mat[:, int(N_samples / 2) + 1 :] = np.conj(np.fliplr(freq_mat[:, 1 : int(N_samples / 2)]))

    # Apply normalization to achieve desired std. dev.
    scale_const_total = ws_std * N_samples / np.sqrt(np.sum(np.abs(freq_mat[0, :]) ** 2))
    freq_mat *= scale_const_total

    # Perform ifft to get time series
    ws_mat = np.zeros((N_points, N_samples))

    for i in range(N_points):
        ws_mat[i, :] = np.real(np.fft.ifft(freq_mat[i, :]))

    return ws_mat


def _get_iec_turbulence_std(
    ws_array: np.ndarray, ws_ref: float, ti_ref: float, offset: float = 3.8
):
    """Generate wind speed standard deviations using the IEC 61400-1 normal turbulence model.

    First, the Iref parameter is defined to achieve the desired reference turbulence intensity
    at the provided reference wind speed. Next, this value of Iref is used to determine the
    wind speed standard deviation for all "mean" wind speeds in the provided ws_array.

    Args:
        ws_array (np.ndarray): Array of mean wind speeds for which corresponding wind speed
            standard deviations are computed (m/s).
        ws_ref (float): Reference wind speed at which the desired turbulence intensity is
            defined (m/s).
        ti_ref (float): Reference turbulence intensity corresponding to the reference wind speed.
        offset (float, optional): Offset value for IEC normal turbulence model equation.
            Defaults to 3.8, as defined in the IEC standard to give the expected value of TI
            for each wind speed.

    Returns:
        np.ndarray: Array of wind speed standard deviations corresponding to the mean wind speeds
            in ws_array.
    """

    Iref = ti_ref * ws_ref / (0.75 * ws_ref + 3.8)
    ws_std = Iref * (0.75 * ws_array + offset)
    return ws_std


def upsample_wind_data(
    ws_data_filepath: str | Path,
    wd_data_filepath: str | Path,
    coords_filepath: str | Path,
    upsampled_data_dir: str | Path,
    upsampled_data_filename: str,
    x_locs_upsample: np.ndarray,
    y_locs_upsample: np.ndarray,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
    timestep_upsample: int = 1,
    turbulence_Uhub: float | None = None,
    turbulence_L: float = 340.2,
    TI_ref: float = 0.1,
    TI_ws_ref: float = 8.0,
    save_individual_wds: bool = False,
) -> dict:
    """Spatially interpolate and temporally upsample wind speed and direction data.

    Processes wind files generated using wind data downloading functions in the
    wind_solar_resource_downloader module (e.g., for the Wind Toolkit or Open-Meteo datasets).
    Spatial interpolation is achieved using 2D Clough-Tocher interpolation. Upsampling is
    accomplished by simple Nyquist upsampling to create a smooth signal. Lastly, for the wind
    speeds, stochastic, uncorrelated turbulence generated using the Kaimal spectrum is added.
    The turbulence intensity is assigned as a function of wind speed based on the IEC normal
    turbulence model.

    Args:
        ws_data_filepath (str | Path): File path to the wind speed file.
        wd_data_filepath (str | Path): File path to the wind direction file.
        coords_filepath (str | Path): File path to the coordinates file.
        upsampled_data_dir (str | Path): Directory to save upsampled data files.
        upsampled_data_filename (str): Filename for upsampled output files.
        x_locs_upsample (np.ndarray): x locations for upsampled wind time series (meters).
        y_locs_upsample (np.ndarray): y locations for upsampled wind time series (meters).
        origin_lat (float | None, optional): Latitude for the origin for defining y locations of
            the upsample wind locations (degrees). If None, the mean latitude from the coordinates
            will be used. Defaults to None.
        origin_lon (float | None, optional): Longitude for the origin for defining x locations of
            the upsample wind locations (degrees). If None, the mean longitude from the coordinates
            will be used. Defaults to None.
        timestep_upsample (int, optional): Time step of upsampled wind time series (seconds).
            Defaults to 1 second.
        turbulence_Uhub (float | None, optional): Mean hub-height wind speed for the Kaimal
            turbulence spectrum (m/s). If None, the mean wind speed from the spatially interpolated
            upsample locations from the wind speed file will be used. Defaults to None.
        turbulence_L (float, optional): Turbulence length scale for the Kaimal turbulence
            spectrum (m). Defaults to 340.2 m, the value specified in the IEC standard.
        TI_ref (float, optional): Reference TI corresponding to the reference wind speed TI_ws_ref
            (fraction). Defaults to 0.1.
        TI_ws_ref (float, optional): Reference wind speed at which the reference TI TI_ref is
            defined (m/s). Defaults to 8 m/s.
        save_individual_wds (bool, optional): If True, upsampled wind directions will be saved
            in the output for each upsampled location. If False, only the mean wind direction
            over all locations will be saved. Defaults to False.

    Returns:
        pd.DataFrame: DataFrame containing the wind speeds and wind directions at each
            upsampled location.

    Note:
        The provided wind time series should have an even number of samples (this simplifies
        the FFT operations). If the time series have an odd number of samples, the last sample
        will be discarded.
    """

    # Create output directory if it doesn't exist
    os.makedirs(upsampled_data_dir, exist_ok=True)

    # Load wind files
    df_ws = pd.read_feather(ws_data_filepath)
    df_wd = pd.read_feather(wd_data_filepath)
    df_coords = pd.read_feather(coords_filepath)

    # Get mean lat and lon if needed
    if (origin_lat is None) | (origin_lon is None):
        origin_lat = df_coords["lat"].mean()
        origin_lon = df_coords["lon"].mean()

    # Convert coordinates to easting and northing values and center on origin
    x_locs_orig, y_locs_orig, zone_number, zone_letter = utm.from_latlon(
        df_coords["lat"].values, df_coords["lon"].values
    )

    origin_x, origin_y, origin_zone_number, origin_zone_letter = utm.from_latlon(
        origin_lat, origin_lon
    )

    if (zone_number != origin_zone_number) | (zone_letter != origin_zone_letter):
        raise ValueError(
            "The provided origin coordinates are in a different UTM zone than the provided wind "
            "data."
        )

    x_locs_orig -= origin_x
    y_locs_orig -= origin_y

    # Check if upsample locations are within the provided wind data boundaries
    multi_point_orig = MultiPoint(list(zip(x_locs_orig, y_locs_orig)))
    polygon_orig = multi_point_orig.convex_hull

    N_locs_upsample = len(x_locs_upsample)
    multi_point_upsample = MultiPoint(list(zip(x_locs_upsample, y_locs_upsample)))

    if not multi_point_upsample.within(polygon_orig):
        raise ValueError(
            "At least one of the provided upsampled locations is outside of the boundary of the "
            "provided wind data locations."
        )

    # If an odd number of samples in provided wind data, remove last sample
    if (len(df_ws) % 2) == 1:
        df_ws = df_ws.iloc[:-1]

    if (len(df_wd) % 2) == 1:
        df_wd = df_wd.iloc[:-1]

    # Ensure order of points in wind dataframe columns matches order in coordinate dataframe
    point_names = list(df_coords["index"].values.astype(str))
    df_ws = df_ws[["time_index"] + point_names]
    df_wd = df_wd[["time_index"] + point_names]

    # get time step of provided wind data and check if it is an integer multiple of upsampled time
    # step
    timestep_orig = int((df_ws.iloc[1]["time_index"] - df_ws.iloc[0]["time_index"]).total_seconds())

    if (timestep_orig / timestep_upsample % 1) != 0.0:
        raise ValueError(
            "The time step of the provided wind data must be an integer multiple of the upsampled "
            "time series time step."
        )

    # Spatially interpolate wind speeds and cosine and sine components of directions at desired
    # upsampled locations
    ws_interp = _spatially_interpolate_wind_data(
        x_locs_orig, y_locs_orig, df_ws[point_names].values, x_locs_upsample, y_locs_upsample
    )

    wd_cos_interp = _spatially_interpolate_wind_data(
        x_locs_orig,
        y_locs_orig,
        np.cos(np.radians(df_wd[point_names].values)),
        x_locs_upsample,
        y_locs_upsample,
    )

    wd_sin_interp = _spatially_interpolate_wind_data(
        x_locs_orig,
        y_locs_orig,
        np.sin(np.radians(df_wd[point_names].values)),
        x_locs_upsample,
        y_locs_upsample,
    )

    # Upsample spatially interpolated wind speeds and direction components using frequencies up to
    # Nyquist frequency to create smooth signals
    ws_interp_upsample = _upsample_Nyquist(ws_interp, timestep_orig, timestep_upsample)
    wd_cos_interp_upsample = _upsample_Nyquist(wd_cos_interp, timestep_orig, timestep_upsample)
    wd_sin_interp_upsample = _upsample_Nyquist(wd_sin_interp, timestep_orig, timestep_upsample)

    # Convert wind direction components to direction
    wd_interp_upsample = (
        np.degrees(np.arctan2(wd_sin_interp_upsample, wd_cos_interp_upsample)) % 360
    )

    # Find mean upsampled wind direction over all locations
    wd_cos_interp_upsample_mean = np.mean(wd_cos_interp_upsample, axis=0)
    wd_sin_interp_upsample_mean = np.mean(wd_sin_interp_upsample, axis=0)

    wd_interp_upsample_mean = (
        np.degrees(np.arctan2(wd_sin_interp_upsample_mean, wd_cos_interp_upsample_mean)) % 360
    )

    # Next generate stochastic turbulence to add to wind speed times series

    # If turbulence_Uhub is undefined, set to mean wind speed from ws_interp
    if turbulence_Uhub is None:
        turbulence_Uhub = np.mean(ws_interp)

    N_samples_upsample = np.size(ws_interp_upsample, 1)

    ws_prime_mat = _generate_uncorrelated_kaimal_stochastic_turbulence(
        N_locs_upsample, N_samples_upsample, timestep_upsample, turbulence_Uhub, turbulence_L
    )

    # Scale turbulence time series to get desired expected value of TI from IEC normal turbulence
    # model
    ws_std = _get_iec_turbulence_std(ws_interp_upsample, TI_ws_ref, TI_ref)
    ws_prime_mat *= ws_std

    # Combine upsampled interpolated wind speeds and turbulence
    ws_interp_upsample += ws_prime_mat

    # Create dataframe with wind speed and direction variables
    ws_cols = [f"ws_{i:03}" for i in range(N_locs_upsample)]
    df_upsample = pd.DataFrame(ws_interp_upsample.T, columns=ws_cols)

    # Either save wind directions for each location or mean wind direction over all locations
    if save_individual_wds:
        wd_cols = [f"wd_{i:03}" for i in range(N_locs_upsample)]
        df_upsample[wd_cols] = wd_interp_upsample.T
    else:
        df_upsample["wd_mean"] = wd_interp_upsample_mean

    # downcast to smallest float type
    for c in df_upsample.columns:
        df_upsample[c] = pd.to_numeric(df_upsample[c], downcast="float")

    df_upsample["time"] = np.arange(0.0, N_samples_upsample * timestep_upsample, timestep_upsample)
    df_upsample["time_utc"] = pd.date_range(
        df_ws["time_index"][0],
        df_ws.iloc[-1]["time_index"] + pd.Timedelta(seconds=timestep_orig - timestep_upsample),
        freq=f"{timestep_upsample}s",
    )

    # Order columns by location
    if save_individual_wds:
        df_upsample = df_upsample[
            ["time", "time_utc"] + list(chain.from_iterable(zip(ws_cols, wd_cols)))
        ]
    else:
        df_upsample = df_upsample[["time", "time_utc", "wd_mean"] + ws_cols]

    # Save combined dataframe
    df_upsample.to_feather(Path(upsampled_data_dir) / upsampled_data_filename)

    return df_upsample
