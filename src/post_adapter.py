import os
import re
import io
import json
import pandas as pd
from lxml import etree
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from src.input_compiler import *
from src.out_processing import *

def read_rorb_outputs(runinfo_xml):
    runinfo_compiler = RunInfo(runinfo_xml)
    startDateTime = runinfo_compiler.startDateTime
    reservoir_operation_xml = runinfo_compiler.outputReservoirOperation
    rainfall_excess_xml = runinfo_compiler.outputRainfallExcess
    gauge_flow_xml = runinfo_compiler.outputGaugeFlow
    fromrorb_folder = runinfo_compiler.fromrorb_folder
    rorb_outfile = f"{runinfo_compiler.model_folder}Talbingo_with_Blowering_Rainfall.out" 
    csv_directory = Path(fromrorb_folder).parent

    # Initialize XMLWriter and rename columns
    xml_writer = XMLWriter()
    rename_columns = {
        'waterLevel': '(H.fcst) (mSMD)',
        'SRes': '(V.fcst) (m3)',
        'qSimIn(iTime)': '(Q-in.fcst) (m3/s)',
        'qSimOut(iTime)': '(Q-out.fcst) (m3/s)',
        'gate_open': '(G.fcst) (m)'
    }

    # Read CSV files into df
    reservoir_operations = []
    file_mappping_config = JsonReader("file_mapping.json")
    GateOps_big_dict= file_mappping_config.extract("GateOps_files_dict")
    for key, value in GateOps_big_dict.items():
            location_id = key
            csv_filename = value['csv_filename']
            csv_filepath = os.path.join(runinfo_compiler.model_folder, csv_filename)
            csv = OutputCSVReader(location_id=key, level_csv=csv_filepath, event_start_str=startDateTime)
            temp_xml = f"{fromrorb_folder}{csv_filename}.xml"
            xml_writer.write_df_to_xml(csv.read_and_process_level_csv(rename_columns), temp_xml)
            reservoir_operations.append(temp_xml)
    
    # Combine to Reservoir Operation XML and remove individual files
    combine_xml_files(reservoir_operations, reservoir_operation_xml, xml_writer.template)
    for file in reservoir_operations:
        os.remove(file)
    
    # Read .out file
    outfile = OutputOUTReader(rorb_outfile)
    
    # Read and process rainfall excess section
    pluvio_section = outfile.extract_section("Input of parameters:", "Routing results:")
    rorb_config = JsonReader("rorb_config.json")
    calc_order_list = rorb_config.extract("rorb_subarea_calc_order_list")
    calc_order = outfile.map_calc_order(pluvio_section, "Pluvi. ref. no.", calc_order_list) #### This is somehow missing one of the calc_order_list
    while any("Rainfall, mm, in time inc. following time shown" in line for line in pluvio_section):
        outfile.del_section(pluvio_section)

    rainfall_excess_dfs = []
    start_datetime, end_datetime, time_increment_hours = outfile.extract_datetime_index(pluvio_section)
    start_datetime = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
    while any("Incs" in line for line in pluvio_section):
        df = outfile.process_rainfall_excess(pluvio_section)
        nrows = len(df)
        time_incs = timedelta(hours=time_increment_hours)
        datetime_index = [start_datetime + time_incs * i for i in range(nrows)]
        df.index = pd.to_datetime(datetime_index)
        rainfall_excess_dfs.append(df)
    del rainfall_excess_dfs[9] ### Figure out how to remove this df!!!!

    # Write to Rainfall Excess XML
    columns_to_remove = ["Incs", "ment", "area"]
    rainfall_excess = []
    for i, df in enumerate(rainfall_excess_dfs, start=0):
        df = df.drop(columns=columns_to_remove)
        df.columns = calc_order[i]
        csv_filename = f"Rainfall_Excess_Interstation_{i}"
        output_xml = f"{fromrorb_folder}{csv_filename}.xml"
        xml_writer.write_df_to_xml(df, output_xml)
        rainfall_excess.append(output_xml)

    combine_xml_files(rainfall_excess, rainfall_excess_xml, xml_writer.template)
    for file in rainfall_excess:
        os.remove(file)

    # Process gauge flow
    hydrograph_section = outfile.extract_section("Hyd001")
    df = outfile.section_to_df(hydrograph_section)
    split_point = df[df.isnull().all(axis=1)].index[0]
    first_table = df.iloc[:split_point].reset_index(drop=True)
    second_table = df.iloc[split_point + 2:].reset_index(drop=True)
    second_table.columns = df.iloc[split_point + 1]
    second_table = second_table.loc[:, ~second_table.columns.isna()]
    hydrogrpah_summary = pd.concat([first_table, second_table], axis=1)
    hydrogrpah_summary = hydrogrpah_summary.loc[:, ~hydrogrpah_summary.columns.duplicated()]
    selected_columns = ['Hyd001', 'Hyd002','Hyd018', 'Hyd019', 'Hyd026', 'Hyd029']
    rename_columns = ["410574 (Q.fcst) (m3/s)", "410575 (Q.fcst) (m3/s)", "410094 (Q.fcst) (m3/s)", "410534 (Q.fcst) (m3/s)", "410533 (Q.fcst) (m3/s)", "410542 (Q.fcst) (m3/s)"]
    selected_hydrographs = hydrogrpah_summary[selected_columns]
    selected_hydrographs.columns = rename_columns
    nrows = len(selected_hydrographs)
    datetime_index = [start_datetime + time_incs * i for i in range(nrows)]
    selected_hydrographs.index = pd.to_datetime(datetime_index)

    # Write to Gauge Flow XML
    csv_filename = f"Gauge_Flow"
    output_xml = f"{fromrorb_folder}{csv_filename}.xml"
    xml_writer.write_df_to_xml(selected_hydrographs, output_xml)

if __name__ == "__main__":
    runinfo_xml = r"C:\RORB_FEWS_Adapter\examples\FromFews\RunInfo.xml"
    read_rorb_outputs(runinfo_xml)