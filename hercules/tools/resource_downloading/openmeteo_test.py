import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
import ssl
import requests
import warnings

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
params = {
	"latitude": 36.607322,
	"longitude": -97.487643,
	"start_date": "2024-01-01",
	"end_date": "2024-01-02",
	"minutely_15": ["wind_speed_80m", "temperature_2m", "shortwave_radiation_instant", "diffuse_radiation_instant", "direct_normal_irradiance_instant"],
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
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
    
    # Create a new session with SSL verification disabled
    cache_session_no_ssl = requests_cache.CachedSession('.cache', expire_after=3600)
    cache_session_no_ssl.verify = False
    retry_session_no_ssl = retry(cache_session_no_ssl, retries=5, backoff_factor=0.2)
    openmeteo_no_ssl = openmeteo_requests.Client(session=retry_session_no_ssl)
    
    responses = openmeteo_no_ssl.weather_api(url, params=params)
    print("API request successful with SSL verification disabled.")

# Process first location. Add a for-loop for multiple locations or weather models
response = responses[0]
print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
print(f"Elevation: {response.Elevation()} m asl")
print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

# Process minutely_15 data. The order of variables needs to be the same as requested.
minutely_15 = response.Minutely15()
minutely_15_wind_speed_80m = minutely_15.Variables(0).ValuesAsNumpy()
minutely_15_temperature_2m = minutely_15.Variables(1).ValuesAsNumpy()
minutely_15_shortwave_radiation_instant = minutely_15.Variables(2).ValuesAsNumpy()
minutely_15_diffuse_radiation_instant = minutely_15.Variables(3).ValuesAsNumpy()
minutely_15_direct_normal_irradiance_instant = minutely_15.Variables(4).ValuesAsNumpy()

minutely_15_data = {"date": pd.date_range(
	start = pd.to_datetime(minutely_15.Time(), unit = "s", utc = True),
	end = pd.to_datetime(minutely_15.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = minutely_15.Interval()),
	inclusive = "left"
)}

minutely_15_data["wind_speed_80m"] = minutely_15_wind_speed_80m
minutely_15_data["temperature_2m"] = minutely_15_temperature_2m
minutely_15_data["shortwave_radiation_instant"] = minutely_15_shortwave_radiation_instant
minutely_15_data["diffuse_radiation_instant"] = minutely_15_diffuse_radiation_instant
minutely_15_data["direct_normal_irradiance_instant"] = minutely_15_direct_normal_irradiance_instant

minutely_15_dataframe = pd.DataFrame(data = minutely_15_data)
print("\nMinutely15 data\n", minutely_15_dataframe)