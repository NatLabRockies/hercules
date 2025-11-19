"""
WTK, NSRDB, and Open-Meteo Data Downloader

This script provides functions to download weather data from multiple sources:
- NREL's Wind Toolkit (WTK) for high-resolution wind data
- NREL's National Solar Radiation Database (NSRDB) for solar irradiance data
- Open-Meteo API for historical weather data with global coverage

All three data sources provide consistent output formats (feather files) for easy integration
into renewable energy modeling workflows.

Author: Andrew Kumler
Date: June 2025
Updated: September 2025 (Added Open-Meteo support)
"""

import math
import os
import time
import warnings
from typing import List, Optional

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from rex import ResourceX
from scipy.interpolate import griddata


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

    This function requires an NREL API key, which can be obtained by visiting
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

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Validate input parameters
    if year is not None and (start_date is not None or end_date is not None):
        raise ValueError(
            "Please provide either 'year' OR both 'start_date' and 'end_date', not both approaches."
        )

    if year is None and (start_date is None or end_date is None):
        raise ValueError("Please provide either 'year' OR both 'start_date' and 'end_date'.")

    # Determine the approach and set up file paths and time info
    if year is not None:
        # Full year approach
        file_years = [year]
        time_suffix = str(year)
        time_description = f"year {year}"
    else:
        # Date range approach

        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        if start_dt > end_dt:
            raise ValueError("start_date must be before end_date")

        # Get all years in the date range
        file_years = list(range(start_dt.year, end_dt.year + 1))
        time_suffix = f"{start_date}_to_{end_date}".replace("-", "")
        time_description = f"period {start_date} to {end_date}"

    # Create the bounding box
    llcrn_lat = target_lat - coord_delta
    llcrn_lon = target_lon - coord_delta
    urcrn_lat = target_lat + coord_delta
    urcrn_lon = target_lon + coord_delta

    print(f"Downloading NSRDB data for {time_description}")
    print(f"Target coordinates: ({target_lat}, {target_lon})")
    print(f"Bounding box: ({llcrn_lat}, {llcrn_lon}) to ({urcrn_lat}, {urcrn_lon})")
    print(f"Variables: {variables}")
    print(f"Years to process: {file_years}")

    t0 = time.time()

    data_dict = {}
    all_dataframes = {var: [] for var in variables}

    try:
        # Process each year in the range
        for file_year in file_years:
            print(f"\nProcessing year {file_year}...")
            fp = f"{nsrdb_dataset_path}/{nsrdb_filename_prefix}_{file_year}.h5"

            with ResourceX(fp) as res:
                # Download each variable for this year
                for var in variables:
                    print(f"  Downloading {var} for {file_year}...")
                    df_year = res.get_box_df(
                        var, lat_lon_1=[llcrn_lat, llcrn_lon], lat_lon_2=[urcrn_lat, urcrn_lon]
                    )

                    # Filter by date range if using date range approach
                    if start_date is not None and end_date is not None:
                        # Filter the DataFrame to the specified date range
                        df_year = df_year.loc[start_date:end_date]

                    all_dataframes[var].append(df_year)

                # Get coordinates (only need to do this once)
                if "coordinates" not in data_dict:
                    gids = df_year.columns.values
                    coordinates = res.lat_lon[gids]
                    df_coords = pd.DataFrame(coordinates, index=gids, columns=["lat", "lon"])
                    data_dict["coordinates"] = df_coords

        # Concatenate all years for each variable
        for var in variables:
            if all_dataframes[var]:
                print(f"Concatenating {var} data across {len(all_dataframes[var])} years...")
                data_dict[var] = pd.concat(all_dataframes[var], axis=0).sort_index()

                # Save to feather format
                output_file = os.path.join(
                    output_dir, f"{filename_prefix}_{var}_{time_suffix}.feather"
                )
                data_dict[var].reset_index().to_feather(output_file)
                print(f"Saved {var} data to {output_file}")

        # Save coordinates
        coords_file = os.path.join(output_dir, f"{filename_prefix}_coords_{time_suffix}.feather")
        data_dict["coordinates"].reset_index().to_feather(coords_file)
        print(f"Saved coordinates to {coords_file}")

    except OSError as e:
        print(f"Error downloading NSRDB data: {e}")
        print("This could be caused by an invalid API key, NSRDB dataset path, or date range.")
        raise
    except Exception as e:
        print(f"Error downloading NSRDB data: {e}")
        raise

    total_time = (time.time() - t0) / 60
    decimal_part = math.modf(total_time)[0] * 60
    print(
        "NSRDB download completed in "
        f"{int(np.floor(total_time))}:{int(np.round(decimal_part, 0)):02d} minutes"
    )

    # Create plots if requested
    if plot_data and data_dict and "coordinates" in data_dict:
        coordinates_array = data_dict["coordinates"][["lat", "lon"]].values
        if plot_type == "timeseries":
            plot_timeseries(
                data_dict, variables, coordinates_array, f"{filename_prefix} NSRDB Data"
            )
        elif plot_type == "map":
            plot_spatial_map(
                data_dict, variables, coordinates_array, f"{filename_prefix} NSRDB Data"
            )

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

    This function requires an NREL API key, which can be obtained by visiting
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

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Validate input parameters
    if year is not None and (start_date is not None or end_date is not None):
        raise ValueError(
            "Please provide either 'year' OR both 'start_date' and 'end_date', not both approaches."
        )

    if year is None and (start_date is None or end_date is None):
        raise ValueError("Please provide either 'year' OR both 'start_date' and 'end_date'.")

    # Determine the approach and set up file paths and time info
    if year is not None:
        # Full year approach
        file_years = [year]
        time_suffix = str(year)
        time_description = f"year {year}"
    else:
        # Date range approach

        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        if start_dt > end_dt:
            raise ValueError("start_date must be before end_date")

        # Get all years in the date range
        file_years = list(range(start_dt.year, end_dt.year + 1))
        time_suffix = f"{start_date}_to_{end_date}".replace("-", "")
        time_description = f"period {start_date} to {end_date}"

    # Create the bounding box
    llcrn_lat = target_lat - coord_delta
    llcrn_lon = target_lon - coord_delta
    urcrn_lat = target_lat + coord_delta
    urcrn_lon = target_lon + coord_delta

    print(f"Downloading WTK data for {time_description}")
    print(f"Target coordinates: ({target_lat}, {target_lon})")
    print(f"Bounding box: ({llcrn_lat}, {llcrn_lon}) to ({urcrn_lat}, {urcrn_lon})")
    print(f"Variables: {variables}")
    print(f"Years to process: {file_years}")

    t0 = time.time()

    data_dict = {}
    all_dataframes = {var: [] for var in variables}

    try:
        # Process each year in the range
        for file_year in file_years:
            print(f"\nProcessing year {file_year}...")
            fp = f"/nrel/wtk/wtk-led/conus/v1.0.0/5min/wtk_conus_{file_year}.h5"

            with ResourceX(fp) as res:
                # Download each variable for this year
                for var in variables:
                    print(f"  Downloading {var} for {file_year}...")
                    df_year = res.get_box_df(
                        var, lat_lon_1=[llcrn_lat, llcrn_lon], lat_lon_2=[urcrn_lat, urcrn_lon]
                    )

                    # Filter by date range if using date range approach
                    if start_date is not None and end_date is not None:
                        # Filter the DataFrame to the specified date range
                        df_year = df_year.loc[start_date:end_date]

                    all_dataframes[var].append(df_year)

                # Get coordinates (only need to do this once)
                if "coordinates" not in data_dict:
                    gids = df_year.columns.values
                    coordinates = res.lat_lon[gids]
                    df_coords = pd.DataFrame(coordinates, index=gids, columns=["lat", "lon"])
                    data_dict["coordinates"] = df_coords

        # Concatenate all years for each variable
        for var in variables:
            if all_dataframes[var]:
                print(f"Concatenating {var} data across {len(all_dataframes[var])} years...")
                data_dict[var] = pd.concat(all_dataframes[var], axis=0).sort_index()

                # Save to feather format
                output_file = os.path.join(
                    output_dir, f"{filename_prefix}_{var}_{time_suffix}.feather"
                )
                data_dict[var].reset_index().to_feather(output_file)
                print(f"Saved {var} data to {output_file}")

        # Save coordinates
        coords_file = os.path.join(output_dir, f"{filename_prefix}_coords_{time_suffix}.feather")
        data_dict["coordinates"].reset_index().to_feather(coords_file)
        print(f"Saved coordinates to {coords_file}")

    except OSError as e:
        print(f"Error downloading WTK data: {e}")
        print("This could be caused by an invalid API key or date range.")
        raise
    except Exception as e:
        print(f"Error downloading WTK data: {e}")
        raise

    total_time = (time.time() - t0) / 60
    decimal_part = math.modf(total_time)[0] * 60
    print(
        "WTK download completed in "
        f"{int(np.floor(total_time))}:{int(np.round(decimal_part, 0)):02d} minutes"
    )

    # Create plots if requested
    if plot_data and data_dict and "coordinates" in data_dict:
        coordinates_array = data_dict["coordinates"][["lat", "lon"]].values
        if plot_type == "timeseries":
            plot_timeseries(data_dict, variables, coordinates_array, f"{filename_prefix} WTK Data")
        elif plot_type == "map":
            plot_spatial_map(data_dict, variables, coordinates_array, f"{filename_prefix} WTK Data")

    return data_dict


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

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Validate input parameters
    if year is not None and (start_date is not None or end_date is not None):
        raise ValueError(
            "Please provide either 'year' OR both 'start_date' and 'end_date', not both approaches."
        )

    if year is None and (start_date is None or end_date is None):
        raise ValueError("Please provide either 'year' OR both 'start_date' and 'end_date'.")

    # Determine the approach and set up time info
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

    # Map variable names to Open-Meteo API parameters
    variable_mapping = {
        "wind_speed_80m": "wind_speed_80m",
        "wind_direction_80m": "wind_direction_80m",
        "temperature_2m": "temperature_2m",
        "shortwave_radiation_instant": "shortwave_radiation_instant",
        "diffuse_radiation_instant": "diffuse_radiation_instant",
        "direct_normal_irradiance_instant": "direct_normal_irradiance_instant",
        "ghi": "shortwave_radiation_instant",  # Alias for solar users
        "dni": "direct_normal_irradiance_instant",  # Alias for solar users
        "dhi": "diffuse_radiation_instant",  # Alias for solar users
        "windspeed_80m": "wind_speed_80m",  # Alias for wind users
        "winddirection_80m": "wind_direction_80m",  # Alias for wind users
    }

    # Validate variables and map them
    mapped_variables = []
    for var in variables:
        if var in variable_mapping:
            mapped_variables.append(variable_mapping[var])
        else:
            print(f"Warning: Variable '{var}' not available in Open-Meteo. Skipping.")

    if not mapped_variables:
        raise ValueError("No valid variables found for Open-Meteo download.")

    t0 = time.time()

    try:
        # Setup the Open-Meteo API client with cache and retry on error
        cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)

        # Setup API parameters
        url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
        params = {
            "latitude": target_lat,
            "longitude": target_lon,
            "start_date": start_date,
            "end_date": end_date,
            "minutely_15": mapped_variables,
            "wind_speed_unit": "ms",
        }

        # Try to make the API request with SSL verification first, then fallback to no verification
        try:
            responses = openmeteo.weather_api(url, params=params)
            print("API request successful with SSL verification.")
        except Exception as e:
            print(f"SSL verification failed: {str(e)[:100]}...")
            print("Trying with SSL verification disabled...")

            # Suppress SSL warnings since we're intentionally disabling verification
            warnings.filterwarnings("ignore", message="Unverified HTTPS request")

            # Create a new session with SSL verification disabled
            cache_session_no_ssl = requests_cache.CachedSession(".cache", expire_after=3600)
            cache_session_no_ssl.verify = False
            retry_session_no_ssl = retry(cache_session_no_ssl, retries=5, backoff_factor=0.2)
            openmeteo_no_ssl = openmeteo_requests.Client(session=retry_session_no_ssl)

            responses = openmeteo_no_ssl.weather_api(url, params=params)
            print("API request successful with SSL verification disabled.")

        # Create data dictionary in the same format as WTK/NSRDB and initialize dataframes
        data_dict = {}
        data_dict["coordinates"] = pd.DataFrame()

        # Initialize for each variable
        original_var_names = []
        for var in mapped_variables:
            # Use original variable name (not mapped name) for consistency
            original_var_name = None
            for orig, mapped in variable_mapping.items():
                if mapped == var and orig in variables:
                    original_var_name = orig
                    break

            var_name = original_var_name if original_var_name else var
            data_dict[var_name] = pd.DataFrame()

            original_var_names.append(var_name)

        # Process the responses for each lat/lon
        for gid, response in enumerate(responses):
            print(f"Coordinates retrieved: {response.Latitude()}°N {response.Longitude()}°E")
            print(f"Elevation: {response.Elevation()} m asl")

            # Process minutely_15 data
            minutely_15 = response.Minutely15()

            # Create the date range
            date_range = pd.date_range(
                start=pd.to_datetime(minutely_15.Time(), unit="s", utc=True),
                end=pd.to_datetime(minutely_15.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=minutely_15.Interval()),
                inclusive="left",
            )

            # Create coordinates DataFrame (single point, but match the format)
            # Use a synthetic GID (grid ID) to match WTK/NSRDB format
            df_coords = pd.DataFrame(
                [[response.Latitude(), response.Longitude()]], index=[gid], columns=["lat", "lon"]
            )
            data_dict["coordinates"] = pd.concat([data_dict["coordinates"], df_coords], axis=0)

            # Process each requested variable
            for i, var_name in enumerate(original_var_names):
                var_data = minutely_15.Variables(i).ValuesAsNumpy()

                # Create DataFrame with same structure as WTK/NSRDB (datetime index, gid columns)
                df_var = pd.DataFrame(var_data, index=date_range, columns=[gid])
                df_var.index.name = "time_index"

                data_dict[var_name] = pd.concat([data_dict[var_name], df_var], axis=1)

        # Check for duplicates, remove if any exist, and rename locations indices consecutively
        if remove_duplicate_coords & (len(data_dict["coordinates"]) > 1):
            duplicate_mask = data_dict["coordinates"].duplicated(
                subset=["lat", "lon"], keep="first"
            )
            data_dict["coordinates"] = data_dict["coordinates"][~duplicate_mask]

            for var_name in original_var_names:
                data_dict[var_name] = data_dict[var_name][
                    [c for c in data_dict["coordinates"].index]
                ]
                data_dict[var_name].columns = range(len(data_dict["coordinates"]))

            data_dict["coordinates"] = data_dict["coordinates"].reset_index(drop=True)

        # Save variables to feather format
        for var_name in original_var_names:
            output_file = os.path.join(
                output_dir, f"{filename_prefix}_{var_name}_{time_suffix}.feather"
            )
            data_dict[var_name].reset_index().to_feather(output_file)
            print(f"Saved {var_name} data to {output_file}")

        # Save coordinates
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

    # Create plots if requested
    if plot_data and data_dict and "coordinates" in data_dict:
        coordinates_array = data_dict["coordinates"][["lat", "lon"]].values
        if plot_type == "timeseries":
            plot_timeseries(
                data_dict, variables, coordinates_array, f"{filename_prefix} Open-Meteo Data"
            )
        elif plot_type == "map":
            plot_spatial_map(
                data_dict, variables, coordinates_array, f"{filename_prefix} Open-Meteo Data"
            )

    return data_dict


def plot_timeseries(data_dict: dict, variables: List[str], coordinates: np.ndarray, title: str):
    """Create time-series plots for the downloaded data.

    Args:
        data_dict (dict): Dictionary containing DataFrames for each variable.
        variables (List[str]): List of variables to plot.
        coordinates (np.ndarray): Array of coordinates for the data points.
        title (str): Title for the plots.
    """

    n_vars = len(variables)
    if n_vars == 0:
        return

    # Create subplots based on number of variables
    fig, axes = plt.subplots(n_vars, 1, figsize=(12, 4 * n_vars), sharex=True)
    if n_vars == 1:
        axes = [axes]

    for i, var in enumerate(variables):
        if var in data_dict:
            df = data_dict[var]

            # Plot all time series (one for each spatial point)
            for col in df.columns:
                axes[i].plot(df.index, df[col], alpha=0.7, linewidth=0.8)

            axes[i].set_ylabel(get_variable_label(var))
            axes[i].set_title(f"{var.replace('_', ' ').title()}")
            axes[i].grid(True, alpha=0.3)

    axes[-1].set_xlabel("Time")
    plt.suptitle(f"{title} - Time Series", fontsize=14, fontweight="bold")
    plt.tight_layout()


def plot_spatial_map(data_dict: dict, variables: List[str], coordinates: np.ndarray, title: str):
    """Create spatial maps showing the mean values across the region.

    Args:
        data_dict (dict): Dictionary containing DataFrames for each variable.
        variables (List[str]): List of variables to plot.
        coordinates (np.ndarray): Array of coordinates for the data points.
        title (str): Title for the plots.
    """

    n_vars = len(variables)
    if n_vars == 0:
        return

    # Calculate subplot layout
    n_cols = min(2, n_vars)
    n_rows = math.ceil(n_vars / n_cols)

    plt.figure(figsize=(8 * n_cols, 6 * n_rows))

    for i, var in enumerate(variables):
        if var in data_dict:
            df = data_dict[var]

            # Extract coordinates
            lats = coordinates[:, 0]
            lons = coordinates[:, 1]

            # Calculate mean values across time
            mean_values = df.mean(axis=0).values

            # Create subplot with map projection
            ax = plt.subplot(n_rows, n_cols, i + 1, projection=ccrs.PlateCarree())

            # Add geographic features
            ax.add_feature(cfeature.COASTLINE, alpha=0.5)
            ax.add_feature(cfeature.BORDERS, linestyle=":", alpha=0.5)
            ax.add_feature(cfeature.LAND, edgecolor="black", facecolor="lightgray", alpha=0.3)
            ax.add_feature(cfeature.OCEAN, facecolor="lightblue", alpha=0.3)

            # Create interpolated grid for smoother visualization
            if len(lats) > 4:  # Only interpolate if we have enough points
                grid_lon = np.linspace(min(lons), max(lons), 50)
                grid_lat = np.linspace(min(lats), max(lats), 50)
                grid_lon, grid_lat = np.meshgrid(grid_lon, grid_lat)

                try:
                    grid_values = griddata(
                        (lons, lats), mean_values, (grid_lon, grid_lat), method="cubic"
                    )
                    contour = ax.contourf(
                        grid_lon,
                        grid_lat,
                        grid_values,
                        levels=15,
                        cmap=get_variable_colormap(var),
                        transform=ccrs.PlateCarree(),
                    )
                    plt.colorbar(
                        contour,
                        ax=ax,
                        orientation="vertical",
                        label=get_variable_label(var),
                        shrink=0.8,
                    )
                except Exception:
                    # Fall back to scatter plot if interpolation fails
                    sc = ax.scatter(
                        lons,
                        lats,
                        c=mean_values,
                        s=100,
                        cmap=get_variable_colormap(var),
                        transform=ccrs.PlateCarree(),
                    )
                    plt.colorbar(
                        sc, ax=ax, orientation="vertical", label=get_variable_label(var), shrink=0.8
                    )
            else:
                # Use scatter plot for few points
                sc = ax.scatter(
                    lons,
                    lats,
                    c=mean_values,
                    s=100,
                    cmap=get_variable_colormap(var),
                    transform=ccrs.PlateCarree(),
                )
                plt.colorbar(
                    sc, ax=ax, orientation="vertical", label=get_variable_label(var), shrink=0.8
                )

            # Add points on top
            ax.scatter(lons, lats, c="black", s=20, transform=ccrs.PlateCarree(), alpha=0.8)

            # Set title
            ax.set_title(f"{var.replace('_', ' ').title()}")

            # Set coordinate labels
            ax.set_xticks(np.linspace(min(lons), max(lons), 5))
            ax.set_yticks(np.linspace(min(lats), max(lats), 5))
            ax.set_xticklabels(
                [f"{lon:.2f}°" for lon in np.linspace(min(lons), max(lons), 5)], fontsize=8
            )
            ax.set_yticklabels(
                [f"{lat:.2f}°" for lat in np.linspace(min(lats), max(lats), 5)], fontsize=8
            )
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")

    plt.suptitle(f"{title} - Spatial Distribution (Time-Averaged)", fontsize=14, fontweight="bold")
    plt.tight_layout()


def get_variable_label(variable: str) -> str:
    """Get appropriate label and units for a variable.

    Args:
        variable (str): Variable name.

    Returns:
        str: Label with units for the variable.
    """
    labels = {
        "ghi": "GHI (W/m²)",
        "dni": "DNI (W/m²)",
        "dhi": "DHI (W/m²)",
        "windspeed_100m": "Wind Speed at 100m (m/s)",
        "winddirection_100m": "Wind Direction at 100m (°)",
        "turbulent_kinetic_energy_100m": "TKE at 100m (m²/s²)",
        "temperature_100m": "Temperature at 100m (°C)",
        "pressure_100m": "Pressure at 100m (Pa)",
        # Open-Meteo variables
        "wind_speed_80m": "Wind Speed at 80m (m/s)",
        "windspeed_80m": "Wind Speed at 80m (m/s)",
        "wind_direction_80m": "Wind Direction at 80m (m/s)",
        "winddirection_80m": "Wind Direction at 80m (m/s)",
        "temperature_2m": "Temperature at 2m (°C)",
        "shortwave_radiation_instant": "Shortwave Radiation (W/m²)",
        "diffuse_radiation_instant": "Diffuse Radiation (W/m²)",
        "direct_normal_irradiance_instant": "Direct Normal Irradiance (W/m²)",
    }
    return labels.get(variable, variable.replace("_", " ").title())


def get_variable_colormap(variable: str) -> str:
    """Get appropriate colormap for a variable.

    Args:
        variable (str): Variable name.

    Returns:
        str: Matplotlib colormap name for the variable.
    """
    colormaps = {
        "ghi": "plasma",
        "dni": "plasma",
        "dhi": "plasma",
        "windspeed_100m": "viridis",
        "winddirection_100m": "hsv",
        "turbulent_kinetic_energy_100m": "cividis",
        "temperature_100m": "RdYlBu_r",
        "pressure_100m": "coolwarm",
        # Open-Meteo variables
        "wind_speed_80m": "viridis",
        "windspeed_80m": "viridis",
        "wind_direction_80m": "hsv",
        "winddirection_80m": "hsv",
        "temperature_2m": "RdYlBu_r",
        "shortwave_radiation_instant": "plasma",
        "diffuse_radiation_instant": "plasma",
        "direct_normal_irradiance_instant": "plasma",
    }
    return colormaps.get(variable, "viridis")
