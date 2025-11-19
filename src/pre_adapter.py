from src.rorb_formatter import *
from src.input_compiler import *


def _gateops_filename(config_entry, procedure):
    """
    Determine which template filename to use for a dam based on its procedure.
    Falls back to the open template when an automatic template is unavailable.
    """
    if procedure in (1, 3):
        return config_entry.get("filename_auto") or config_entry["filename_open"]
    if procedure in (2, 4, 5):
        return config_entry["filename_open"]
    raise ValueError(f"Unsupported GateOps procedure '{procedure}'")


def write_gateops_files(template_folder, model_folder, gateops_big_dict, gateops_formatter, param_compiler):
    """
    Generate per-dam GateOps files and return metadata for the multi-gate template.
    """
    gateops_counter = 0
    gateops_storage_and_file_list = []

    for dam_id, config in gateops_big_dict.items():
        procedure = param_compiler.gateops[dam_id].procedure
        filename = _gateops_filename(config, procedure)
        template_path = f"{template_folder}Template_{filename}"
        model_path = f"{model_folder}{filename}"

        writer = TemplateWriter(template_path, model_path)
        writer.fill(
            replacements_dict={
                "gateops_timestep_minute": gateops_formatter.timestep_hour,
                "initial_reservoir_storage": gateops_formatter.initial_storage(dam_id, template_path),
            }
        )

        gateops_storage_and_file_list.append(config["storage"])
        gateops_storage_and_file_list.append(model_path)
        gateops_counter += 1

    return gateops_counter, gateops_storage_and_file_list

# Write RORB model input files
def write_template_files(runinfo_xml):  
    runinfo_compiler = RunInfo(runinfo_xml)
    params_xml = runinfo_compiler.inputParameterFile
    state_xml = runinfo_compiler.inputStateFile
    meteo_netcdf = runinfo_compiler.inputMeteoFile
    rain_netcdf = runinfo_compiler.inputRainFile
    transfer_netcdf = runinfo_compiler.inputTransferFile
    operation_netcdf = runinfo_compiler.inputOperationFile
    model_folder = runinfo_compiler.model_folder
    template_folder = f"{runinfo_compiler.model_folder}templates\\"

    # Logging configuration
    logging.basicConfig(
        level=logging.WARNING, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',  
        handlers=[
            logging.FileHandler(f"{model_folder}Pre_Adapter.log", mode='w'),
            logging.StreamHandler()
        ]
    )

    # Write .par file 
    # Load model parameters and formatted ones
    param_compiler = Params(params_xml)
    par_formatter = PARFormatter(runinfo_xml, params_xml)

    # Fill in the Template_RORB_CMD
    par_writer = TemplateWriter(f"{template_folder}Template_RORB_CMD.par", f"{model_folder}RORB_CMD.par")
    par_writer.fill(replacements_dict={
        "catg_file": f"{model_folder}Talbingo_with_Blowering.catg",
        "stm_file": f"{model_folder}Rainfall.stm",
        "num_burst": param_compiler.num_burst,
        "num_isa": param_compiler.num_isa,
        "loss_params_isa":  par_formatter.loss_params_isa,
        "routing_params_isa":  par_formatter.routing_params_isa,
        "gate_file": f"{model_folder}multiGateOps_UpperTumut_until_Jounama.dat",
        "snow_file": f"Snowmelt :{model_folder}Snowmelt.dat" if param_compiler.snow_setting == "true" else "",
        "matching_file": f"Matching :{model_folder}multiRecorded_hydrographs.dat",
        }
    )

    par_writer.clear_empty_lines()

    # Write .stm file 
    # Load formatted storm data
    storm_formatter = STMFormatter(runinfo_xml, rain_netcdf, params_xml)

    # Fill in the Template_Rainfall
    stm_writer = TemplateWriter(f"{template_folder}Template_Rainfall.stm", f"{model_folder}Rainfall.stm")
    stm_writer.fill(replacements_dict={
        "start_time": runinfo_compiler.startDateTime,
        "end_time": runinfo_compiler.endDateTime,
        "stm_setting": storm_formatter.stm_setting,
        "pluvio_setting": storm_formatter.pluvio_setting,
        "all_subarea_temporal_patterns": storm_formatter.all_subarea_temporal_patterns,
        "subarea_rainfall": storm_formatter.subarea_rainfall,
        "pluvio_choice": storm_formatter.pluvio_choice,
        "baseflow_setting": storm_formatter.baseflow_setting,
        "all_baseflow_hydrographs": storm_formatter.all_baseflow_hydrographs
        }
    )

    # Write .catg file 
    # Keep the original .catg file
    catg_writer = TemplateWriter(f"{template_folder}Template_Talbingo_with_Blowering.catg", f"{model_folder}Talbingo_with_Blowering.catg")
    catg_writer.fill(replacements_dict={})

    # Write .dat file (snowmelt)
    # Load formatted snow data
    snow_formatter = SNOWFormatter(runinfo_xml, meteo_netcdf, state_xml)

    # Fill in the Template_Snowmelt
    snow_writer = TemplateWriter(f"{template_folder}Template_Snowmelt.dat", f"{model_folder}Snowmelt.dat")
    snow_writer.fill(replacements_dict={
        "temp_timeseries": snow_formatter.temp_timeseries,
        "temp_number_increment": snow_formatter.temp_number_increment,
        "wind_timeseries": snow_formatter.wind_timeseries,
        "wind_number_increment": snow_formatter.wind_number_increment,
        'num_elezone': len(snow_formatter.snowmelt_water_content_elezone),
        "snowmelt_water_content_elezone": snow_formatter.snowmelt_water_content_elezone,
        "snowmelt_weighted_snowpack_density": snow_formatter.snowmelt_weighted_snowpack_density,
        }
    )  
    
    # Write .dat file (gateops and transfer)
    # Load file mapping configuration
    file_mappping_config = JsonReader("file_mapping.json")
    gateops_big_dict= file_mappping_config.extract("GateOps_files_dict")
    Qtrans_big_dict = file_mappping_config.extract("Qtrans_files_dict")
    Qgen_big_dict = file_mappping_config.extract("Qgen_files_dict")
    Qoutlet_big_dict = file_mappping_config.extract("Qoutlet_files_dict")

    gateops = GateOpsFormatter(state_xml)
    gateops_counter, gateops_storage_and_file_list = write_gateops_files(
        template_folder=template_folder,
        model_folder=model_folder,
        gateops_big_dict=gateops_big_dict,
        gateops_formatter=gateops,
        param_compiler=param_compiler,
    )

    # Initialize transfer counter and input list
    transfer_counter = 0
    transfer_file_list =[]

    # Write transfer files
    trans_formatter = TRANSFormatter(runinfo_xml, transfer_netcdf)
    for key, value in Qtrans_big_dict.items():
        id = key
        in_node = value["in"]
        out_node = value["out"]
        filename = value["filename"]
        writer = TemplateWriter(f"{template_folder}Template_GateOpsTransfer.dat", f"{model_folder}{filename}")
        writer.fill(replacements_dict={
            "in": in_node,
            "out": out_node,
            "transfer": trans_formatter.transfer_Qtrans(id)
            }
        )
        transfer_file_list.append(f"{model_folder}{filename}")
        transfer_counter +=1

    for key, value in Qgen_big_dict.items():
        id = key
        in_node = value["in"]
        out_node = value["out"]
        filename = value["filename"]
        transfer_file_list.append(f"{model_folder}{filename}")
        writer = TemplateWriter(f"{template_folder}Template_GateOpsTransfer.dat", f"{model_folder}{filename}")
        writer.fill(replacements_dict={
            "in": in_node,
            "out": out_node,
            "transfer": trans_formatter.transfer_Qgen(id)
            }
        )
        transfer_counter +=1

    for key, value in Qoutlet_big_dict.items():
        id = key
        in_node = value["in"]
        out_node = value["out"]
        filename = value["filename"]
        transfer_file_list.append(f"{model_folder}{filename}")
        writer = TemplateWriter(f"{template_folder}Template_GateOpsTransfer.dat", f"{model_folder}{filename}")
        writer.fill(replacements_dict={
            "in": in_node,
            "out": out_node,
            "transfer": trans_formatter.transfer_Qoutlet(id)
            }
        )
        transfer_counter +=1
    
    # Initialize operation counter and input list
    operation_counter = 0
    operation_file_list = []

    # Write gate operation override files
    operation_formatter = OpFormatter(runinfo_xml, operation_netcdf)
    gateoverride_list = operation_formatter.get_dam_ids()
    for key, value in gateops_big_dict.items():
        id = key
        storage = value["storage"]
        filename = value.get("overwrite_filename")   
        if id in gateoverride_list and filename:
            writer = TemplateWriter(f"{template_folder}Template_GateOpsOverride.dat", f"{model_folder}{filename}")
            writer.fill(replacements_dict={
                "gate_override": storage,
                "outflow_opening": operation_formatter.override_outflow_and_opening(id),
                }
            )
            operation_file_list.append(f"{model_folder}{filename}")
            operation_counter +=1


    # Write multiGateOps file
    multigateops_writer = TemplateWriter(f"{template_folder}Template_multiGateOps_UpperTumut_until_Jounama.dat", f"{model_folder}multiGateOps_UpperTumut_until_Jounama.dat")
    multigateops_writer.fill(replacements_dict={
        "gateops_number": gateops_counter,
        "gateops_storages_and_files": FormatUtilities.format_lists(gateops_storage_and_file_list),
        "transfer_number" : transfer_counter,
        "transfer_timestep_hour": trans_formatter.timestep_hour,
        "transfer_number_timestep": trans_formatter.num_data,
        "transfer_files": FormatUtilities.format_lists(transfer_file_list),
        "operation_number": operation_counter,
        "operation_timestep_hour": operation_formatter.timestep_hour,
        "operation_number_timestep": operation_formatter.num_data,
        "operation_files": FormatUtilities.format_lists(operation_file_list),
        }
    )

def write_run_batch(runinfo_xml):
    runinfo_compiler = RunInfo(runinfo_xml)
    model_folder = runinfo_compiler.model_folder
    rorb_exe = runinfo_compiler.rorb_exe
    par_file = f"{model_folder}RORB_CMD.par"

    # Create the run batch file content
    batch_content = f"""@echo off
    set model_folder={model_folder}
    cd /d %model_folder%
    {rorb_exe} {par_file}"""

    # Write the batch file
    batch_file_path = f"{model_folder}RUN_RORB.bat"
    with open(batch_file_path, 'w') as batch_file:
        batch_file.write(batch_content)



if __name__ == "__main__":
    runinfo_xml = r"C:\RORB_FEWS_Adapter\examples\to_rorb\runinfo.xml"
    write_template_files(runinfo_xml)
    write_run_batch(runinfo_xml)
