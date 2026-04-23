"""WIND Toolkit (WTK) wind data downloader.

This module provides the `download_wtk_data` function, which was previously
defined in `wind_solar_resource_downloader`. The implementation is moved
here without functional changes to support a more modular resource package
layout.
"""

import math
import os
import time
from typing import List, Optional

import numpy as np
import pandas as pd
from rex import ResourceX

from hercules.resource.resource_utilities import (
    plot_spatial_map,
    plot_timeseries,
)
from hercules.utilities import hercules_float_type


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

    if year is not None and (start_date is not None or end_date is not None):
        raise ValueError(
            "Please provide either 'year' OR both 'start_date' and 'end_date', not both approaches."
        )

    if year is None and (start_date is None or end_date is None):
        raise ValueError("Please provide either 'year' OR both 'start_date' and 'end_date'.")

    if year is not None:
        file_years = [year]
        time_suffix = str(year)
        time_description = f"year {year}"
    else:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        if start_dt > end_dt:
            raise ValueError("start_date must be before end_date")

        file_years = list(range(start_dt.year, end_dt.year + 1))
        time_suffix = f"{start_date}_to_{end_date}".replace("-", "")
        time_description = f"period {start_date} to {end_date}"

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

    data_dict: dict = {}
    all_dataframes: dict = {var: [] for var in variables}

    try:
        for file_year in file_years:
            print(f"\nProcessing year {file_year}...")
            fp = f"/nrel/wtk/wtk-led/conus/v1.0.0/5min/wtk_conus_{file_year}.h5"

            with ResourceX(fp) as res:
                for var in variables:
                    print(f"  Downloading {var} for {file_year}...")
                    df_year = res.get_box_df(
                        var,
                        lat_lon_1=[llcrn_lat, llcrn_lon],
                        lat_lon_2=[urcrn_lat, urcrn_lon],
                    )

                    if start_date is not None and end_date is not None:
                        df_year = df_year.loc[start_date:end_date]

                    all_dataframes[var].append(df_year)

                if "coordinates" not in data_dict:
                    gids = df_year.columns.values
                    coordinates = res.lat_lon[gids]
                    df_coords = pd.DataFrame(coordinates, index=gids, columns=["lat", "lon"])
                    data_dict["coordinates"] = df_coords

        for var in variables:
            if all_dataframes[var]:
                print(f"Concatenating {var} data across {len(all_dataframes[var])} years...")
                data_dict[var] = pd.concat(all_dataframes[var], axis=0).sort_index()

                for col in data_dict[var].columns:
                    if pd.api.types.is_numeric_dtype(data_dict[var][col]):
                        data_dict[var][col] = data_dict[var][col].astype(hercules_float_type)

                all_dataframes[var].clear()

                output_file = os.path.join(
                    output_dir,
                    f"{filename_prefix}_{var}_{time_suffix}.feather",
                )
                data_dict[var].reset_index().to_feather(output_file)
                print(f"Saved {var} data to {output_file}")

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

    if plot_data and data_dict and "coordinates" in data_dict:
        coordinates_array = data_dict["coordinates"][["lat", "lon"]].values
        if plot_type == "timeseries":
            plot_timeseries(
                data_dict,
                variables,
                coordinates_array,
                f"{filename_prefix} WTK Data",
            )
        elif plot_type == "map":
            plot_spatial_map(
                data_dict,
                variables,
                coordinates_array,
                f"{filename_prefix} WTK Data",
            )

    return data_dict
