"""Resource downloading and processing utilities for Hercules.

This subpackage contains modules for downloading and processing wind and
solar resource data from multiple sources (NSRDB, WTK, Open-Meteo) and
for upsampling wind data for use in Hercules simulations.
"""

from .nsrdb_downloader import download_nsrdb_data
from .openmeteo_downloader import download_openmeteo_data
from .resource_utilities import (
    get_variable_colormap,
    get_variable_label,
    plot_spatial_map,
    plot_timeseries,
)
from .upsample_wind_data import upsample_wind_data
from .wtk_downloader import download_wtk_data

__all__ = [
    "download_nsrdb_data",
    "download_wtk_data",
    "download_openmeteo_data",
    "plot_timeseries",
    "plot_spatial_map",
    "get_variable_label",
    "get_variable_colormap",
    "upsample_wind_data",
]
