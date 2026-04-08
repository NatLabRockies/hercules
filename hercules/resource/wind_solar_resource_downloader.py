"""WTK, NSRDB, and Open-Meteo Data Downloader

This module provides functions to download weather data from multiple sources:
- NLR's Wind Toolkit (WTK) for high-resolution wind data
- NLR's National Solar Radiation Database (NSRDB) for solar irradiance data
- Open-Meteo API for historical weather data with global coverage

All three data sources provide consistent output formats (feather files) for easy integration
into renewable energy modeling workflows.

Author: Andrew Kumler
Date: June 2025
Updated: September 2025 (Added Open-Meteo support)
"""

import os
import time
import warnings
from typing import List, Optional

import openmeteo_requests
import pandas as pd
import requests_cache
from hercules.resource.resource_utilities import (
    create_bounding_box,
    dispatch_plots,
    download_nrel_rex_data,
    get_variable_colormap,
    get_variable_label,
    plot_spatial_map,
    plot_timeseries,
    print_elapsed_time,
    save_coords_to_feather,
    save_variable_to_feather,
    validate_time_params,
)
from hercules.utilities import hercules_float_type
from retry_requests import retry

# Re-export plotting utilities so existing callers can still import them here
__all__ = [
    "download_nsrdb_data",
    "download_wtk_data",
    "download_openmeteo_data",
    "plot_timeseries",
    "plot_spatial_map",
    "get_variable_label",
    "get_variable_colormap",
]


def download_nsrdb_data(
    target_lat: float,
    target_lon: float,
    year: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    variables: List[str] = ["ghi", "dni", "dhi", "wind_speed", "air_temperature"],
    nsrdb_dataset_path="/nrel/nsrdb/GOES/conus/v4.0.0",
    nsrdb_filename_prefix="nsrdb_conus",
    coord_delta: float = 0.1,
    output_dir: str = "./data",
    filename_prefix: str = "nsrdb",
    plot_data: bool = False,
    plot_type: str = "timeseries",
) -> dict:
    """Download NSRDB solar irradiance data for a specified location and time period.

    This function requires an NLR API key, which can be obtained by visiting
    https://developer.nrel.gov/signup/. After receiving your API key, you must make a configuration
    file at ~/.hscfg containing the following:

        hs_endpoint = https://developer.nrel.gov/api/hsds

        hs_api_key = YOUR_API_KEY_GOES_HERE

    More information can be found at: https://github.com/NREL/hsds-examples.

    Args:
        target_lat (float): Target latitude coordinate.
        target_lon (float): Target longitude coordinate.
        year (int, optional): Year of data to download (if using full year approach).
        start_date (str, optional): Start date in format 'YYYY-MM-DD' (if using date range
            approach).
        end_date (str, optional): End date in format 'YYYY-MM-DD' (if using date range
            approach).
        variables (List[str], optional): List of variables to download.
            Defaults to ['ghi', 'dni', 'dhi', 'wind_speed', 'air_temperature'].
        nsrdb_dataset_path (str, optional): Path name of NSRDB dataset. Available datasets at
            https://developer.nrel.gov/docs/solar/nsrdb/.
            Defaults to "/nrel/nsrdb/GOES/conus/v4.0.0".
        nsrdb_filename_prefix (str, optional): File name prefix for the NSRDB HDF5 files in the
            format {nsrdb_filename_prefix}_{year}.h5. Defaults to "nsrdb_conus".
        coord_delta (float, optional): Coordinate delta for bounding box. Defaults to 0.1 degrees.
        output_dir (str, optional): Directory to save output files. Defaults to "./data".
        filename_prefix (str, optional): Prefix for output filenames. Defaults to "nsrdb".
        plot_data (bool, optional): Whether to create plots of the data. Defaults to False.
        plot_type (str, optional): Type of plot to create: 'timeseries' or 'map'.
            Defaults to "timeseries".

    Returns:
        dict: Dictionary containing DataFrames for each variable and coordinates.

    Note:
        Either 'year' OR both 'start_date' and 'end_date' must be provided. Date range approach
        allows for more flexible time periods than full year. Plots are not automatically shown.
        If plot_data is True, call matplotlib.pyplot.show() to display the figure.
    """
    os.makedirs(output_dir, exist_ok=True)

    time_params = validate_time_params(year, start_date, end_date)
    bounding_box = create_bounding_box(target_lat, target_lon, coord_delta)

    data_dict = download_nrel_rex_data(
        dataset_path=nsrdb_dataset_path,
        dataset_filename_prefix=nsrdb_filename_prefix,
        source_name="NSRDB",
        target_lat=target_lat,
        target_lon=target_lon,
        variables=variables,
        bounding_box=bounding_box,
        file_years=time_params["file_years"],
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
        filename_prefix=filename_prefix,
        time_suffix=time_params["time_suffix"],
        time_description=time_params["time_description"],
        os_error_hint=(
            "This could be caused by an invalid API key, NSRDB dataset path, or date range."
        ),
    )

    dispatch_plots(data_dict, variables, plot_data, plot_type, f"{filename_prefix} NSRDB Data")

    return data_dict


def download_wtk_data(
    target_lat: float,
    target_lon: float,
    year: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    variables: List[str] = ["windspeed_100m", "winddirection_100m"],
    coord_delta: float = 0.1,
    output_dir: str = "./data",
    filename_prefix: str = "wtk",
    plot_data: bool = False,
    plot_type: str = "timeseries",
) -> dict:
    """Download WTK wind data for a specified location and time period.

    This function requires an NLR API key, which can be obtained by visiting
    https://developer.nrel.gov/signup/. After receiving your API key, you must make a configuration
    file at ~/.hscfg containing the following:

        hs_endpoint = https://developer.nrel.gov/api/hsds

        hs_api_key = YOUR_API_KEY_GOES_HERE

    More information can be found at: https://github.com/NREL/hsds-examples.

    Args:
        target_lat (float): Target latitude coordinate.
        target_lon (float): Target longitude coordinate.
        year (int, optional): Year of data to download (if using full year approach).
        start_date (str, optional): Start date in format 'YYYY-MM-DD' (if using date range
            approach).
        end_date (str, optional): End date in format 'YYYY-MM-DD' (if using date range approach).
        variables (List[str], optional): List of variables to download.
            Defaults to ['windspeed_100m', 'winddirection_100m'].
        coord_delta (float, optional): Coordinate delta for bounding box. Defaults to 0.1 degrees.
        output_dir (str, optional): Directory to save output files. Defaults to "./data".
        filename_prefix (str, optional): Prefix for output filenames. Defaults to "wtk".
        plot_data (bool, optional): Whether to create plots of the data. Defaults to False.
        plot_type (str, optional): Type of plot to create: 'timeseries' or 'map'.
            Defaults to "timeseries".

    Returns:
        dict: Dictionary containing DataFrames for each variable and coordinates.

    Note:
        Either 'year' OR both 'start_date' and 'end_date' must be provided. Date range approach
        allows for more flexible time periods than full year. Plots are not automatically shown.
        If plot_data is True, call matplotlib.pyplot.show() to display the figure.
    """
    os.makedirs(output_dir, exist_ok=True)

    time_params = validate_time_params(year, start_date, end_date)
    bounding_box = create_bounding_box(target_lat, target_lon, coord_delta)

    data_dict = download_nrel_rex_data(
        dataset_path="/nrel/wtk/wtk-led/conus/v1.0.0/5min",
        dataset_filename_prefix="wtk_conus",
        source_name="WTK",
        target_lat=target_lat,
        target_lon=target_lon,
        variables=variables,
        bounding_box=bounding_box,
        file_years=time_params["file_years"],
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
        filename_prefix=filename_prefix,
        time_suffix=time_params["time_suffix"],
        time_description=time_params["time_description"],
        os_error_hint="This could be caused by an invalid API key or date range.",
    )

    dispatch_plots(data_dict, variables, plot_data, plot_type, f"{filename_prefix} WTK Data")

    return data_dict


# ---------------------------------------------------------------------------
# Open-Meteo variable mapping
# ---------------------------------------------------------------------------

OPENMETEO_VARIABLE_MAPPING = {
    "wind_speed_80m": "wind_speed_80m",
    "wind_direction_80m": "wind_direction_80m",
    "temperature_2m": "temperature_2m",
    "shortwave_radiation_instant": "shortwave_radiation_instant",
    "diffuse_radiation_instant": "diffuse_radiation_instant",
    "direct_normal_irradiance_instant": "direct_normal_irradiance_instant",
    "ghi": "shortwave_radiation_instant",
    "dni": "direct_normal_irradiance_instant",
    "dhi": "diffuse_radiation_instant",
    "windspeed_80m": "wind_speed_80m",
    "winddirection_80m": "wind_direction_80m",
}
"""Mapping from user-facing variable names (including aliases) to Open-Meteo API parameter
names."""


def download_openmeteo_data(
    target_lat: float | List[float],
    target_lon: float | List[float],
    year: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    variables: List[str] = [
        "wind_speed_80m",
        "wind_direction_80m",
        "temperature_2m",
        "shortwave_radiation_instant",
        "diffuse_radiation_instant",
        "direct_normal_irradiance_instant",
    ],
    coord_delta: float = 0.1,
    output_dir: str = "./data",
    filename_prefix: str = "openmeteo",
    plot_data: bool = False,
    plot_type: str = "timeseries",
    remove_duplicate_coords=True,
) -> dict:
    """Download Open-Meteo weather data for specified location(s) and time period.

    Data are retrieved from the nearest weather grid cell to the requested locations. The grid cell
    resolution varies with latitude, but at ~35 degrees latitude, the grid cell resolution is
    approximately 0.027 degrees latitude (~2.4 km in the N-S direction) and 0.0333 degrees
    longitude (~3.7km in the E-W direction).

    Args:
        target_lat (float | List[float]): Target latitude coordinate or list of latitude
            coordinates.
        target_lon (float | List[float]): Target longitude coordinate or list of longitude
            coordinates.
        year (int, optional): Year of data to download (if using full year approach).
        start_date (str, optional): Start date in format 'YYYY-MM-DD' (if using date range
            approach).
        end_date (str, optional): End date in format 'YYYY-MM-DD' (if using date range approach).
        variables (List[str], optional): List of variables to download. Available options include
            wind_speed_80m, wind_direction_80m, temperature_2m, shortwave_radiation_instant,
            diffuse_radiation_instant, direct_normal_irradiance_instant.
        coord_delta (float, optional): Not used for Open-Meteo (points specified individually),
            kept for consistency. Defaults to 0.1.
        output_dir (str, optional): Directory to save output files. Defaults to "./data".
        filename_prefix (str, optional): Prefix for output filenames. Defaults to "openmeteo".
        plot_data (bool, optional): Whether to create plots of the data. Defaults to False.
        plot_type (str, optional): Type of plot to create: 'timeseries' or 'map'.
            Defaults to "timeseries".
        remove_duplicate_coords (bool, optional): Whether to remove data from duplicate coordinates.
            Defaults to True.

    Returns:
        dict: Dictionary containing DataFrames for each variable and coordinates.

    Note:
        Either 'year' OR both 'start_date' and 'end_date' must be provided. Open-Meteo provides
        point data (not gridded), so coord_delta is ignored. Available historical data typically
        spans from 1940 to present. Plots are not automatically shown. If plot_data is True, call
        matplotlib.pyplot.show() to display the figure.
    """
    os.makedirs(output_dir, exist_ok=True)

    time_params = validate_time_params(year, start_date, end_date)
    time_suffix = time_params["time_suffix"]
    time_description = time_params["time_description"]
    api_start_date = time_params["start_date"]
    api_end_date = time_params["end_date"]

    print(f"Downloading Open-Meteo data for {time_description}")
    print(f"Target coordinates: ({target_lat}, {target_lon})")
    print(f"Variables: {variables}")
    print("Note: Open-Meteo provides point data (coord_delta ignored)")

    mapped_variables = _map_openmeteo_variables(variables)

    t0 = time.time()

    try:
        responses = _fetch_openmeteo_responses(
            target_lat, target_lon, api_start_date, api_end_date, mapped_variables
        )

        data_dict, original_var_names = _process_openmeteo_responses(
            responses, mapped_variables, variables
        )

        if remove_duplicate_coords and len(data_dict["coordinates"]) > 1:
            _remove_duplicate_coordinates(data_dict, original_var_names)

        for var_name in original_var_names:
            save_variable_to_feather(
                data_dict[var_name], output_dir, filename_prefix, var_name, time_suffix
            )

        save_coords_to_feather(data_dict["coordinates"], output_dir, filename_prefix, time_suffix)

    except Exception as e:
        print(f"Error downloading Open-Meteo data: {e}")
        raise

    print_elapsed_time(t0, "Open-Meteo")

    dispatch_plots(data_dict, variables, plot_data, plot_type, f"{filename_prefix} Open-Meteo Data")

    return data_dict


# ---------------------------------------------------------------------------
# Open-Meteo internal helpers
# ---------------------------------------------------------------------------


def _map_openmeteo_variables(variables: List[str]) -> list:
    """Map user-facing variable names to Open-Meteo API parameter names.

    Args:
        variables (list[str]): List of user-facing variable names.

    Returns:
        list: List of mapped Open-Meteo API parameter names.

    Raises:
        ValueError: If no valid variables are found after mapping.
    """
    mapped_variables = []
    for var in variables:
        if var in OPENMETEO_VARIABLE_MAPPING:
            mapped_variables.append(OPENMETEO_VARIABLE_MAPPING[var])
        else:
            print(f"Warning: Variable '{var}' not available in Open-Meteo. Skipping.")

    if not mapped_variables:
        raise ValueError("No valid variables found for Open-Meteo download.")

    return mapped_variables


def _fetch_openmeteo_responses(
    target_lat: float | List[float],
    target_lon: float | List[float],
    start_date: str,
    end_date: str,
    mapped_variables: list,
) -> list:
    """Fetch data from the Open-Meteo API with SSL fallback.

    Attempts the request with SSL verification first. If that fails, retries
    with SSL verification disabled.

    Args:
        target_lat (float | list[float]): Target latitude(s).
        target_lon (float | list[float]): Target longitude(s).
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
        mapped_variables (list): List of Open-Meteo API parameter names.

    Returns:
        list: List of Open-Meteo API response objects.
    """
    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
    params = {
        "latitude": target_lat,
        "longitude": target_lon,
        "start_date": start_date,
        "end_date": end_date,
        "minutely_15": mapped_variables,
        "wind_speed_unit": "ms",
    }

    try:
        responses = openmeteo.weather_api(url, params=params)
        print("API request successful with SSL verification.")
    except Exception as e:
        print(f"SSL verification failed: {str(e)[:100]}...")
        print("Trying with SSL verification disabled...")

        warnings.filterwarnings("ignore", message="Unverified HTTPS request")

        cache_session_no_ssl = requests_cache.CachedSession(".cache", expire_after=3600)
        cache_session_no_ssl.verify = False
        retry_session_no_ssl = retry(cache_session_no_ssl, retries=5, backoff_factor=0.2)
        openmeteo_no_ssl = openmeteo_requests.Client(session=retry_session_no_ssl)

        responses = openmeteo_no_ssl.weather_api(url, params=params)
        print("API request successful with SSL verification disabled.")

    return responses


def _process_openmeteo_responses(
    responses: list,
    mapped_variables: list,
    original_variables: List[str],
) -> tuple:
    """Process Open-Meteo API responses into a data dictionary.

    Args:
        responses (list): List of Open-Meteo API response objects.
        mapped_variables (list): List of mapped Open-Meteo API parameter names.
        original_variables (list[str]): Original user-facing variable names.

    Returns:
        tuple: (data_dict, original_var_names) where data_dict contains DataFrames for each
            variable and coordinates, and original_var_names is the list of variable names used
            as keys in data_dict.
    """
    data_dict = {"coordinates": pd.DataFrame()}

    original_var_names = []
    for var in mapped_variables:
        original_var_name = None
        for orig, mapped in OPENMETEO_VARIABLE_MAPPING.items():
            if mapped == var and orig in original_variables:
                original_var_name = orig
                break

        var_name = original_var_name if original_var_name else var
        data_dict[var_name] = pd.DataFrame()
        original_var_names.append(var_name)

    for gid, response in enumerate(responses):
        print(f"Coordinates retrieved: {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation: {response.Elevation()} m asl")

        minutely_15 = response.Minutely15()

        date_range = pd.date_range(
            start=pd.to_datetime(minutely_15.Time(), unit="s", utc=True),
            end=pd.to_datetime(minutely_15.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=minutely_15.Interval()),
            inclusive="left",
        )

        df_coords = pd.DataFrame(
            [[response.Latitude(), response.Longitude()]], index=[gid], columns=["lat", "lon"]
        )
        data_dict["coordinates"] = pd.concat([data_dict["coordinates"], df_coords], axis=0)

        for i, var_name in enumerate(original_var_names):
            var_data = minutely_15.Variables(i).ValuesAsNumpy()

            df_var = pd.DataFrame(
                var_data.astype(hercules_float_type), index=date_range, columns=[gid]
            )
            df_var.index.name = "time_index"

            data_dict[var_name] = pd.concat([data_dict[var_name], df_var], axis=1)

    return data_dict, original_var_names


def _remove_duplicate_coordinates(
    data_dict: dict,
    original_var_names: list,
) -> None:
    """Remove duplicate coordinates from the data dictionary in-place.

    When multiple requested coordinates map to the same weather grid cell, this function keeps
    only the first occurrence and re-indexes the columns consecutively.

    Args:
        data_dict (dict): Data dictionary to modify. Must contain a "coordinates" key.
        original_var_names (list): List of variable names to filter.
    """
    duplicate_mask = data_dict["coordinates"].duplicated(subset=["lat", "lon"], keep="first")
    data_dict["coordinates"] = data_dict["coordinates"][~duplicate_mask]

    for var_name in original_var_names:
        data_dict[var_name] = data_dict[var_name][[c for c in data_dict["coordinates"].index]]
        data_dict[var_name].columns = range(len(data_dict["coordinates"]))

    data_dict["coordinates"] = data_dict["coordinates"].reset_index(drop=True)
