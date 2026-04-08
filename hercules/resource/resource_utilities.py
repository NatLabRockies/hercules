"""Shared utilities for resource data downloading and visualization.

This module provides common functions used by the NSRDB, WTK, and Open-Meteo
resource downloaders, including time parameter validation, data I/O,
elapsed time formatting, and plotting.
"""

import math
import os
import time
from typing import List, Optional

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from hercules.utilities import hercules_float_type
from rex import ResourceX
from scipy.interpolate import griddata


def validate_time_params(
    year: Optional[int],
    start_date: Optional[str],
    end_date: Optional[str],
) -> dict:
    """Validate time parameters and compute derived time information.

    Ensures that either ``year`` or both ``start_date`` and ``end_date`` are
    provided (but not both). Returns file_years, time_suffix,
    time_description, and resolved start_date/end_date values.

    Args:
        year (int, optional): Year of data to download.
        start_date (str, optional): Start date in 'YYYY-MM-DD' format.
        end_date (str, optional): End date in 'YYYY-MM-DD' format.

    Returns:
        dict: Dictionary with keys:
            - file_years (list[int]): Years spanned by the time range.
            - time_suffix (str): Filename-safe suffix for the time range.
            - time_description (str): Human-readable time range description.
            - start_date (str): Resolved start date string.
            - end_date (str): Resolved end date string.

    Raises:
        ValueError: If the parameter combination is invalid or if
            start_date > end_date.
    """
    if year is not None and (start_date is not None or end_date is not None):
        raise ValueError(
            "Please provide either 'year' OR both 'start_date' and 'end_date', not both approaches."
        )

    if year is None and (start_date is None or end_date is None):
        raise ValueError("Please provide either 'year' OR both 'start_date' and 'end_date'.")

    if year is not None:
        return {
            "file_years": [year],
            "time_suffix": str(year),
            "time_description": f"year {year}",
            "start_date": f"{year}-01-01",
            "end_date": f"{year}-12-31",
        }

    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    if start_dt > end_dt:
        raise ValueError("start_date must be before end_date")

    return {
        "file_years": list(range(start_dt.year, end_dt.year + 1)),
        "time_suffix": f"{start_date}_to_{end_date}".replace("-", ""),
        "time_description": f"period {start_date} to {end_date}",
        "start_date": start_date,
        "end_date": end_date,
    }


def create_bounding_box(
    target_lat: float,
    target_lon: float,
    coord_delta: float,
) -> tuple:
    """Create a bounding box from a center point and coordinate delta.

    Args:
        target_lat (float): Center latitude coordinate.
        target_lon (float): Center longitude coordinate.
        coord_delta (float): Half-width of the bounding box in degrees.

    Returns:
        tuple: (llcrn_lat, llcrn_lon, urcrn_lat, urcrn_lon) lower-left and
            upper-right corners of the bounding box.
    """
    return (
        target_lat - coord_delta,
        target_lon - coord_delta,
        target_lat + coord_delta,
        target_lon + coord_delta,
    )


def download_nrel_rex_data(
    dataset_path: str,
    dataset_filename_prefix: str,
    source_name: str,
    target_lat: float,
    target_lon: float,
    variables: List[str],
    bounding_box: tuple,
    file_years: List[int],
    start_date: Optional[str],
    end_date: Optional[str],
    output_dir: str,
    filename_prefix: str,
    time_suffix: str,
    time_description: str,
    os_error_hint: str = "This could be caused by an invalid API key or date range.",
) -> dict:
    """Download data from an NLR rex-based dataset (NSRDB or WTK).

    Handles the complete download workflow: fetching data via ResourceX for
    each year, concatenating across years, converting to the hercules float
    type, and saving to feather format.

    Args:
        dataset_path (str): Base path of the dataset on the NLR HSDS server.
        dataset_filename_prefix (str): Filename prefix for the HDF5 files
            in the format ``{dataset_filename_prefix}_{year}.h5``.
        source_name (str): Human-readable data source name (e.g., "NSRDB",
            "WTK") used in log messages.
        target_lat (float): Target latitude coordinate.
        target_lon (float): Target longitude coordinate.
        variables (list[str]): List of variables to download.
        bounding_box (tuple): (llcrn_lat, llcrn_lon, urcrn_lat, urcrn_lon)
            corners of the spatial bounding box.
        file_years (list[int]): List of years to download.
        start_date (str, optional): Start date for filtering. If None, no
            date filtering is applied.
        end_date (str, optional): End date for filtering. If None, no date
            filtering is applied.
        output_dir (str): Directory to save output feather files.
        filename_prefix (str): Prefix for output filenames.
        time_suffix (str): Suffix for output filenames encoding the time
            range.
        time_description (str): Human-readable time range for log messages.
        os_error_hint (str, optional): Additional context for OSError
            messages. Defaults to "This could be caused by an invalid API
            key or date range."

    Returns:
        dict: Dictionary containing DataFrames for each variable and a
            "coordinates" key with lat/lon data.

    Raises:
        OSError: If there is an error accessing the NLR HSDS server.
    """
    llcrn_lat, llcrn_lon, urcrn_lat, urcrn_lon = bounding_box

    print(f"Downloading {source_name} data for {time_description}")
    print(f"Target coordinates: ({target_lat}, {target_lon})")
    print(f"Bounding box: ({llcrn_lat}, {llcrn_lon}) to ({urcrn_lat}, {urcrn_lon})")
    print(f"Variables: {variables}")
    print(f"Years to process: {file_years}")

    t0 = time.time()

    data_dict = {}
    all_dataframes = {var: [] for var in variables}

    try:
        for file_year in file_years:
            print(f"\nProcessing year {file_year}...")
            fp = f"{dataset_path}/{dataset_filename_prefix}_{file_year}.h5"

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

                save_variable_to_feather(
                    data_dict[var],
                    output_dir,
                    filename_prefix,
                    var,
                    time_suffix,
                )

        save_coords_to_feather(
            data_dict["coordinates"],
            output_dir,
            filename_prefix,
            time_suffix,
        )

    except OSError as e:
        print(f"Error downloading {source_name} data: {e}")
        print(os_error_hint)
        raise
    except Exception as e:
        print(f"Error downloading {source_name} data: {e}")
        raise

    print_elapsed_time(t0, source_name)

    return data_dict


def save_variable_to_feather(
    df: pd.DataFrame,
    output_dir: str,
    filename_prefix: str,
    var_name: str,
    time_suffix: str,
) -> str:
    """Save a variable DataFrame to feather format.

    Args:
        df (pd.DataFrame): DataFrame to save.
        output_dir (str): Directory to save the file in.
        filename_prefix (str): Prefix for the filename.
        var_name (str): Variable name included in the filename.
        time_suffix (str): Time range suffix included in the filename.

    Returns:
        str: Path to the saved feather file.
    """
    output_file = os.path.join(output_dir, f"{filename_prefix}_{var_name}_{time_suffix}.feather")
    df.reset_index().to_feather(output_file)
    print(f"Saved {var_name} data to {output_file}")
    return output_file


def save_coords_to_feather(
    df_coords: pd.DataFrame,
    output_dir: str,
    filename_prefix: str,
    time_suffix: str,
) -> str:
    """Save a coordinates DataFrame to feather format.

    Args:
        df_coords (pd.DataFrame): Coordinates DataFrame with 'lat' and
            'lon' columns.
        output_dir (str): Directory to save the file in.
        filename_prefix (str): Prefix for the filename.
        time_suffix (str): Time range suffix included in the filename.

    Returns:
        str: Path to the saved feather file.
    """
    coords_file = os.path.join(output_dir, f"{filename_prefix}_coords_{time_suffix}.feather")
    df_coords.reset_index().to_feather(coords_file)
    print(f"Saved coordinates to {coords_file}")
    return coords_file


def print_elapsed_time(t0: float, source_name: str) -> None:
    """Print elapsed time since t0 in minutes:seconds format.

    Args:
        t0 (float): Start time from ``time.time()``.
        source_name (str): Name of the data source for the log message.
    """
    total_time = (time.time() - t0) / 60
    decimal_part = math.modf(total_time)[0] * 60
    print(
        f"{source_name} download completed in "
        f"{int(np.floor(total_time))}:{int(np.round(decimal_part, 0)):02d}"
        " minutes"
    )


def dispatch_plots(
    data_dict: dict,
    variables: List[str],
    plot_data: bool,
    plot_type: str,
    title: str,
) -> None:
    """Dispatch plotting based on the plot_data flag and plot_type.

    Args:
        data_dict (dict): Dictionary containing DataFrames for each variable
            and a "coordinates" key.
        variables (list[str]): List of variable names to plot.
        plot_data (bool): Whether to create plots.
        plot_type (str): Type of plot: 'timeseries' or 'map'.
        title (str): Title for the plots.
    """
    if plot_data and data_dict and "coordinates" in data_dict:
        coordinates_array = data_dict["coordinates"][["lat", "lon"]].values
        if plot_type == "timeseries":
            plot_timeseries(data_dict, variables, coordinates_array, title)
        elif plot_type == "map":
            plot_spatial_map(data_dict, variables, coordinates_array, title)


# ---------------------------------------------------------------------------
# Plotting functions
# ---------------------------------------------------------------------------


def plot_timeseries(
    data_dict: dict,
    variables: List[str],
    coordinates: np.ndarray,
    title: str,
):
    """Create time-series plots for the downloaded data.

    Args:
        data_dict (dict): Dictionary containing DataFrames for each variable.
        variables (list[str]): List of variables to plot.
        coordinates (np.ndarray): Array of coordinates for the data points.
        title (str): Title for the plots.
    """
    n_vars = len(variables)
    if n_vars == 0:
        return

    fig, axes = plt.subplots(n_vars, 1, figsize=(12, 4 * n_vars), sharex=True)
    if n_vars == 1:
        axes = [axes]

    for i, var in enumerate(variables):
        if var in data_dict:
            df = data_dict[var]

            for col in df.columns:
                axes[i].plot(df.index, df[col], alpha=0.7, linewidth=0.8)

            axes[i].set_ylabel(get_variable_label(var))
            axes[i].set_title(f"{var.replace('_', ' ').title()}")
            axes[i].grid(True, alpha=0.3)

    axes[-1].set_xlabel("Time")
    plt.suptitle(f"{title} - Time Series", fontsize=14, fontweight="bold")
    plt.tight_layout()


def plot_spatial_map(
    data_dict: dict,
    variables: List[str],
    coordinates: np.ndarray,
    title: str,
):
    """Create spatial maps showing the mean values across the region.

    Args:
        data_dict (dict): Dictionary containing DataFrames for each variable.
        variables (list[str]): List of variables to plot.
        coordinates (np.ndarray): Array of coordinates for the data points.
        title (str): Title for the plots.
    """
    n_vars = len(variables)
    if n_vars == 0:
        return

    n_cols = min(2, n_vars)
    n_rows = math.ceil(n_vars / n_cols)

    plt.figure(figsize=(8 * n_cols, 6 * n_rows))

    for i, var in enumerate(variables):
        if var in data_dict:
            df = data_dict[var]

            lats = coordinates[:, 0]
            lons = coordinates[:, 1]

            mean_values = df.mean(axis=0).values

            ax = plt.subplot(n_rows, n_cols, i + 1, projection=ccrs.PlateCarree())

            ax.add_feature(cfeature.COASTLINE, alpha=0.5)
            ax.add_feature(cfeature.BORDERS, linestyle=":", alpha=0.5)
            ax.add_feature(
                cfeature.LAND,
                edgecolor="black",
                facecolor="lightgray",
                alpha=0.3,
            )
            ax.add_feature(cfeature.OCEAN, facecolor="lightblue", alpha=0.3)

            if len(lats) > 4:
                grid_lon = np.linspace(min(lons), max(lons), 50)
                grid_lat = np.linspace(min(lats), max(lats), 50)
                grid_lon, grid_lat = np.meshgrid(grid_lon, grid_lat)

                try:
                    grid_values = griddata(
                        (lons, lats),
                        mean_values,
                        (grid_lon, grid_lat),
                        method="cubic",
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
                    sc = ax.scatter(
                        lons,
                        lats,
                        c=mean_values,
                        s=100,
                        cmap=get_variable_colormap(var),
                        transform=ccrs.PlateCarree(),
                    )
                    plt.colorbar(
                        sc,
                        ax=ax,
                        orientation="vertical",
                        label=get_variable_label(var),
                        shrink=0.8,
                    )
            else:
                sc = ax.scatter(
                    lons,
                    lats,
                    c=mean_values,
                    s=100,
                    cmap=get_variable_colormap(var),
                    transform=ccrs.PlateCarree(),
                )
                plt.colorbar(
                    sc,
                    ax=ax,
                    orientation="vertical",
                    label=get_variable_label(var),
                    shrink=0.8,
                )

            ax.scatter(
                lons,
                lats,
                c="black",
                s=20,
                transform=ccrs.PlateCarree(),
                alpha=0.8,
            )

            ax.set_title(f"{var.replace('_', ' ').title()}")

            ax.set_xticks(np.linspace(min(lons), max(lons), 5))
            ax.set_yticks(np.linspace(min(lats), max(lats), 5))
            ax.set_xticklabels(
                [f"{lon:.2f}°" for lon in np.linspace(min(lons), max(lons), 5)],
                fontsize=8,
            )
            ax.set_yticklabels(
                [f"{lat:.2f}°" for lat in np.linspace(min(lats), max(lats), 5)],
                fontsize=8,
            )
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")

    plt.suptitle(
        f"{title} - Spatial Distribution (Time-Averaged)",
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()


# ---------------------------------------------------------------------------
# Variable metadata helpers
# ---------------------------------------------------------------------------


def get_variable_label(variable: str) -> str:
    """Get appropriate axis label with units for a variable.

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
        "wind_speed_80m": "Wind Speed at 80m (m/s)",
        "windspeed_80m": "Wind Speed at 80m (m/s)",
        "wind_direction_80m": "Wind Direction at 80m (°)",
        "winddirection_80m": "Wind Direction at 80m (°)",
        "temperature_2m": "Temperature at 2m (°C)",
        "shortwave_radiation_instant": "Shortwave Radiation (W/m²)",
        "diffuse_radiation_instant": "Diffuse Radiation (W/m²)",
        "direct_normal_irradiance_instant": "Direct Normal Irradiance (W/m²)",
    }
    return labels.get(variable, variable.replace("_", " ").title())


def get_variable_colormap(variable: str) -> str:
    """Get appropriate matplotlib colormap name for a variable.

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
