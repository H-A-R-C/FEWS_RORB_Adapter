import pytest
import os
import subprocess
import shutil
import netCDF4 as nc
import datetime
from src.utils import *
from src.input_compiler import *
from src.pre_adapter import *
import xml.etree.ElementTree as ET
import logging

# Common root directory
root_directory = r"C:\Users\christian.urich\codes\FEWS_RORB_Adapter"

example_directory = os.path.join(root_directory, "examples")
pre_adapter = os.path.join(root_directory, "dist")


test_temp_timeseries = [1, 2, 3, 4, 5]
test_wind_timeseries = [1, 2, 3, 4, 5]
test_snowmelt_water_content_elezone = [1, 2, 3, 4, 5]
test_snowmelt_weighted_snowpack_density = [1, 2, 3, 4, 5]

runinfo_template = os.path.join(root_directory, "tests", "template_runinfo.xml")
rorb_exe = os.path.join(root_directory, "bin_rorb", "RORB_CMD", "rorb_cmd.exe")

model_config = {
    "Snowmelt_Off": {
        "directory_path":rf"{example_directory}\talbingo_rog_local-rog",
        "rorbSnow": "false",
        "rorbTransfer": "true",
        },
    "Snowmelt_On": {
        "directory_path":rf"{example_directory}\talbingo_rog_local-rog",
        "rorbSnow": "true",
        "rorbTransfer": "true",
        },
    "Snowmelt_Custom_Timeseries": {
        "directory_path":rf"{example_directory}\talbingo_rog_local-rog",
        "rorbSnow": "true",
        "rorbTransfer": "true",
        "temp_timeseries": test_temp_timeseries,
        "temp_number_increment": len(test_temp_timeseries)+1,
        "wind_timeseries": test_wind_timeseries,
        "wind_number_increment": len(test_wind_timeseries)+1,
        "num_elezone": len(test_snowmelt_water_content_elezone),
        "snowmelt_water_content_elezone": test_snowmelt_water_content_elezone,
        "snowmelt_weighted_snowpack_density": test_snowmelt_weighted_snowpack_density,
        },
    }

@pytest.fixture
def initialize_test_directory(id):
    folders = {
        "to_rorb": os.path.join(example_directory, f"{id}\\to_rorb"),
        "model": os.path.join(example_directory, f"{id}\\model"),
        "from_rorb": os.path.join(example_directory, f"{id}\\from_rorb"),
        "logs": os.path.join(example_directory, f"{id}\\Logs")
    }
    for folder in folders.values():
        os.makedirs(folder, exist_ok=True)
        clean_folder(folder)
    return folders

def copy_files(source_folder, destination_folder):
    # Ensure the destination folder exists
    os.makedirs(destination_folder, exist_ok=True)

    # Iterate through all items in the source folder
    for item in os.listdir(source_folder):
        source_path = os.path.join(source_folder, item)
        destination_path = os.path.join(destination_folder, item)
        
        # Check if it's a file or a directory
        if os.path.isfile(source_path):
            # Copy the file to the destination folder
            shutil.copy(source_path, destination_path)
        elif os.path.isdir(source_path):
            # Copy the directory to the destination folder recursively
            shutil.copytree(source_path, destination_path, dirs_exist_ok=True)

def clean_folder(folder_path):
    # Check if the folder exists
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        # Remove all contents of the folder
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove the file or link
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove the directory and its contents
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    else:
        print(f"Folder does not exist: {folder_path}")



@pytest.mark.parametrize("id, setting", model_config.items())
def test_01_prepare_template_file(id, setting, initialize_test_directory):
    test_folders = initialize_test_directory
    rorb_model = setting.get("directory_path")
    
    
    copy_files(rorb_model, os.path.join(example_directory, f"{id}"))
    

    runinfo_output_path = os.path.join(test_folders["to_rorb"], "RunInfo.xml")
    try:
        template_runinfo = TemplateWriter(runinfo_template, runinfo_output_path)
        template_runinfo.fill(replacements_dict={
            'example_directory': example_directory,
            'id': id,
            'rorb_folder': os.path.dirname(rorb_exe),
            'exe': os.path.basename(rorb_exe)
        })
    except Exception as e:
        pytest.fail(f"Failed to generate RunInfo.xml for {id}: {e}")

@pytest.mark.parametrize("id, setting", model_config.items())
def test_02_compile_input_files(id, setting, initialize_test_directory):
    test_folders = initialize_test_directory
    rorb_model = setting.get("directory_path")
    copy_files(rorb_model, os.path.join(example_directory, f"{id}"))
    #copy_files(r"C:\Users\christian.urich\codes\FEWS_RORB_Adapter\examples\to_rorb", os.path.join(example_directory, f"{id}", "to_rorb"))
    #copy_files(r"C:\Users\christian.urich\codes\FEWS_RORB_Adapter\examples\model\templates", os.path.join(example_directory, f"{id}", "model","templates"))
    
    runinfo_xml = os.path.join(test_folders["to_rorb"], "RunInfo.xml")
    template_runinfo = TemplateWriter(runinfo_template, runinfo_xml)
    template_runinfo.fill(replacements_dict={
        'example_directory': example_directory,
        'id': id,
        'rorb_folder': os.path.dirname(rorb_exe),
        'exe': os.path.basename(rorb_exe)
    })


    runinfo_compiler = RunInfo(runinfo_xml)
    params_xml = runinfo_compiler.inputParameterFile
    state_xml = runinfo_compiler.inputStateFile
    meteo_netcdf = runinfo_compiler.inputMeteoFile
    rain_netcdf = runinfo_compiler.inputRainFile
    transfer_xml = runinfo_compiler.inputTransferFile
    model_folder = runinfo_compiler.model_folder
    template_folder = runinfo_compiler.model_folder + "templates\\"

    # Write .par file 
    # Load model parameters and formatted ones
    param_compiler = Params(params_xml)
    par_formatter = PARFormatter(runinfo_xml, params_xml)

    # Turn Snowmelt module ON/OFF
    param_compiler.snow_setting = setting.get("rorbSnow")

    # Write snowmelt.dat file if snowmelt module is ON (NEED TO CHNAGE PRE-ADAPTER TO INCLUDE THIS!!!!)
    if param_compiler.snow_setting == "true":
        # Load formatted snow data
        snow_formatter = SNOWFormatter(runinfo_xml, meteo_netcdf, state_xml)

        # Fill in the Template_Snowmelt
        snow_writer = TemplateWriter(f"{template_folder}Template_Snowmelt.dat", f"{model_folder}Snowmelt.dat")
        snow_writer.fill(replacements_dict={
            "temp_timeseries": setting.get("temp_timeseries") if setting.get("temp_timeseries") is not None else snow_formatter.temp_timeseries,
            "temp_number_increment": setting.get("temp_number_increment") if setting.get("temp_number_increment") is not None else snow_formatter.temp_number_increment,
            "wind_timeseries": setting.get("wind_timeseries") if setting.get("wind_timeseries") is not None else snow_formatter.wind_timeseries,
            "wind_number_increment": setting.get("wind_number_increment") if setting.get("wind_number_increment") is not None else snow_formatter.wind_number_increment,
            # (!!!!   THIS DOESNT MATCH WITH THE NUMBER OF INITAL WATER CONTENTS - NEED TO CHANGE   !!!!)
            'num_elezone': setting.get("num_elezone") if setting.get("num_elezone") is not None else len(snow_formatter.snowmelt_water_content_elezone),
            "snowmelt_water_content_elezone": setting.get("snowmelt_water_content_elezone") if setting.get("snowmelt_water_content_elezone") is not None else snow_formatter.snowmelt_water_content_elezone,
            "snowmelt_weighted_snowpack_density": setting.get("snowmelt_weighted_snowpack_density") if setting.get("snowmelt_weighted_snowpack_density") is not None else snow_formatter.snowmelt_weighted_snowpack_density
            }
        )

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
        "snow_file": f"Snowmelt :{model_folder}Snowmelt.dat" if param_compiler.snow_setting == "true" else "# END"
        }
    )

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

    # Write .dat file (gateops and transfer)
    # Load file mapping configuration
    file_mappping_config = JsonReader("file_mapping.json")
    gateops_big_dict = file_mappping_config.extract("GateOps_files_dict")
    Qtrans_big_dict = file_mappping_config.extract("Qtrans_files_dict")
    Qgen_big_dict = file_mappping_config.extract("Qgen_files_dict")

    gateops_formatter = GateOpsFormatter(state_xml)
    gateops_counter, gateops_storage_and_file_list = write_gateops_files(
        template_folder=template_folder,
        model_folder=model_folder,
        gateops_big_dict=gateops_big_dict,
        gateops_formatter=gateops_formatter,
        param_compiler=param_compiler,
    )

    # Initialize transfer counter and input list
    transfer_counter = 0
    transfer_file_list =[]

    # Write transfer files
    trans_formatter = TRANSFormatter(runinfo_xml, transfer_xml)
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

    # Write multiGateOps file
    multigateops_writer = TemplateWriter(f"{template_folder}Template_multiGateOps_UpperTumut_until_Jounama.dat", f"{model_folder}multiGateOps_UpperTumut_until_Jounama.dat")
    if setting.get("rorbTransfer") == "true":
        multigateops_writer.fill(replacements_dict={
            "gateops_number": gateops_counter,
            "gateops_storages_and_files": FormatUtilities.format_lists(gateops_storage_and_file_list),
            "transfer_number" : transfer_counter,
            "transfer_timestep_hour": trans_formatter.timestep_hour,
            "transfer_number_timestep": trans_formatter.num_data,
            "transfer_files": FormatUtilities.format_lists(transfer_file_list)
            })
    else:
        multigateops_writer.fill(replacements_dict={
            "gateops_number": gateops_counter,
            "gateops_storages_and_files": FormatUtilities.format_lists(gateops_storage_and_file_list),
            "transfer_number" : 0,
            "transfer_timestep_hour": 0,
            "transfer_number_timestep": 0,
            "transfer_files": ""
            })
    
    # except Exception as e:
    #     pytest.fail(f"Failed write RORB model input files for {id}: {e}")


@pytest.mark.parametrize("id, setting", model_config.items())
def test_03_run_rorb(id, setting):
    try:
        PARfile = os.path.join(example_directory, f"{id}\\model\\RORB_CMD.par")
        result = subprocess.run([rorb_exe, PARfile], check=True, capture_output=True, text=True)

        # Debug output
        print(f"Output for {id}: {result.stdout}")
        print(f"Error for {id}: {result.stderr}")

    except subprocess.CalledProcessError as e:
        print(f"Subprocess failed for {id}: {e}")
        print(f"Subprocess output: {e.output}")
        raise

    except Exception as e:
        print(f"Error in {id}: {e}")
        raise
