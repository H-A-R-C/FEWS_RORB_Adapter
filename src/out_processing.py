import re
import pandas as pd
from lxml import etree
from datetime import datetime, timedelta
from src.input_compiler import *

def combine_xml_files(input_files, output_file, template):
    combined_root = etree.fromstring(template)
    namespaces = {'ns': 'http://www.wldelft.nl/fews/PI'}

    # Parse and combine all XML files
    for file in input_files:
        try:
            print(f"Processing file: {file}")
            tree = etree.parse(file)  # Parse the current XML file
            root = tree.getroot()

            # Append all <series> elements to the combined root
            for child in root.findall('ns:series', namespaces):
                combined_root.append(child)
        except Exception as e:
            print(f"Error processing file '{file}': {e}")
    
    # Write the combined XML to the output file
    combined_tree = etree.ElementTree(combined_root)
    combined_tree.write(output_file, pretty_print=True, xml_declaration=True, encoding="UTF-8")


class OutputCSVReader:
    def __init__(self, location_id:str, level_csv: str, event_start_str: str):
        """
        Initializes the OutputReader instance.

        :param level_csv: The file path to the CSV file containing level data.
        :param event_start_str: The start time of the event in ISO format string.
        :param timestep_minutes: The number of minutes each timestep in the CSV represents.
        """
        self.event_start_str = event_start_str
        self.level_csv = level_csv
        self.location_id = location_id
        # self.df = self.read_and_process_level_csv(rename_columns)

    def read_and_process_level_csv(self, rename_columns):
        """
        Reads and processes the CSV file specified in 'self.level_csv'.
        The method calculates time-related information based on the event start time
        and adds new columns to the DataFrame for date, time, and value.

        :return: Processed Pandas DataFrame
        """
        try:
            Output_df = pd.read_csv(self.level_csv)
            Output_df.columns = Output_df.columns.str.strip()
            filtered_df = Output_df[list(rename_columns.keys())].rename(columns=rename_columns)
            filtered_df['location_id'] = self.location_id
            grouped_df = filtered_df.groupby('location_id')
            processed_columns = []
            for loc_id, group in grouped_df:
                group = group.drop(columns=['location_id'])
                group.columns = [f"{loc_id} {col}" for col in group.columns]
                processed_columns.append(group)
            processed_df = pd.concat(processed_columns, axis=1)
            timedelta = Output_df['iTime'].astype(int) - 1
            base_time = pd.to_datetime(self.event_start_str)
            processed_df['datetime'] = base_time + pd.to_timedelta(timedelta, unit="m")
            processed_df = processed_df.set_index('datetime')

            return processed_df
    
        except Exception as e:
            # Log the error and re-raise it if any exception occurs during the CSV reading and processing.
            logging.error("Error processing CSV file:", e)
            raise
        
class OutputOUTReader:
    def __init__(self, out_file: str):
        """
        Initializes the OutputOUTReader instance.

        :param out_file: The file path to the output file.
        """
        self.out_file = out_file

    def extract_section(self, start_marker, end_marker=None):
        """
        Extracts a section of data from the output file between the specified markers.

        :param start_marker: The start marker to search for.
        :param end_marker: The end marker to search for.

        :return: List of lines extracted from the output file.
        """
        extracted_lines = []
        within_section = False

        with open(self.out_file, 'r') as file:
            for line in file:
                if start_marker in line:
                    within_section = True
                    extracted_lines.append(line.strip())
                    continue
                if end_marker and end_marker in line and within_section:
                    within_section = False
                    break
                if within_section:
                    extracted_lines.append(line.strip())

        if not extracted_lines:
            raise ValueError("No data found between the specified markers.")

        return extracted_lines

    def section_to_df(self, lines):
        """
        Converts the extracted section of lines from the output file to a DataFrame.

        :param lines: List of lines extracted from the output file.

        :return: Pandas DataFrame containing the data from the section.
        """
        
        # Split lines into data rows
        data = [line.split() for line in lines]

        # Extract the header
        header = data[0]
        data_rows = data[1:]

        # Dynamically handle column mismatch
        max_columns = max(len(row) for row in data_rows)
        if len(header) < max_columns:
            # Extend the header with placeholder column names
            header.extend([f"Extra_{i}" for i in range(len(header), max_columns)])
        elif len(header) > max_columns:
            raise ValueError("Header has more columns than the data rows.")

        # Create the DataFrame
        df = pd.DataFrame(data_rows, columns=header)

        return df

    def map_calc_order(self, lines, keyword, calc_order_list):
        """
        Maps the calculation order based on the pluvio reference numbers.

        :param lines: List of lines extracted from the output file.
        :param keyword: The keyword to search for in the lines.
        :param calc_order_list: List of calculation order values.

        :return: List of mapped calculation order values.
        """
        calc_order = []
        for line in lines:
            if keyword in line:
                pluvio_ref_num = line.replace(keyword, "").strip().split()
                mapped_values = [f"{calc_order_list[int(num) - 1]} (P.fcst.excess) (mm)" for num in pluvio_ref_num]
                calc_order.append(mapped_values)

        return calc_order

    def del_section(self, lines):
        """
        Deletes a section of lines from the output file.

        :param lines: List of lines extracted from the output file.
        """
        start_idx = next(i for i, line in enumerate(lines) if "Rainfall, mm, in time inc. following time shown" in line)
        end_idx = next(i for i, line in enumerate(lines) if "Pluvi. ref. no." in line and i > start_idx)

        del lines[start_idx:end_idx+1]

    def process_rainfall_excess(self, lines):
        """
        Processes the rainfall excess data from the output file.

        :param lines: List of lines extracted from the output file.

        :return: Pandas DataFrame containing the processed rainfall excess data.
        """
        start_idx = next(i for i, line in enumerate(lines) if "Incs" in line)
        end_idx = next(i for i, line in enumerate(lines) if "Tot." in line and i > start_idx)
        section = lines[start_idx:end_idx]
        header = "".join(section[0]).split()
        data_lines = section[2:-1]
        data = [line.split() for line in data_lines]
        df = pd.DataFrame(data, columns=header)

        del lines[start_idx:end_idx+1]
        return df

    def extract_datetime_index(self, lines):
        """
        Extracts the start datetime, end datetime, and time increment from the output file.

        :param lines: List of lines extracted from the output file.

        :return: Tuple containing the start datetime, end datetime, and time increment.
        """
        datetime_pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
        time_increment_pattern = r"([\d\.]+) hours"

        for line in lines:
            datetime_match = re.search(datetime_pattern, line)
            if datetime_match:
                start_datetime = datetime_match.group(1)
                end_datetime = datetime_match.group(2)
            
            time_increment_match = re.search(time_increment_pattern, line)
            if time_increment_match:
                time_increment = float(time_increment_match.group(1))

        return start_datetime, end_datetime, time_increment