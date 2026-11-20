# Post-process the outputs of the wind, storage, and LMP example with hercules.analysis

from hercules import HerculesOutput
from hercules.analysis import energy_market, plotting, storage, utilities

ho = HerculesOutput("outputs/hercules_output.h5")

# Limit export to the interconnect first; energy and revenue use the POI-limited columns
utilities.add_POI_limited_columns(ho)

energy = utilities.compute_energy_total_MWh(ho)
revenue = energy_market.compute_revenue_RT_total(ho)
revenue_battery = energy_market.compute_revenue_RT_total(ho, "analysis.battery.power_POI_limited")
print(f"Energy exported (POI limited): {energy:.2f} MWh")
print(f"Plant capacity factor: {utilities.compute_capacity_factor(ho):.3f}")
print(f"Real-time revenue, plant: ${revenue:,.0f}")
print(f"Real-time revenue, battery (net of charging): ${revenue_battery:,.0f}")
print(f"Battery energy discharged: {storage.compute_energy_discharged_total_MWh(ho):.2f} MWh")
print(f"Battery equivalent full cycles: {storage.compute_cycle_count_equivalent_total(ho):.3f}")

# Interactive time series: one row per entry, then plant export and LMP rows
plotting.plot_timeseries_plotly(
    ho,
    ["wind_farm.power", ["battery.power", "battery.power_setpoint"], "battery.SOC"],
    title="Example 05: wind and storage with LMP",
    save_file="outputs/timeseries.html",
)
print("Saved outputs/timeseries.html")
