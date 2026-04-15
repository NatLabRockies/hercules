"""Open-Meteo solar and wind data downloader.

This module provides the `download_openmeteo_data` function, which was
previously defined in `wind_solar_resource_downloader`. The implementation
is moved here without functional changes to support a more modular resource
package layout.
"""

import math
import os
import time
import warnings
from typing import List, Optional

import numpy as np
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

from hercules.resource.resource_utilities import (
    plot_spatial_map,
    plot_timeseries,
)
from hercules.utilities import hercules_float_type


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

    if year is not None and (start_date is not None or end_date is not None):
        raise ValueError(
            "Please provide either 'year' OR both 'start_date' and 'end_date', not both approaches."
        )

    if year is None and (start_date is None or end_date is None):
        raise ValueError("Please provide either 'year' OR both 'start_date' and 'end_date'.")

    if year is not None:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        time_suffix = str(year)
        time_description = f"year {year}"
    else:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        if start_dt > end_dt:
            raise ValueError("start_date must be before end_date")

        time_suffix = f"{start_date}_to_{end_date}".replace("-", "")
        time_description = f"period {start_date} to {end_date}"

    print(f"Downloading Open-Meteo data for {time_description}")
    print(f"Target coordinates: ({target_lat}, {target_lon})")
    print(f"Variables: {variables}")
    print("Note: Open-Meteo provides point data (coord_delta ignored)")

    variable_mapping = {
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

    mapped_variables: list[str] = []
    for var in variables:
        if var in variable_mapping:
            mapped_variables.append(variable_mapping[var])
        else:
            print(f"Warning: Variable '{var}' not available in Open-Meteo. Skipping.")

    if not mapped_variables:
        raise ValueError("No valid variables found for Open-Meteo download.")

    t0 = time.time()

    try:
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

        data_dict: dict = {}
        data_dict["coordinates"] = pd.DataFrame()

        original_var_names: list[str] = []
        for var in mapped_variables:
            original_var_name = None
            for orig, mapped in variable_mapping.items():
                if mapped == var and orig in variables:
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
                [[response.Latitude(), response.Longitude()]],
                index=[gid],
                columns=["lat", "lon"],
            )
            data_dict["coordinates"] = pd.concat([data_dict["coordinates"], df_coords], axis=0)

            for i, var_name in enumerate(original_var_names):
                var_data = minutely_15.Variables(i).ValuesAsNumpy()

                df_var = pd.DataFrame(
                    var_data.astype(hercules_float_type),
                    index=date_range,
                    columns=[gid],
                )
                df_var.index.name = "time_index"

                data_dict[var_name] = pd.concat([data_dict[var_name], df_var], axis=1)

        if remove_duplicate_coords and (len(data_dict["coordinates"]) > 1):
            duplicate_mask = data_dict["coordinates"].duplicated(
                subset=["lat", "lon"],
                keep="first",
            )
            data_dict["coordinates"] = data_dict["coordinates"][~duplicate_mask]

            for var_name in original_var_names:
                data_dict[var_name] = data_dict[var_name][
                    [c for c in data_dict["coordinates"].index]
                ]
                data_dict[var_name].columns = range(len(data_dict["coordinates"]))

            data_dict["coordinates"] = data_dict["coordinates"].reset_index(drop=True)

        for var_name in original_var_names:
            output_file = os.path.join(
                output_dir,
                f"{filename_prefix}_{var_name}_{time_suffix}.feather",
            )
            data_dict[var_name].reset_index().to_feather(output_file)
            print(f"Saved {var_name} data to {output_file}")

        coords_file = os.path.join(output_dir, f"{filename_prefix}_coords_{time_suffix}.feather")
        data_dict["coordinates"].reset_index().to_feather(coords_file)
        print(f"Saved coordinates to {coords_file}")

    except Exception as e:
        print(f"Error downloading Open-Meteo data: {e}")
        raise

    total_time = (time.time() - t0) / 60
    decimal_part = math.modf(total_time)[0] * 60
    print(
        "Open-Meteo download completed in "
        f"{int(np.floor(total_time))}:{int(np.round(decimal_part, 0)):02d} minutes"
    )

    if plot_data and data_dict and "coordinates" in data_dict:
        coordinates_array = data_dict["coordinates"][["lat", "lon"]].values
        if plot_type == "timeseries":
            plot_timeseries(
                data_dict,
                variables,
                coordinates_array,
                f"{filename_prefix} Open-Meteo Data",
            )
        elif plot_type == "map":
            plot_spatial_map(
                data_dict,
                variables,
                coordinates_array,
                f"{filename_prefix} Open-Meteo Data",
            )

    return data_dict
