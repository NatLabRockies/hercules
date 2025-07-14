import logging
from pathlib import Path

import numpy as np
import pandas as pd
from floris import FlorisModel
from hercules.amr_wind_standin import AMRWindStandin
from hercules.floris_standin import (
    construct_floris_from_amr_input,
    default_floris_dict,
    FlorisStandin,
)
from SEAS.federate_agent import FederateAgent

AMR_INPUT = Path(__file__).resolve().parent / "test_inputs" / "amr_input_florisstandin.inp"
AMR_EXTERNAL_DATA = Path(__file__).resolve().parent / "test_inputs" / "amr_standin_data.csv"
AMR_EXTERNAL_DATA_HET = Path(__file__).resolve().parent / "test_inputs" / "amr_standin_data_het.csv"

CONFIG = {
    "name": "floris_standin",
    "gridpack": {},
    "helics": {
        "deltat": 1.0,
        "subscription_topics": ["control"],
        "publication_topics": ["status"],
        "endpoints": [],
        "helicsport": None,
    },
    "publication_interval": 1,
    "endpoint_interval": 1,
    "starttime": 0,
    "stoptime": 10.0,
    "Agent": "floris_standin",
}


def test_construct_floris_from_amr_input():
    fmodel_test = construct_floris_from_amr_input(AMR_INPUT)
    assert isinstance(fmodel_test, FlorisModel)


def test_FlorisStandin_instantiation():
    # Check instantiates correctly
    floris_standin = FlorisStandin(CONFIG, AMR_INPUT)

    # Check inheritance
    assert isinstance(floris_standin, FederateAgent)
    assert isinstance(floris_standin, AMRWindStandin)

    # Get FLORIS equivalent, match layout and turbines
    fmodel_true = FlorisModel(default_floris_dict)
    fmodel_true.set(
        layout_x=floris_standin.fmodel.layout_x,
        layout_y=floris_standin.fmodel.layout_y,
        turbine_type=floris_standin.fmodel.core.farm.turbine_definitions,
    )

    assert fmodel_true.core.as_dict() == floris_standin.fmodel.core.as_dict()


def test_FlorisStandin_get_step_yaw_angles():
    floris_standin = FlorisStandin(CONFIG, AMR_INPUT, smoothing_coefficient=0.0)

    # Get FLORIS equivalent, match layout and turbines
    fmodel_true = FlorisModel(default_floris_dict)
    fmodel_true.set(
        layout_x=floris_standin.fmodel.layout_x,
        layout_y=floris_standin.fmodel.layout_y,
        turbine_type=floris_standin.fmodel.core.farm.turbine_definitions,
    )

    default_wind_direction = 240.0  # Matches default in FlorisStandin
    default_wind_speed = 8.0  # Matches default in FlorisStandin

    # Test with None yaw angles
    fs_ws, fs_wd, fs_tp, fs_twd, fs_tws = floris_standin.get_step(5.0)
    fmodel_true.set(wind_speeds=[default_wind_speed], wind_directions=[default_wind_direction])
    fmodel_true.run()
    fmodel_true_tp = fmodel_true.get_turbine_powers() / 1000 # kW expected

    assert fs_ws == default_wind_speed
    assert fs_wd == default_wind_direction
    assert fs_twd == [default_wind_direction] * 2
    # Check wind speeds are near (but below, due to rotor averaging) the default
    assert (0.5*default_wind_speed < np.array(fs_tws)).all()
    assert (np.array(fs_tws) < default_wind_speed).all()
    assert np.allclose(fs_tp, fmodel_true_tp.flatten().tolist())

    # Test with any "no value" yaw angles (should apply no yaw angle)
    fs_ws, fs_wd, fs_tp, fs_twd, fs_tws = floris_standin.get_step(5.0, yaw_angles=[-1000, 20])
    
    assert fs_ws == default_wind_speed
    assert fs_wd == default_wind_direction
    assert fs_twd == [default_wind_direction] * 2
    assert (0.5*default_wind_speed < np.array(fs_tws)).all()
    assert (np.array(fs_tws) < default_wind_speed).all()
    assert np.allclose(fs_tp, fmodel_true_tp.flatten().tolist())

    # Test with aligned turbines
    yaw_angles = [240.0, 240.0]
    fs_ws, fs_wd, fs_tp, fs_twd, fs_tws = floris_standin.get_step(5.0, yaw_angles)
    fmodel_true.set(wind_speeds=[default_wind_speed], wind_directions=[default_wind_direction])
    fmodel_true.run()
    fmodel_true_tp = fmodel_true.get_turbine_powers() / 1000 # kW expected

    assert np.allclose(fs_tp, fmodel_true_tp.flatten().tolist())

    # Test with misaligned turbines
    yaw_angles = [260.0, 230.0]
    fs_ws, fs_wd, fs_tp, fs_twd, fs_tws = floris_standin.get_step(5.0, yaw_angles)
    fmodel_true.set(wind_speeds=[default_wind_speed], wind_directions=[default_wind_direction])
    fmodel_true.run()  # Don't expect to work
    fmodel_true_tp = fmodel_true.get_turbine_powers() / 1000
    assert not np.allclose(fs_tp, fmodel_true_tp.flatten().tolist())

    # Correct yaw angles
    fmodel_true.set(yaw_angles=default_wind_direction - np.array([yaw_angles]))
    fmodel_true.run()
    fmodel_true_tp = fmodel_true.get_turbine_powers() / 1000 # kW expected
    assert np.allclose(fs_tp, fmodel_true_tp.flatten().tolist())

    # Test that yaw angles are maintained from the previous step if large misalignments are provided
    yaw_angles = [0.0, 10.0]
    _, _, fs_tp2, _, _ = floris_standin.get_step(5.0, yaw_angles)
    assert np.allclose(fs_tp, fs_tp2)
    assert np.allclose(
        default_wind_direction-floris_standin.fmodel.core.farm.yaw_angles,
        [260.0, 230.0]
    )

def test_FlorisStandin_get_step_power_setpoints(caplog):
    floris_standin = FlorisStandin(CONFIG, AMR_INPUT, smoothing_coefficient=0.0)

    # Get FLORIS equivalent, match layout and turbines
    fmodel_true = FlorisModel(default_floris_dict)
    fmodel_true.set(
        layout_x=floris_standin.fmodel.layout_x,
        layout_y=floris_standin.fmodel.layout_y,
        turbine_type=floris_standin.fmodel.core.farm.turbine_definitions,
    )

    default_wind_direction = 240.0  # Matches default in FlorisStandin
    default_wind_speed = 8.0  # Matches default in FlorisStandin

    # Test with power setpoints
    fs_ws, fs_wd, fs_tp, fs_twd, fs_tws = floris_standin.get_step(5.0, power_setpoints=[1e3, 1e3])
    fmodel_true.set(wind_speeds=[default_wind_speed], wind_directions=[default_wind_direction])
    fmodel_true.run() # don't expect to work
    fmodel_true_tp = fmodel_true.get_turbine_powers() / 1000
    assert not np.allclose(fs_tp, fmodel_true_tp.flatten().tolist())

    # Correct power setpoints
    fmodel_true.set(power_setpoints=np.array([[1e6, 1e6]]))
    fmodel_true.run()
    fmodel_true_tp = fmodel_true.get_turbine_powers() / 1000 # kW expected
    assert np.allclose(fs_tp, fmodel_true_tp.flatten().tolist())

    # Mixed power setpoints
    fs_ws, fs_wd, fs_tp, fs_twd, fs_tws = floris_standin.get_step(5.0, power_setpoints=[None, 1e3])
    fmodel_true.set(power_setpoints=np.array([[None, 1e6]]))
    fmodel_true.run()
    fmodel_true_tp = fmodel_true.get_turbine_powers() / 1000
    assert np.allclose(fs_tp, fmodel_true_tp.flatten().tolist())

    # Test warning raise with invalid combination of yaw angles and power setpoints
    with caplog.at_level(logging.WARNING):
        floris_standin.get_step(5.0, yaw_angles=[230.0, 240.0], power_setpoints=[1e3, 1e3])
    assert caplog.text != "" # Checking not empty
    caplog.clear()

    # Test with valid combination of yaw angles and power setpoints
    yaw_angles = [260.0, 240.0]
    power_setpoints = [None, 1e3]
    fs_ws, fs_wd, fs_tp, fs_twd, fw_tws = floris_standin.get_step(
        5.0,
        yaw_angles=yaw_angles,
        power_setpoints=power_setpoints
    )
    floris_power_setpoints = np.array([power_setpoints])
    floris_power_setpoints[0,1] *= 1e3 
    fmodel_true.set(
        yaw_angles=default_wind_direction - np.array([yaw_angles]),
        power_setpoints=floris_power_setpoints
    )
    fmodel_true.run()
    fmodel_true_tp = fmodel_true.get_turbine_powers() / 1000
    assert np.allclose(fs_tp, fmodel_true_tp.flatten().tolist())


def test_FlorisStandin_with_standin_data_yaw_angles():
    floris_standin = FlorisStandin(CONFIG, AMR_INPUT, AMR_EXTERNAL_DATA, smoothing_coefficient=0.0)

    yaw_angles_all = [
        [240.0, 240.0],
        [240.0, 240.0],  # Step up from 8 to 10 m/s
        [240.0, 240.0],
        [240.0, 240.0],  # Step back down to 8 m/s
        [240.0, 240.0],  # wd changes to 270.0 here
        [270.0, 270.0],  # change to match wd
        [270.0, 270.0],
        [250.0, 270.0],  # Apply simple wake steering
        [250.0, 270.0],
        [250.0, 270.0],
    ]

    # Initialize storage
    fs_ws_all = []
    fs_wd_all = []
    fs_tp_all = []
    fs_twd_all = []
    fs_tws_all = []
    for i, s in enumerate(np.arange(0, 10.0, 1.0)):
        fs_ws, fs_wd, fs_tp, fs_twd, fs_tws = floris_standin.get_step(
            s,
            yaw_angles=yaw_angles_all[i]
        )
        fs_ws_all.append(fs_ws)
        fs_wd_all.append(fs_wd)
        fs_tp_all.append(fs_tp)
        fs_twd_all.append(fs_twd)
        fs_tws_all.append(fs_tws)

    # Check standin data mapped over correctly
    assert fs_ws_all == floris_standin.standin_data.amr_wind_speed.to_list()
    assert fs_wd_all == floris_standin.standin_data.amr_wind_direction.to_list()
    assert np.allclose(
        np.array(fs_twd_all)[:, 0], floris_standin.standin_data.amr_wind_direction.values
    )
    assert np.allclose(
        np.array(fs_tws_all)[:, 0], floris_standin.standin_data.amr_wind_speed.values, atol=0.1
    ) # All should be within 1 m/s (shear means lower mean wind speed than free stream)

    # Check power behaves as expected
    # Same condition for each
    fs_tp_all = np.array(fs_tp_all)
    assert np.allclose(fs_tp_all[0, :], fs_tp_all[3, :])
    # Higher power at 10 than 8 m/s
    assert (np.array(fs_tp_all[0, :]) < np.array(fs_tp_all[1, :])).all()
    # Same power at upstream turbine, lower power at downstream turbine when aligned
    assert fs_tp_all[5, 0] == fs_tp_all[0, 0]
    assert fs_tp_all[5, 1] < fs_tp_all[0, 1]
    # Lower power at upstream turbine, higher power at downstream turbine when steering,
    # total power uplift
    assert fs_tp_all[7, 0] < fs_tp_all[6, 0]
    assert fs_tp_all[7, 1] > fs_tp_all[6, 1]
    assert fs_tp_all[7, :].sum() > fs_tp_all[6, :].sum()
    # More power steering at 10m/s than 8m/s
    assert fs_tp_all[9, :].sum() > fs_tp_all[7, :].sum()

def test_FlorisStandin_with_standin_data_power_setpoints():
    floris_standin = FlorisStandin(CONFIG, AMR_INPUT, AMR_EXTERNAL_DATA, smoothing_coefficient=0.0)

    power_setpoints_all = [
        [None, None],
        [None, None],  # Step up from 8 to 10 m/s
        [None, None],
        [None, None],  # Step back down to 8 m/s
        [None, None],  # wd changes to 270.0 here
        [1e3, None],  # Apply a power setpoint at upstream turbine
        [1e3, 1e3], # Apply a power setpoint at both turbines
        [None, 1e3],  # Apply a power setpoint at downstream turbine
        [None, None],
        [None, None],
    ]

    # Initialize storage
    fs_ws_all = []
    fs_wd_all = []
    fs_tp_all = []
    fs_twd_all = []
    fs_tws_all = []
    for i, s in enumerate(np.arange(0, 10.0, 1.0)):
        fs_ws, fs_wd, fs_tp, fs_twd, fs_tws = floris_standin.get_step(
            s,
            power_setpoints=power_setpoints_all[i]
        )
        fs_ws_all.append(fs_ws)
        fs_wd_all.append(fs_wd)
        fs_tp_all.append(fs_tp)
        fs_twd_all.append(fs_twd)
        fs_tws_all.append(fs_tws)

    # Check power behaves as expected
    # Same condition for each
    fs_tp_all = np.array(fs_tp_all)
    assert np.allclose(fs_tp_all[0, :], fs_tp_all[3, :])
    # Higher power at 10 than 8 m/s
    assert (np.array(fs_tp_all[0, :]) < np.array(fs_tp_all[1, :])).all()
    # Same power at upstream turbine, lower power at downstream turbine when aligned
    assert fs_tp_all[4, 0] == fs_tp_all[0, 0]
    assert fs_tp_all[4, 1] < fs_tp_all[0, 1]
    # Turbines match setpoint when set
    assert fs_tp_all[5, 0] == 1e3
    assert fs_tp_all[5, 1] > 1e3
    assert (fs_tp_all[6, :] == 1e3).all()
    assert fs_tp_all[7, 0] > 1e3
    assert fs_tp_all[7, 1] <= 1e3

def test_FlorisStandin_smoothing_coefficient():
    floris_standin_no_smoothing = FlorisStandin(CONFIG, AMR_INPUT, smoothing_coefficient=0.0)
    floris_standin_default_smoothing = FlorisStandin(CONFIG, AMR_INPUT)
    floris_standin_heavy_smoothing = FlorisStandin(CONFIG, AMR_INPUT, smoothing_coefficient=0.9)

    # Start at zero power
    floris_standin_no_smoothing.turbine_powers_prev = np.zeros(2)
    floris_standin_default_smoothing.turbine_powers_prev = np.zeros(2)
    floris_standin_heavy_smoothing.turbine_powers_prev = np.zeros(2)

    # Step forward
    fs_tp_no_smoothing = floris_standin_no_smoothing.get_step(1.0)[2]
    fs_tp_default_smoothing = floris_standin_default_smoothing.get_step(1.0)[2]
    fs_tp_heavy_smoothing = floris_standin_heavy_smoothing.get_step(1.0)[2]

    # Check smoothing ordering correct
    assert (np.array(fs_tp_no_smoothing) > np.array(fs_tp_default_smoothing)).all()
    assert (np.array(fs_tp_default_smoothing) > np.array(fs_tp_heavy_smoothing)).all()

    # Check magnitude is correct
    assert np.allclose(0.1*np.array(fs_tp_no_smoothing), np.array(fs_tp_heavy_smoothing))

def test_FlorisStandin_with_heterogeneous_inflow():
    floris_standin = FlorisStandin(
        CONFIG,
        AMR_INPUT,
        AMR_EXTERNAL_DATA_HET,
        smoothing_coefficient=0.0
    )

    # Set the wind shear to zero to simplify comparisons
    floris_standin.fmodel.set(wind_shear=0.0)

    # Check heterogeneous map interpolation at specified time
    floris_standin.get_step(0)
    turbine_vels_norm_0 = floris_standin.fmodel.turbine_average_velocities / 8.0
    assert np.allclose(turbine_vels_norm_0[0,0], 0.9)
    assert 0.9 < turbine_vels_norm_0[0,1] < 1.0 # Unwaked at 0 degrees
    # Check matches data at time 0

    # Check changed correctly at time 4
    floris_standin.get_step(4)
    turbine_vels_norm_4 = floris_standin.fmodel.turbine_average_velocities / 8.0
    assert np.allclose(turbine_vels_norm_4[0,:], 1.0)

    # Check interpolates correctly for time step 2.
    floris_standin.get_step(2)
    turbine_vels_norm_2 = floris_standin.fmodel.turbine_average_velocities / 8.0
    assert (turbine_vels_norm_0 < turbine_vels_norm_2).all()
    assert (turbine_vels_norm_2 < turbine_vels_norm_4).all()

def test_FlorisStandin_with_bad_heterogeneous_inflow():
    # Read in valid heterogeneous inflow data
    df_het_orig = pd.read_csv(AMR_EXTERNAL_DATA_HET)

    # Add extra key to heterogeneous_inflow_config; reprint
    for i in range(len(df_het_orig)):
        dict_temp = eval(df_het_orig.heterogeneous_inflow_config.iloc[i])
        dict_temp["bad_key"] = 0.0
        df_het_orig.heterogeneous_inflow_config.iloc[i] = str(dict_temp)
    
    # Write to new file
    AMR_EXTERNAL_DATA_HET_BAD = (
        Path(__file__).resolve().parent / "test_inputs" / "amr_standin_data_het_bad.csv"
    )
    df_het_orig.to_csv(AMR_EXTERNAL_DATA_HET_BAD, index=False)

    # Check that the extra key is just ignored
    floris_standin = FlorisStandin(
        CONFIG,
        AMR_INPUT,
        AMR_EXTERNAL_DATA_HET_BAD,
        smoothing_coefficient=0.0
    )
    
    # Set the wind shear to zero to simplify comparisons
    floris_standin.fmodel.set(wind_shear=0.0)
    
    # Step, check ok
    floris_standin.get_step(0)
    turbine_vels_norm_0 = floris_standin.fmodel.turbine_average_velocities / 8.0
    assert np.allclose(turbine_vels_norm_0[0,0], 0.9)

    # Remove needed key for heterogeneous_inflow_config
    df_het_orig = pd.read_csv(AMR_EXTERNAL_DATA_HET)
    for i in range(len(df_het_orig)):
        dict_temp = eval(df_het_orig.heterogeneous_inflow_config.iloc[i])
        del dict_temp["speed_multipliers"]
        df_het_orig.heterogeneous_inflow_config.iloc[i] = str(dict_temp)
    df_het_orig.to_csv(AMR_EXTERNAL_DATA_HET_BAD, index=False)

    # Check proceeds without heterogeneity
    floris_standin = FlorisStandin(
        CONFIG,
        AMR_INPUT,
        AMR_EXTERNAL_DATA_HET_BAD,
        smoothing_coefficient=0.0
    )
    floris_standin.fmodel.set(wind_shear=0.0)
    floris_standin.get_step(0)
    turbine_vels_norm_0 = floris_standin.fmodel.turbine_average_velocities / 8.0
    assert np.allclose(turbine_vels_norm_0, 1.0) # No heterogeneity applied

    # Delete the bad file
    AMR_EXTERNAL_DATA_HET_BAD.unlink()
