# Solar and Wind Resource Downloading and Upsampling

Functions are provided in the `hercules.resource.wind_solar_resource_downloading` module for downloading solar and wind time series data so they can be used as inputs to Hercules simulations. The `hercules.resource.upsample_wind_data` module is used to spatially interpolate downloaded wind data at specific wind turbine locations and temporally upsample the data.

## Overview

The `hercules.resource.wind_solar_resource_downloading` module contains functions for downloading solar data from the [National Solar Radiation Database (NSRDB)](https://nsrdb.nrel.gov), wind data from the [Wind Integration National Dataset (WIND) Toolkit](https://www.nrel.gov/grid/wind-toolkit), and solar and wind data from [Open-Meteo](https://open-meteo.com).

For downloaded wind data, the `hercules.resource.upsample_wind_data` module can be used to spatially interpolate the data at specific wind turbine locations and temporally upsample the data to represent realistic turbulent wind speeds. The downloaded and upsampled data can be saved as `.feather` files and used as inputs to Hercules simulations.

## Solar and Wind Resource Downloading Module

This section describes the functions for downloading solar and wind resource data in the `hercules.resource.wind_solar_resource_downloading` module.

### API Key

The functions for downloading NSRDB and WIND Toolkit data require an NLR API key, which can be obtained by visiting https://developer.nrel.gov/signup/. After receiving your API key, you must make a configuration file at ~/.hscfg containing the following:
```
hs_endpoint = https://developer.nrel.gov/api/hsds
hs_api_key = YOUR_API_KEY_GOES_HERE
```

More information can be found at: https://github.com/NREL/hsds-examples. An API key is not needed for downloading Open-Meteo data.

### Output Format

For each resource dataset, the downloaded data are returned as a dictionary of pandas DataFrames with `.feather` files saved for each DataFrame.

The dictionary key `coordinates` and a corresponding `.feather` file contain a DataFrame with columns `index`, `lat`, and `lon` describing the lat/lon coordinates of each grid location index.

For each variable downloaded, the dictionary key given by the variable name and a corresponding `.feather` file contain a DataFrame with a `time_index` column, containing the time in UTC, and columns corresponding to each grid location index containing the time series data for the variable.

### NSRDB Solar Data

The function `download_nsrdb_data` is used to download historical global horizontal irradiance (GHI), direct normal irradiance (DNI), and diffuse horizontal irradiance (DHI) time series data at a grid of coordinates from the National Solar Radiation Database (NSRDB). By default, data are downloaded from the [GOES Conus PSM v4](https://developer.nrel.gov/docs/solar/nsrdb/nsrdb-GOES-conus-v4-0-0-download/) dataset, which includes data for the continental US for 2018 to the present and has a spatial resolution of 2 km and temporal resolution of 5 minutes. However, [other NSRDB datasets](https://developer.nrel.gov/docs/solar/nsrdb/) can be used as well.

Arguments to the `download_nsrdb_data` function used to specify the data to download are as follows:
- `target_lat`: The latitude of the center of the grid of points for which data are requested.
- `target_lon`: The longitude of the center of the grid of points for which data are requested.
- `year`: The year for which data are requested.
- `start_date`: If `year` is not used, the specific start date for which data are requested.
- `end_date`: If `year` is not used, the specific end date for which data are requested.
- `variables`: List of variables to download. Defaults to ["ghi", "dni", "dhi", "wind_speed", "air_temperature"].
- `nsrdb_dataset_path`:  Path name of NSRDB dataset. Available datasets are described [here](https://developer.nrel.gov/docs/solar/nsrdb/) and path names can be identified [here](https://data.openei.org/s3_viewer?bucket=nrel-pds-nsrdb). Defaults to the GOES Conus v4.0.0 dataset: "/nrel/nsrdb/GOES/conus/v4.0.0".
- `nsrdb_filename_prefix`: File name prefix for the NSRDB HDF5 files in the format "{nsrdb_filename_prefix}_{year}.h5". Information about file names can be found [here](https://data.openei.org/s3_viewer?bucket=nrel-pds-nsrdb). Defaults to "nsrdb_conus".
- `coord_delta`: Coordinate delta for bounding box defining grid of points for which data are requested. Bounding box is defined as target_lat +/- coord_delta and target_lon +/- coord_delta. Defaults to 0.1 degrees.

### WIND Toolkit Wind Data

The function `download_wtk_data` is used to download historical wind data from the [WIND Toolkit Long-term Ensemble Dataset (WTK-LED)](https://www.nrel.gov/grid/wind-toolkit). WTK-LED data are available at US offshore and land-based locations and are provided at a spatial resolution of 2 km and a temporal resolution of 5 minutes for years 2018 through 2020. Available variables include wind speed, wind direction, and turbulent kinetic energy at multiple heights. The full list of available variables can be found [here](https://developer.nrel.gov/docs/wind/wind-toolkit/wtk-conus-5min-v2-0-0-download/).

Arguments to the `download_wtk_data` function used to specify the data to download are as follows:
- `target_lat`: The latitude of the center of the grid of points for which data are requested.
- `target_lon`: The longitude of the center of the grid of points for which data are requested.
- `year`: The year for which data are requested.
- `start_date`: If `year` is not used, the specific start date for which data are requested.
- `end_date`: If `year` is not used, the specific end date for which data are requested.
- `variables`: List of variables to download. Defaults to ["windspeed_100m", "winddirection_100m"].
- `coord_delta`: Coordinate delta for bounding box defining grid of points for which data are requested. Bounding box is defined as target_lat +/- coord_delta and target_lon +/- coord_delta. Defaults to 0.1 degrees.

### Open-Meteo Solar and Wind Data

The function `download_openmeteo_data` is used to download historical solar and wind data from the [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api). Data are available at a temporal resolution of 15 minutes for the year 2016 through 15 days from the present (i.e., a 15-day forecast). The spatial resolution varies with latitude, but at ~35 degrees latitude, the grid cell resolution is approximately 0.027 degrees latitude (~2.4 km in the N-S direction) and 0.0333 degrees longitude (~3.7km in the E-W direction). Available variables include wind speed and wind direction at a height of 80 m, temperature at 2 m, instant shortwave radiation, instant diffuse radiation, and instant direct normal irradiance. More information can be found [here](https://open-meteo.com/en/docs/historical-forecast-api).

Note that in contrast to the NSRDB and WIND Toolkit downloading functions, the specific coordinates at which data are requested must be provided instead of specifying the area of interest as a bounding box. Data will be returned for the nearest weather grid points to the requested coordinates.

Arguments to the `download_openmeteo_data` function used to specify the data to download are as follows:
- `target_lat`: The latitude or list of latitudes for which data are requested.
- `target_lon`: The longitude or list of longitudes for which data are requested.
- `year`: The year for which data are requested.
- `start_date`: If `year` is not used, the specific start date for which data are requested.
- `end_date`: If `year` is not used, the specific end date for which data are requested.
- `variables`: List of variables to download. Defaults to ["wind_speed_80m", "wind_direction_80m", "temperature_2m", "shortwave_radiation_instant", "diffuse_radiation_instant", "direct_normal_irradiance_instant"].
- `remove_duplicate_coords`: Whether to remove duplicate coordinates when returning the requested data. Duplicate coordinates can arise if the same weather grid point is the nearest point to multiple requested coordinates. Defaults to `True`.

## Wind Data Upsampling Module

After downloading wind data from WIND Toolkit or Open-Meteo, the `hercules.resource.upsample_wind_data` module can be used to spatially interpolate wind speeds and directions from the grid of downloaded points to specific wind turbine locations. The spatially interpolated wind speeds and directions are then upsampled to the desired temporal resolution and realistic turbulence is added to the wind speed time series. The upsampled data are then saved in the format used for wind inputs to Hercules simulations.

### Spatial Interpolation Overview

Both wind speed and direction at the specified wind turbine locations are spatially interpolated from the grid of locations for which data are downloaded using the [Clough-Tocher interpolation method](https://docs.scipy.org/doc//scipy-1.9.2/reference/generated/scipy.interpolate.CloughTocher2DInterpolator.html). This method produces a smooth, continuous surface that includes the original grid values and is expected to result in more realistic values than simple bilinear interpolation. It can also be applied to irregular grids of downloaded data.

### Temporal Upsampling Overview

After spatially interpolating the downloaded wind data, the time series of wind speed and wind direction are upsampled from the original temporal resolution (e.g., 5 minutes for WIND Toolkit and 15 minutes for Open-Meteo data) to the desired resolution (e.g., 1 second). This is accomplished by applying the discrete Fourier transform (DFT) to the original time series, increasing the length of the frequency-domain signal to match the desired temporal resolution by adding zeros above the Nyquist frequency, then applying the inverse DFT. The result is a smooth upsampled time series with no additional frequency content beyond what is present in the original signal.

### Turbulence Model

Because high-frequency turbulent fluctuations in wind speed are important to consider when simulating wind turbine power production, zero-mean stochastic turbulence is added to the upsampled wind speeds at each location. Stochastic turbulence is generated using the Kaimal turbulence spectrum, as defined in the IEC 61400-1 design standard. The generated turbulence is then scaled to achieve wind speed-dependent turbulence intensity (TI) values based on the normal turbulence model defined in the IEC 61400-1 standard, in which TI decreases as wind speed increases. Specifically, the upsampled wind speed value at each time sample is used to determine the TI, and the turbulence value corresponding to that time sample is scaled accordingly.

However, rather than using the specific TI magnitudes defined in the IEC standard, the entire stochastic turbulence signal is scaled to achieve a user-specified TI at the provided reference wind speed. In other words, the user specifies the desired TI at a reference wind speed, but the *relative* change in TI as a function of wind speed is based on the IEC normal turbulence model.

Note that in the current implementation, independent stochastic turbulence is generated at each upsampled location; spatial coherence is not modeled.

### Wind Data Upsampling Function

The function `upsample_wind_data` is used to perform the above-mentioned steps and return the upsampled wind speeds and directions at each upsampled location as a pandas DataFrame, which is also saved as a `.feather` file.

Arguments to the `upsample_wind_data` function used to specify the upsampling are as follows:
- `ws_data_filepath`: Filepath to the `.feather` file containing raw downloaded wind speed data saved by the `download_wtk_data` or `download_openmeteo_data` functions in the `wind_solar_resource_downloading` module.
- `wd_data_filepath`: Filepath to the `.feather` file containing raw downloaded wind direction data saved by the `download_wtk_data` or `download_openmeteo_data` functions in the `wind_solar_resource_downloading` module.
- `coords_filepath`: Filepath to the `.feather` file containing the coordinates corresponding to the downloaded wind data saved by the `download_wtk_data` or `download_openmeteo_data` functions in the `wind_solar_resource_downloading` module.
- `x_locs_upsample`: The "x" (Easting) locations of the desired upsampled locations (e.g., corresponding to turbine locations) relative to the provided origin coordinates in meters.
- `y_locs_upsample`: The "y" (Northing) locations of the desired upsampled locations (e.g., corresponding to turbine locations) relative to the provided origin coordinates in meters.
- `origin_lat`: The "origin" latitude corresponding to a `y_locs_upsample` location of 0.
- `origin_lon`: The "origin" longitude corresponding to a `x_locs_upsample` location of 0.
- `timestep_upsample`: Time step of upsampled wind time series in seconds. Defaults to 1 second.
- `turbulence_Uhub`: Mean hub-height wind speed to use for the Kaimal turbulence spectrum (m/s). If `None`, the mean wind speed from the interpolated upsample locations will be used. Defaults to `None`.
- `turbulence_L`: The turbulence length scale to use for the Kaimal turbulence spectrum (m). Defaults to 340.2 m, the value specified in the IEC standard.
- `TI_ref`: The reference TI that will be assigned at the reference wind speed `TI_ws_ref`. Defaults to 0.1.
- `TI_ws_ref`: The reference wind speed at which the reference TI `TI_ref` is defined (m/s). Defaults to 8 m/s.
- `save_individual_wds`: If `True`, upsampled wind directions will be saved in the output for each upsampled location. If `False`, only the mean wind direction over all locations will be saved. Defaults to `False`.

### Output Format

The function `upsample_wind_data` returns a pandas DataFrame containing the upsampled wind time series and saves the DataFrame as a `.feather` file. This DataFrame is in the format used for Hercules wind plant simulation inputs. An example illustrating the DataFrame columns is shown below for the case where `save_individual_wds` is `True`. Note that the suffixes "000", "001", etc. correspond to the locations specified in `x_locs_upsample` and `y_locs_upsample` (in order), and the `time` column contains the number of seconds from the start of the time series.

| time | time_utc | ws_000 | wd_000 | ws_001 | wd_001 | ws_002 | ...
|-----|-----|-----|-----|-----|-----|-----|-----|
| 0.0 | 2020-01-01 00:00:00+00:00 | 5.7 | 256.2 | 5.7 | 256.0 | 6.4 | ... |
| 1.0 | 2020-01-01 00:00:01+00:00 | 5.4 | 256.1 | 5.9 | 255.9 | 6.4 | ... |
| 2.0 | 2020-01-01 00:00:02+00:00 | 5.7 | 256.0 | 5.8 | 255.8 | 5.7 | ... |
| 3.0 | 2020-01-01 00:00:03+00:00 | 6.5 | 255.9 | 5.0 | 255.7 | 6.5 | ... |
| ... | ... | ... | ... | ... | ... | ... | ... |

On the other hand, for the case where `save_individual_wds` is `False`, an example DataFrame is provided below.

| time | time_utc | wd_mean | ws_000 | ws_001 | ws_002 | ...
|-----|-----|-----|-----|-----|-----|-----|
| 0.0 | 2020-01-01 00:00:00+00:00 | 255.8 | 5.7 | 5.7 | 6.4 | ... |
| 1.0 | 2020-01-01 00:00:01+00:00 | 255.8 | 5.4 | 5.9 | 6.4 | ... |
| 2.0 | 2020-01-01 00:00:02+00:00 | 255.7 | 5.7 | 5.8 | 5.7 | ... |
| 3.0 | 2020-01-01 00:00:03+00:00 | 255.6 | 6.5 | 5.0 | 6.5 | ... |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |
