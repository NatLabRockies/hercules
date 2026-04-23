"""Shared utilities for resource data downloading and visualization.

This module provides common plotting and labeling functions used by the
NSRDB, WTK, and Open-Meteo resource downloaders. Additional shared
utilities (e.g., time parameter validation, data I/O) can be added in
future changes as the resource modules are further modularized.
"""

import math
from typing import List

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata


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
            ax.add_feature(cfeature.LAND, edgecolor="black", facecolor="lightgray", alpha=0.3)
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

            ax.scatter(lons, lats, c="black", s=20, transform=ccrs.PlateCarree(), alpha=0.8)

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
