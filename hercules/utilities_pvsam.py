import math
from typing import List, Optional

import numpy as np
import pandas as pd

from hercules.utilities import hercules_float_type

"""

This file contains all the utilities required to make intermediate 
calculations of the PV design and layout.

Functions that can be kept separate and self-contained should be here 
to enable re-use by other scripts and tests. Making these functions 
standalone helps clarify the required inputs and function scope. It 
also reduces the bulk of the PVPlant classes, making it easier to 
understand what aggregate logic it performs.

These may include any helper functions for calculating any system 
variable such as number of inverters, combiner boxes, etc or for 
estimating some value given a PV layout.

"""


def find_modules_per_string(
    model,
    v_mppt_min: float,
    v_mppt_max: float,
    v_mp_module: float,
    v_oc_module: float,
    inv_vdcmax: float,
    target_relative_string_voltage: float = None,
) -> float:
    """Calculate the number of modules per string to best match target string voltage.

    Helper function for size_electrical_parameters that calculates the
    number of modules per string to best match target string voltage.

    Args:
        model: PySAM.PVsamv1 model.
        v_mppt_min (float): Lower boundary of inverter maximum-power-point operating window, V.
        v_mppt_max (float): Upper boundary of inverter maximum-power-point operating window, V.
        v_mp_module (float): Voltage of module at maximum point point at reference conditions, V.
        v_oc_module (float): Open circuit voltage of module at reference conditions, V.
        inv_vdcmax (float): Maximum inverter input DC voltage, V.
        target_relative_string_voltage (float, optional): Relative string voltage within MPPT
            voltage window, [0, 1]. Defaults to None.

    Returns:
        float: Number of modules per string.
    """
    if v_mp_module <= 0:
        raise Exception("Module maximum power point voltage must be greater than 0.")
    if target_relative_string_voltage is None:
        target_relative_string_voltage = 0.5

    target_string_voltage = v_mppt_min + target_relative_string_voltage * (v_mppt_max - v_mppt_min)
    modules_per_string = max(1, round(target_string_voltage / v_mp_module))
    if inv_vdcmax > 0:
        while modules_per_string > 0 and modules_per_string * v_oc_module > inv_vdcmax:
            modules_per_string -= 1
    model.value("subarray1_modules_per_string", modules_per_string)
    return modules_per_string


def find_inverter_count(
    model,
    dc_ac_ratio: float,
    modules_per_string: float,
    n_strings: float,
    module_power: float,
    inverter_power: float,
):
    """Calculate the number of inverters needed for the system.

    Helper function for size_electrical_parameters that sizes the number of inverters.

    Args:
        model: PySAM.Pvsamv1 model.
        dc_ac_ratio (float): DC-to-AC ratio.
        modules_per_string (float): Modules per string.
        n_strings (float): Number of strings in array.
        module_power (float): Module power at maximum point point at reference conditions, kW.
        inverter_power (float): Inverter maximum AC power, kW.

    Returns:
        float: Number of inverters in array.
    """
    n_inverters_frac = (
        modules_per_string * n_strings * module_power / (dc_ac_ratio * inverter_power)
    )
    n_inverters = max(1, round(n_inverters_frac))
    model.value("inverter_count", n_inverters)
    return n_inverters


def size_electrical_parameters(
    model,
    target_system_capacity: float,
    vdcmax_inverter: Optional[float] = None,
    n_inputs_inverter: Optional[float] = None,
    n_inputs_combiner: Optional[float] = None,
):
    """Calculate electrical parameters to match target capacity and DC/AC ratio.

    Calculates the number of strings, combiner boxes and inverters to best match target
    capacity and DC/AC ratio.

    Args:
        model: PySAM.Pvsamv1 model.
        target_system_capacity (float): Target system capacity, kW.
        vdcmax_inverter (float, optional): Inverter maximum DC voltage, V. Defaults to None.
        n_inputs_inverter (float, optional): Number of DC inputs per inverter. Defaults to None.
        n_inputs_combiner (float, optional): Number of DC inputs per combiner box. Defaults to None.

    Returns:
        tuple: Number of strings, number of combiner boxes, number of inverters, calculated
            system capacity, kW.
    """

    # Force target DC/AC ratio to 1.0
    target_dc_ac_ratio = 1.0

    module_model = model.value("module_model")
    module_power = 0
    module_vmp = 0
    module_voc = 0

    if module_model == 0:
        ref = int(model.SimpleEfficiencyModuleModel.spe_reference)
        eff_list = [
            model.SimpleEfficiencyModuleModel.spe_eff0,
            model.SimpleEfficiencyModuleModel.spe_eff1,
            model.SimpleEfficiencyModuleModel.spe_eff2,
            model.SimpleEfficiencyModuleModel.spe_eff3,
            model.SimpleEfficiencyModuleModel.spe_eff4,
        ]
        rad_list = [
            model.SimpleEfficiencyModuleModel.spe_rad0,
            model.SimpleEfficiencyModuleModel.spe_rad1,
            model.SimpleEfficiencyModuleModel.spe_rad2,
            model.SimpleEfficiencyModuleModel.spe_rad3,
            model.SimpleEfficiencyModuleModel.spe_rad4,
        ]
        eff = eff_list[ref]
        rad = rad_list[ref]
        area = model.SimpleEfficiencyModuleModel.spe_area
        module_power = eff / 100.0 * rad * area  # Wdc
        module_vmp = model.SimpleEfficiencyModuleModel.spe_vmp
        module_voc = model.SimpleEfficiencyModuleModel.spe_voc
    elif module_model == 1:
        module_power = (
            model.CECPerformanceModelWithModuleDatabase.cec_v_mp_ref
            * model.CECPerformanceModelWithModuleDatabase.cec_i_mp_ref
        )
        module_vmp = model.CECPerformanceModelWithModuleDatabase.cec_v_mp_ref
        module_voc = model.CECPerformanceModelWithModuleDatabase.cec_v_oc_ref
    elif module_model == 2:
        module_vmp = model.CECPerformanceModelWithUserEnteredSpecifications.sixpar_vmp
        module_voc = model.CECPerformanceModelWithUserEnteredSpecifications.sixpar_voc
        module_power = (
            module_vmp * model.CECPerformanceModelWithUserEnteredSpecifications.sixpar_imp
        )
    elif module_model == 3:
        print("This function does not currently work for the Sandia Array Performance Model")
        """
        module_power = model.SandiaPVArrayPerformanceModelWithModuleDatabase.snl_ref_pmp
        module_vmp = model.SandiaPVArrayPerformanceModelWithModuleDatabase.snl_ref_vmp
        module_voc = model.SandiaPVArrayPerformanceModelWithModuleDatabase.snl_ref_voc
        """
        return
    elif module_model == 4:
        module_vmp = model.IEC61853SingleDiodeModel.sd11par_Vmp0
        module_voc = model.IEC61853SingleDiodeModel.sd11par_Voc0
        module_power = module_vmp * model.IEC61853SingleDiodeModel.sd11par_Imp0
    elif module_model == 5:
        module_vmp = model.MermoudLejeuneSingleDiodeModel.mlm_V_mp_ref
        module_voc = model.MermoudLejeuneSingleDiodeModel.mlm_V_oc_ref
        module_power = module_vmp * model.MermoudLejeuneSingleDiodeModel.mlm_I_mp_ref
    else:
        print("The module model is not recognized. Please use a valid module model.")
        return

    inverter_model = model.value("inverter_model")
    inv_power = 0
    vdcmax_inv = 0
    v_mppt_max = 0
    v_mppt_min = 0

    if inverter_model == 0:
        inv_power = model.InverterCECDatabase.inv_snl_paco
        vdcmax_inv = model.InverterCECDatabase.inv_snl_vdcmax
    elif inverter_model == 1:
        inv_power = model.InverterDatasheet.inv_ds_paco
        vdcmax_inv = model.InverterDatasheet.inv_ds_vdcmax
    elif inverter_model == 1:
        inv_power = model.InverterPartLoadCurve.inv_pd_paco
        vdcmax_inv = model.InverterPartLoadCurve.inv_pd_vdcmax
    elif inverter_model == 1:
        inv_power = model.InverterCECCoefficientGenerator.inv_cec_cg_paco
        vdcmax_inv = model.InverterCECCoefficientGenerator.inv_cec_cg_vdcmax
    elif inverter_model == 1:
        inv_power = model.InverterMermoudLejeuneModel.ond_PMaxOUT
        vdcmax_inv = model.InverterMermoudLejeuneModel.ond_VAbsMax
    else:
        print("The inverter model is not recognized. Please use a valid inverter model.")
        return

    if vdcmax_inverter is not None:
        vdcmax_inv = vdcmax_inverter
    v_mppt_min = model.value("mppt_low_inverter")
    v_mppt_max = model.value("mppt_hi_inverter")
    modules_per_string = find_modules_per_string(
        model, v_mppt_min, v_mppt_max, module_vmp, module_voc, vdcmax_inv
    )

    n_strings_frac = (
        target_system_capacity * 1000.0 / (modules_per_string * module_power)
    )  # Wac/Wdc
    n_strings = max(1, round(n_strings_frac))

    if target_dc_ac_ratio < 0:
        target_dc_ac_ratio = 1
    n_inverters = find_inverter_count(
        model,
        dc_ac_ratio=target_dc_ac_ratio,
        modules_per_string=modules_per_string,
        n_strings=n_strings,
        module_power=module_power / 1000.0,  # kWdc
        inverter_power=inv_power / 1000.0,  # kWac
    )

    if n_inputs_combiner is not None and n_inputs_inverter is not None:
        n_combiners = math.ceil(n_strings / n_inputs_combiner)
        # Ensure there are enough inverters for the number of combiner boxes
        n_inverters = max(n_inverters, math.ceil(n_combiners / n_inputs_inverter))
    else:
        n_combiners = None

    # Verify sizing was close to the target size, otherwise error out
    calculated_system_capacity = verify_capacity_from_electrical_parameters(
        system_capacity_target=target_system_capacity,
        n_strings=[n_strings],
        modules_per_string=[modules_per_string],
        module_power=module_power / 1000.0,  # kWac
    )
    model.value("subarray1_modules_per_string", modules_per_string)
    model.value("subarray1_nstrings", n_strings)
    model.value("system_capacity", calculated_system_capacity)
    return n_strings, n_combiners, n_inverters, calculated_system_capacity


def verify_capacity_from_electrical_parameters(
    system_capacity_target: float,
    n_strings: List[int],
    modules_per_string: List[int],
    module_power: float,
    percent_max_deviation: float = 5,
) -> float:
    """Compute system capacity from electrical parameters and verify against target.

    Computes system capacity from specified number of strings, modules per
    string and module power. If computed capacity is significantly different than
    the specified capacity an exception will be thrown.

    Args:
        system_capacity_target (float): Target system capacity, kW.
        n_strings (List[int]): Number of strings in each subarray, -.
        modules_per_string (List[int]): Modules per string in each subarray, -.
        module_power (float): Module power at maximum point point at reference conditions, kW.
        percent_max_deviation (float, optional): If calculated system capacity differs from target
            by this percent or more, raise an exception; if None, do not check. Defaults to 5.

    Returns:
        float: Calculated system capacity, kW.
    """
    # PERCENT_MAX_DEVIATION = 5       # [%]
    assert len(n_strings) == len(modules_per_string)
    calc_sys_capacity = (
        sum(
            np.array(n_strings, dtype=hercules_float_type)
            * np.array(modules_per_string, dtype=hercules_float_type)
        )
        * module_power
    )
    if (
        percent_max_deviation is not None
        and abs((calc_sys_capacity / system_capacity_target - 1)) * 100 > percent_max_deviation
    ):
        raise Exception(
            f"The specified system capacity of {system_capacity_target} kW "
            f"is more than "
            f"{percent_max_deviation}% from the value calculated from the "
            f"specified number "
            f"of strings, modules per string and module power "
            f"({int(calc_sys_capacity)} kW)."
        )

    return calc_sys_capacity


def align_from_capacity(
    system_capacity_target: float,
    dc_ac_ratio: float,
    modules_per_string: float,
    module_power: float,
    inverter_power: float,
) -> list:
    """Ensure coherence between parameters for detailed PV model.

    Ensure coherence between parameters for detailed PV model (pvsamv1),
    keeping the DC-to-AC ratio approximately the same.

    Args:
        system_capacity_target (float): Target system capacity, kW.
        dc_ac_ratio (float): DC-to-AC ratio.
        modules_per_string (float): Modules per string, -.
        module_power (float): Module power at maximum point point at reference conditions, kW.
        inverter_power (float): Inverter maximum AC power, kW.

    Returns:
        list: Number strings, calculated system capacity [kW], number of inverters.
    """
    n_strings_frac = system_capacity_target / (modules_per_string * module_power)
    n_strings = max(1, round(n_strings_frac))
    system_capacity = module_power * n_strings * modules_per_string

    if dc_ac_ratio > 0:
        n_inverters_frac = (
            modules_per_string * n_strings * module_power / (dc_ac_ratio * inverter_power)
        )
    else:
        n_inverters_frac = modules_per_string * n_strings * module_power / inverter_power
    n_inverters = max(1, round(n_inverters_frac))

    return n_strings, system_capacity, n_inverters


def get_num_modules(pvsam_model) -> float:
    """Return the number of modules in all subarrays.

    Args:
        pvsam_model: PySAM PV model.

    Returns:
        float: Number of modules in all subarrays.
    """
    n_modules = 0
    for i in range(1, 4 + 1):
        if i == 1 or pvsam_model.value(f"subarray{i}_enable") == 1:
            n_modules += pvsam_model.value(f"subarray{i}_nstrings") * pvsam_model.value(
                f"subarray{i}_modules_per_string"
            )
    return n_modules


def set_cec_module_library_selection(model, module_name: str) -> dict:
    """Set module values from the CEC Module Database library.

    Return the module values from the CEC Module Database library as a dictionary.

    Args:
        model: Pvsamv1 model to write the module values to.
        module_name (str): Name of module for indexing library.

    Returns:
        dict: Dictionary with variable values for selected module.
    """
    module_model = model.value("module_model")
    if module_model != 1:
        print(
            "This function only works if module_model == 1 "
            "(CEC Performance Model with Module Database)"
        )
        return

    file = "https://raw.githubusercontent.com/NREL/SAM/patch/deploy/libraries/CEC%20Modules.csv"
    db = pd.read_csv(file, index_col=0, header=2)  # Reading this might take 1 min or so,
    # the database is big.

    modfilter = db.index.str.startswith(module_name)
    CECMod = db[modfilter]
    # CECParamList = CECMod.values.tolist()
    print(len(CECMod), " modules selected. Name of 1st entry: ", CECMod.index[0])
    # column_names = list(CECMod.columns)
    for columnName, columnData in CECMod.items():
        if (
            columnName.startswith("cec_")
            and columnName != "cec_material"
            and columnName != "cec_gamma_pmp"
        ):
            print(columnName)
            model.value(columnName, columnData)
        else:
            continue

    mod_dict = CECMod.to_dict()
    return mod_dict


def set_cec_inverter_library_selection(model, inverter_name: str) -> dict:
    """Set inverter values from the CEC Inverter Database library.

    Return the inverter values from the CEC Inverter Database library as a dictionary.

    Args:
        model: Pvsamv1 model to write the module values to.
        inverter_name (str): Name of inverter for indexing library.

    Returns:
        dict: Dictionary with variable values for selected inverter.
    """
    inv_model = model.value("inverter_model")
    if inv_model != 0:
        print("This function only works if inverter_model == 1 (Inverter CEC Database)")
        return

    file = "https://raw.githubusercontent.com/NREL/SAM/patch/deploy/libraries/CEC%20Inverters.csv"
    db = pd.read_csv(file, index_col=0, header=2)  # Reading this might take 1 min or so,
    # the database is big.

    invfilter = db.index.str.startswith(inverter_name)
    CECInv = db[invfilter]
    # CECParamList = CECInv.values.tolist()
    print(len(CECInv), " inverters selected. Name of 1st entry: ", CECInv.index[0])
    # column_names = list(CECInv.columns)
    unused_cols = ["inv_snl_ac_voltage", "inv_snl_idcmax"]
    for columnName, columnData in CECInv.items():
        print(columnName)
        if columnName.startswith("inv_snl") and columnName not in unused_cols:
            if columnName.startswith("inv_snl_mppt_low"):
                model.value("mppt_low_inverter", columnData)
            elif columnName.startswith("inv_snl_mppt_hi"):
                model.value("mppt_hi_inverter", columnData)
            else:
                model.value(columnName, columnData)
        else:
            continue

    inv_dict = CECInv.to_dict()
    return inv_dict
