# Electrolyzer Plant

The hydrogen electrolyzer modules use the [electrolyzer](https://github.com/NREL/electrolyzer) package developed by the National Laboratory of the Rockies to predict hydrogen output of hydrogen electrolyzer plants. This repo contains models for PEM and Alkaline electrolyzer cell types.

To create a hydrogen electrolyzer plant, set `component_type: ElectrolyzerPlant` in the component's YAML section. The section key is a user-chosen `component_name` (e.g. `electrolyzer`); see [Component Names, Types, and Categories](component_types.md) for details.


## Inputs

#### Required Parameters
The parameters listed below are required unless otherwise specified as *Optional*.

- `general`: General simulation parameters.
- `initial_conditions`: Initial conditions for the simulation including:
  - `power_available_kw`: Initial power available to the electrolyzer [kW]
- `electrolyzer`: Electrolyzer plant specific parameters including:
    - `initialize`: boolean. Whether to initialize the electrolyzer.
    - `initial_power_kW`: Initial power input to the electrolyzer [kW].
    - `supervisor`:
        - `system_rating_MW`: Total system rating in MW.
        - `n_stacks`: Number of electrolyzer stacks in the plant.
    - `stack`: Electrolyzer stack parameters including:
        - `cell_type`: Type of electrolyzer cell (e.g., PEM, Alkaline).
        - `max_current`: Maximum current of the stack [A].
        - `temperature`: Stack operating temperature [degC].
        - `n_cells`: Number of cells per stack.
        - `min_power`: Minimum power for electrolyzer operation [kW].
        - `stack_rating_kW`: Stack rated power [kW].
        - `include_degradation_penalty`: *Optional* Whether to include degradation penalty.
        - `hydrogen_degradation_penalty`: *Optional* boolean, whether degradation is applied to hydrogen (True) or power (False)
    - `cell_params`: Electrolyzer cell parameters including:
        - `cell_area`: Area of individual cells in the stack [cm^2].
        - `turndown_ratio`: Minimum turndown ratio for stack operation [between 0 and 1].
        - `max current_density`: Maximum current density [A/cm^2].
        - `p_anode`: Anode operating pressure [bar].
        - `p_cathode`: Cathode operating pressure [bar].
        - `alpha_a`: anode charge transfer coefficient.
        - `alpha_c`: cathode charge transfer coefficient.
        - `i_0_a`: anode exchange current density [A/cm^2].
        - `i_0_c`: cathode exchange current density [A/cm^2].
        - `e_m`: membrane thickness [cm].
        - `R_ohmic_elec`: electrolyte resistance [A*cm^2].
        - `f_1`: Faradaic coefficient [mA^2/cm^4].
        - `f_2`: Faradaic coefficient [mA^2/cm^4].
    - `degradation`: Electrolyzer degradation parameters including:
        - `eol_eff_percent_loss`: End of life efficiency percent loss [%].
        - `PEM_params` or `ALK_params`: Degradation parameters specific to PEM or Alkaline cells:
            - `rate_steady`: Rate of voltage degradation under steady operation alone
            - `rate_fatigue`: Rate of voltage degradation under variable operation alone 
            - `rate_onoff`: Rate of voltage degradation per on/off cycle
    - `controller`: Electrolyzer control parameters including:
        - `control_type`: Controller type for electrolyzer plant operation.
    - `costs`: *Optional* Cost parameters for the electrolyzer plant including:
        - `plant_params`:
            - `plant_life`: integer, Plant life in years
            - `pem_location`: Location of the PEM electrolyzer. Options are 
                [onshore, offshore, in-turbine]
            - `grid_connected`: boolean, Whether the plant is connected to the grid or not
        - `feedstock`: Parameters related to the feedstock including:
            - `water_feedstock_cost`: Cost of water per kg of water
            - `water_per_kgH2`: Amount of water required per kg of hydrogen produced
        - `opex`: Operational expenditure parameters including:
            - `var_OM`: Variable operation and maintenance cost per kW 
            - `fixed_OM`: Fixed operation and maintenance cost per kW-year
        - `stack_replacement`: Parameters related to stack replacement costs including:
            - `d_eol`: End of life cell voltage value [V]
            - `stack_replacement_percent`: Stack replacement cost as a percentage of CapEx [0,1]
        - `capex`: Capital expenditure parameters including:
            - `capex_learning_rate`: Capital expenditure learning rate.
            - `ref_cost_bop`: Reference cost of balance of plant per kW.
            - `ref_size_bop`: Reference size of balance of plant in kW.
            - `ref_cost_pem`: Reference cost of PEM electrolyzer stack per kW.
            - `ref_size_pem`: Reference size of PEM electrolyzer stack in kW.
        - `finances`: Financial parameters including:
            - `discount_rate`: Discount rate for financial calculations [%].
            - `install_factor`: Installation factor for capital expenditure [0,1].
- `log_channels`: List of output channels to log (see [Logging Configuration](elec-logging-configuration) below)


## Outputs
(elec-logging-configuration)=
**Logging Configuration**

The `log_channels` parameter controls which outputs are written to the HDF5 output file. This is a list of channel names. The `power` channel is always logged, even if not explicitly specified.


### Available Channels

**Scalar Channels:**
- `H2_output`: Total hydrogen produced during the last timestep
- `H2_mfr`: Mass flow rate of the hydrogen production in kg/s
- `power`: Power that the electrolyzer plant used to create hydrogen (kW). This follows the convention that power consumed is negative power.
- `Power_input_kw`: Power allocated to the electrolyzer plant to use (kW)
- `stacks_on`: Total number of stacks producing hydrogen

**Array Channels:**
- `stacks_waiting`: Boolean list of the stacks that are waiting to start producing hydrogen (True for stacks waiting, False for stacks not waiting)


**Example:**
```yaml
ele:
  component_type: ElectrolyzerPlant
  log_channels:
    - power
    - H2_output
    - H2_mfr
  initial_conditions:
    - power_available_kw: 3000
  electrolyzer:
  # ... other parameters
```

If `log_channels` is not specified, only `power` will be logged.

## References
1. Z. Tully, G. Starke, K. Johnson and J. King, "An Investigation of Heuristic Control Strategies for Multi-Electrolyzer Wind-Hydrogen Systems Considering Degradation," 2023 IEEE Conference on Control Technology and Applications (CCTA), Bridgetown, Barbados, 2023, pp. 817-822, doi: 10.1109/CCTA54093.2023.10252187.
