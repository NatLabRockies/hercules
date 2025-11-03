"""Generate solar input data with 1-minute time steps.

This script generates deterministic solar irradiance data over a specified time period.
The data includes a realistic daily solar cycle with cloud effects and is saved as a
pickle file (.p) designed to be reproducible across different machines.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def generate_solar_input(
    num_time_steps,
    time_step_minutes,
    latitude,
    longitude,
    date,
    seed,
    output_filename,
):
    """Generate solar input data with realistic daily cycle and cloud effects.

    This function generates deterministic solar irradiance data over a specified
    time period. The data includes a realistic daily solar cycle with cloud effects
    and is saved as a pandas DataFrame to a pickle file (.p).

    Args:
        num_time_steps (int): Number of time steps to generate.
        time_step_minutes (int): Time step in minutes.
        latitude (float): Latitude of the solar site in degrees.
        longitude (float): Longitude of the solar site in degrees.
        date (datetime): Date for the solar calculations.
        seed (int): Random seed for reproducibility.
        output_filename (str): Name of the output pickle file.

    """
    # Set random seed for reproducibility
    np.random.seed(seed)

    # Generate time arrays
    time_minutes = np.arange(num_time_steps) * time_step_minutes
    start_time = datetime(2020, 3, 1, 5, 0, 0)
    time_utc = [start_time + timedelta(minutes=int(t)) for t in time_minutes]

    # Calculate solar position and irradiance for each time step
    ghi_data = np.zeros(num_time_steps)  # Global Horizontal Irradiance
    dni_data = np.zeros(num_time_steps)  # Direct Normal Irradiance
    dhi_data = np.zeros(num_time_steps)  # Diffuse Horizontal Irradiance
    temp_data = np.zeros(num_time_steps)  # Temperature
    wind_speed_data = np.zeros(num_time_steps)  # Wind Speed

    for i, (time_min, utc_time) in enumerate(zip(time_minutes, time_utc)):
        # Calculate solar position (simplified)
        hour = utc_time.hour + utc_time.minute / 60.0
        day_of_year = utc_time.timetuple().tm_yday

        # Solar declination (simplified)
        declination = 23.45 * np.sin(np.radians(360 * (day_of_year - 80) / 365))

        # Hour angle
        hour_angle = 15 * (hour - 12)

        # Solar altitude (simplified)
        solar_altitude = np.arcsin(
            np.sin(np.radians(latitude)) * np.sin(np.radians(declination))
            + np.cos(np.radians(latitude))
            * np.cos(np.radians(declination))
            * np.cos(np.radians(hour_angle))
        )

        # Convert to degrees
        solar_altitude_deg = np.degrees(solar_altitude)

        # Calculate clear sky irradiance
        if solar_altitude_deg > 0:
            # Clear sky GHI (simplified model)
            clear_ghi = 1000 * np.sin(np.radians(solar_altitude_deg)) ** 1.2

            # Clear sky DNI (simplified)
            clear_dni = 900 * np.sin(np.radians(solar_altitude_deg)) ** 0.8

            # Clear sky DHI (simplified)
            clear_dhi = clear_ghi - clear_dni * np.sin(np.radians(solar_altitude_deg))

            # Add cloud effects
            # Create a cloud pattern that varies throughout the day
            cloud_base = 0.3 + 0.4 * np.sin(np.radians(hour * 15))  # Base cloudiness
            cloud_variation = 0.2 * np.sin(np.radians(hour * 30 + i * 0.5))  # Fast variation
            cloud_noise = 0.1 * np.random.randn()  # Random noise

            cloud_factor = np.clip(cloud_base + cloud_variation + cloud_noise, 0.0, 1.0)

            # Apply cloud effects
            ghi_data[i] = clear_ghi * (1 - 0.7 * cloud_factor)
            dni_data[i] = clear_dni * (1 - 0.9 * cloud_factor)
            # Diffuse increases with clouds
            dhi_data[i] = clear_dhi + clear_ghi * 0.3 * cloud_factor

            # Temperature (simplified model)
            base_temp = 20 + 10 * np.sin(np.radians(hour * 15 - 90))  # Daily cycle
            temp_data[i] = base_temp + 5 * np.random.randn()

            # Wind speed (simplified model)
            base_wind = 2.0 + 1.0 * np.sin(np.radians(hour * 15))  # Daily cycle
            wind_speed_data[i] = base_wind + 0.5 * np.random.randn()
        else:
            # Night time - no solar irradiance
            ghi_data[i] = 0.0
            dni_data[i] = 0.0
            dhi_data[i] = 0.0
            temp_data[i] = 15 + 5 * np.random.randn()  # Cooler at night
            wind_speed_data[i] = 1.5 + 0.5 * np.random.randn()  # Lower wind at night

    # Create the output DataFrame
    solar_data = pd.DataFrame(
        {
            "SRRL BMS Global Horizontal Irradiance (W/m²_irr)": ghi_data,
            "SRRL BMS Direct Normal Irradiance (W/m²_irr)": dni_data,
            "SRRL BMS Diffuse Horizontal Irradiance (W/m²_irr)": dhi_data,
            "SRRL BMS Dry Bulb Temperature (°C)": temp_data,
            "SRRL BMS Wind Speed at 19' (m/s)": wind_speed_data,
            "time_utc": time_utc,
        }
    )

    # Save to pickle file
    solar_data.to_pickle(output_filename)


def main():
    """Generate solar input data and save to pickle file."""
    print("Generating solar input data...")

    # Generate the solar data
    generate_solar_input(
        num_time_steps=721,  # 12 hours
        time_step_minutes=1,
        latitude=40.0,  # Example latitude (Denver area)
        longitude=-105.0,  # Example longitude
        date=datetime(2020, 6, 15),  # Summer solstice
        seed=42,
        output_filename="inputs/solar_input.p",
    )


if __name__ == "__main__":
    main()
