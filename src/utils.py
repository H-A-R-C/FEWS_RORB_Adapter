"""
This module contains utilities for reading and writing data from various file formats.
Each utility is designed for a specific file format, including XML, JSON, and NetCDF files.
Note that some XML utilities are designed for specific inputs, they need to be modified for other uses.
"""

from typing import List
import os
import re
import json
import numpy as np
from lxml import etree
import netCDF4 as nc
import logging

# =============================================================================
# File Reading Utilities
# =============================================================================
# ----------------------------------------------------------------------------
# Read.json file
# ----------------------------------------------------------------------------
class JsonReader:
    def __init__(self, filename: str):
        """
        Initializes the JSON_ReadingUtilities with a specific JSON file.
        :param filepath: Path to the JSON file
        """
        try:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            self.filepath = os.path.join(dir_path, filename)  # Store the file path for potential future reference.
            self.data = self._load_json_file()  # Load the JSON file into a dictionary.
        
        except Exception as e:
            logging.error(f"Failed to initialize JSON file '{self.filepath}': {e}")
            raise FileNotFoundError(f"JSON file '{self.filepath}' not found")
    
    def _load_json_file(self):
        with open(self.filepath, 'r') as file:
            data = json.load(file)
            return data
        
    def extract(self, key: str):
        return self.data[key]
    

# ----------------------------------------------------------------------------
# Read .xml file
# ----------------------------------------------------------------------------
class XMLReader:
    def __init__(self, filepath: str):
        """
        Initializes the XMLReader with a specific XML file.
        :param filepath: Path to the XML file
        """
        try:
            self.filepath = filepath  # Store the file path for potential future reference.
            self.tree = etree.parse(filepath)  # Parse the XML file into an lxml etree structure.
            self.root = self.tree.getroot()  # Store the root element of the XML tree for quick access.
            self.namespace = self.root.nsmap.get(None, '')  # Extract the default namespace if it is defined.
        
        except Exception as e:
            logging.error(f"Failed to initialize XML file '{filepath}': {e}")
            raise FileNotFoundError(f"XML file '{filepath}' not found")
    
    def extract_attribute_from_element(self, element_name: str, attribute_name: str) -> str:
        """
        Extracts the value of a specific attribute from an element.
        """
        try:
            # Find the element by its name.
            elem = self.root.find(f"{{{self.namespace}}}{element_name}")
            if elem is None:
                raise KeyError(f"Element '{element_name}' not found.")
            
            # Extract the attribute value from the element.
            attribs = elem.attrib
            if attribute_name in attribs:
                return attribs[attribute_name]
            else:
                raise AttributeError(f"Attribute '{attribute_name}' not found in element '{element_name}'.")
            
        except Exception as e:
            logging.error(f"Failed to extract from '{self.filepath}': {e}")

    def extract_datetime_from_element(self, element_name: str) -> str:
        """
        Extracts the datetime of a specific attribute from an element.
        Specifically for runinfo.xml
        """        
        try: 
            date = self.extract_attribute_from_element(element_name, 'date')
            time = self.extract_attribute_from_element(element_name, 'time')
            return f"{date} {time}"
        
        except Exception as e:
            logging.error(f"Failed to extract from '{self.filepath}': {e}")

    def extract_element_text(self, element_name: str, index: int = 0) -> str:
        """
        Extracts the text value of a specified element by its name and index (defaults to 0).
        """
        try:
            # Find all elements with the specified name.
            elems = self.root.findall(f"{{{self.namespace}}}{element_name}")
            if len(elems) ==0:
                raise KeyError(f"Element '{element_name}' not found.")
            
            # Check if the index is within the range of the found elements.
            if index >= len(elems):
                raise IndexError(f"Index {index} out of range for element '{element_name}'.")
            
            # Extract the text value of the element at the specified index.
            elem = elems[index]
            if elem.text:
                return elem.text
            else:
                raise ValueError(f"Element '{element_name}' at index {index} has no text.")

        except Exception as e:
            logging.error(f"Failed to extract from '{self.filepath}': {e}")

    def extract_properties_value_from_key(self, search_key_name: str) -> str:
        """
        Extracts the value of a specific subelement based on a 'key' attribute within a 'properties' element.
        Specifically for runinfo.xml
        """
        try:
            # Find the key with the specified name.
            key = self.root.find( f".//{{{self.namespace}}}properties/*[@key='{search_key_name}']")
            if key is None:
                raise KeyError(f"Key '{search_key_name}' not found in element properties.")
            
            # Extract the value attribute of the key.
            attrib = key.attrib.get('value')
            if attrib:
                return attrib
            else:
                raise AttributeError(f"Key '{search_key_name}' has no value attribute.")

        except Exception as e:
            logging.error(f"Failed to extract from '{self.filepath}': {e}")

    def extract_rorb_parameter_value(self, group_id: str, param_search_id: str, param_search_subelem: str) -> str:
        """
        Extracts the text content of a specified subelement defined by a group ID, parameter ID, and subelement field name.
        Specifically for params.xml
        """
        try:
            # Find the group with the @id.
            group = self.root.find(f".//{{{self.namespace}}}group[@id='{group_id}']")
            if group is None:
                raise KeyError(f"Group '{group_id}' not found.")  

            # Find the parameter with the @id in the group.
            parameter = group.find(f".//{{{self.namespace}}}parameter[@id='{param_search_id}']")
            if parameter is None:
                raise KeyError(f"Parameter '{param_search_id}' not found in group '{group_id}'.")
            
            # Find the subelement field within the parameter.
            search_field = parameter.find(f".//{{{self.namespace}}}{param_search_subelem}")
            if search_field is None:
                raise KeyError(f"Element '{param_search_subelem}' not found in parameter '{param_search_id}' of group '{group_id}'.")
            
            # Extract the text content of the subelement field.
            param_txt = search_field.text
            if param_txt:
                return param_txt
            else:
                raise ValueError(f"Element '{param_search_subelem}' in parameter '{param_search_id}' of group '{group_id}' has no text.")
            
        except Exception as e:
            logging.error(f"Failed to extract from '{self.filepath}': {e}")
       
    def extract_rorb_parameter_value_with_conditions(
            self, group_id: str, param_condition_id: str, param_condition_stringValue: str, param_search_id: str, param_search_subelem: str) -> float:
        """
        Extracts the text content of a specified field from a parameter within a group that meets specific conditions.
        Specifically for params.xml
        """
        try:
            # Find all groups with the parameter @id.
            groups = self.root.findall(f".//{{{self.namespace}}}group[@id='{group_id}']")
            if len(groups)==0: # Check if any groups were found.
                raise KeyError(f"Group '{group_id}' not found.")  
            
            # Find the target group that meets the conditions.
            target_group = None
            for group in groups:
                # Find all parameters with the @id.
                params = group.findall(f".//{{{self.namespace}}}parameter[@id='{param_condition_id}']")
                if len(params)==0: 
                    raise KeyError(f"parameter @id '{param_condition_id}' not found in group '{group_id}'.")
                
                # Loop through the parameters to find the one with the correct stringValue.
                for param in params:
                    stringValue_txt = param.find(f".//{{{self.namespace}}}stringValue").text
                    if stringValue_txt == param_condition_stringValue:
                        target_group = group
                        break

            # Check if the target group was found.
            if target_group is None:
                raise KeyError(f"Group '{group_id}' with parameter @id '{param_condition_id}'='{param_condition_stringValue}' not found.")
            
            # Find the parameter with the @id in the target group.
            search_param = target_group.find(f".//{{{self.namespace}}}parameter[@id='{param_search_id}']")
            if search_param is None:
                raise KeyError(f"Parameter '{param_search_id}' not found in group '{group_id}'.")
            
            # Extract the subelement field within the parameter.
            search_param_field = search_param.find(f".//{{{self.namespace}}}{param_search_subelem}")
            if search_param_field is None:
                raise KeyError(f"Subelement '{param_search_subelem}' not found in parameter '{param_search_id}' of group '{group_id}'.")

            search_param_txt = search_param_field.text
            if search_param_txt:
                return float(search_param_txt)
            else:
                raise ValueError(f"Subelement '{param_search_subelem}' in parameter '{param_search_id}' of group '{group_id}' has no text.")

        except Exception as e:
            logging.error(f"Failed to extract from '{self.filepath}': {e}")

    def extract_event_state_variable(self, state_search_locationId: str, state_search_parameterId: str, missVal_fill = np.nan) -> float:
        """
        Extracts the event value of a specific locationId and parameterId.
        Specifically for input_state.xml
        """

        try:
            # Find all series.
            series = self.root.findall(f'.//{{{self.namespace}}}series')

            # Find the target serie that meets the conditions.
            target_serie = None
            target_header = None
            for serie in series:
                # Find the header of the serie.
                header = serie.find(f'.//{{{self.namespace}}}header')                
                locationId = header.find(f'.//{{{self.namespace}}}locationId').text
                parameterId = header.find(f'.//{{{self.namespace}}}parameterId').text
                if locationId == state_search_locationId and parameterId == state_search_parameterId:
                    target_serie = serie 
                    target_header = header  
                    break

            # Check if the target serie was found.
            if target_serie is None or target_header is None:
                raise KeyError(f"Serie with locationId '{state_search_locationId}' and/or parameterId '{state_search_parameterId}' not found.")

            # Extract the event value from the target serie.
            event = target_serie.find(f'.//{{{self.namespace}}}event')
            val = float(event.get('value'))
            missVal = float(target_header.find(f'.//{{{self.namespace}}}missVal').text)
            if val:
                if val == missVal:
                    return missVal_fill
                else:
                    return val
            else:
                raise ValueError(f"Value for locationId '{state_search_locationId}' and parameterId '{state_search_parameterId}' has no text.")
                
        except Exception as e:
            logging.error(f"Failed to extract from '{self.filepath}': {e}")


# ----------------------------------------------------------------------------
# Write .xml file
# ----------------------------------------------------------------------------
class XMLWriter:
    def __init__(self):
        self.template = """<TimeSeries xmlns="http://www.wldelft.nl/fews/PI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.wldelft.nl/fews/PI http://fews.wldelft.nl/schemas/version1.0/pi-schemas/pi_timeseries.xsd" version="1.2">
    <daylightSavingObservingTimeZone>AET</daylightSavingObservingTimeZone></TimeSeries>"""        
        self.root = etree.fromstring(self.template)
        self.headers_cache = {}

    def _generate_header_xml(self, location_id: str, parameter_id: str, start_date: str, start_time: str, end_date: str, end_time: str, unit: str):
        """
        Generate the header XML element for a specific location, parameter, and qualifier.
        """
        key = (location_id, parameter_id) 
        
        # check if the header is already in the cache
        if key not in self.headers_cache:
            header = etree.Element("header")
            etree.SubElement(header, "type").text = "instantaneous"
            etree.SubElement(header, "locationId").text = location_id
            etree.SubElement(header, "parameterId").text = parameter_id
            etree.SubElement(header, "timeStep", unit="second", multiplier="900") # Fixed timestep!!!
            etree.SubElement(header, "startDate", date=start_date, time=start_time)
            etree.SubElement(header, "endDate", date=end_date, time=end_time)
            etree.SubElement(header, "missVal").text = "-99.0"
            etree.SubElement(header, "units").text = unit
            self.headers_cache[key] = header
            
        return self.headers_cache[key]

    def write_df_to_xml(self, df, output_filepath: str):
        # get the date and time from the DataFrame index
        df['date'] = df.index.date
        df['time'] = df.index.time

        grouped = df.melt(id_vars=['date', 'time'], var_name='variable', value_name='value')
        grouped = grouped.groupby('variable', sort=False)

        # write the XML file
        try: 
            with open(output_filepath, 'wb') as file:
                file.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
                file.write(self.template.encode().replace(b'></TimeSeries>', b'>'))

                # iterate over the groups and write the XML elements
                for var, group in grouped:
                    pattern = re.compile(r'([^\(]+)\(([^\)]+)\)\s+\((.*?)\)')
                    matches = pattern.findall(var)
                    loc_id, param_id, unit = matches[0]
                    
                    # generate the header XML element
                    header_xml = self._generate_header_xml(
                        location_id=loc_id, 
                        parameter_id=param_id, 
                        start_date=group['date'].iloc[0].strftime('%Y-%m-%d'), 
                        start_time=group['time'].iloc[0].strftime('%H:%M:%S'),
                        end_date=group['date'].iloc[-1].strftime('%Y-%m-%d'), 
                        end_time= group['time'].iloc[-1].strftime('%H:%M:%S'),
                        unit=unit.replace('(', '').replace(')', '')
                        )
                    
                    file.write(b'<series>')
                    file.write(etree.tostring(header_xml, pretty_print=True))

                    # iterate over the rows in the group and write the event XML elements
                    for index, row in group.iterrows():
                        event_xml = etree.Element(
                            "event", 
                            date=str(row['date']), 
                            time=str(row['time']), 
                            value=str(row['value'])
                            )
                        
                        file.write(etree.tostring(event_xml, pretty_print=True))

                    file.write(b'</series>')
                file.write(b'</TimeSeries>')
                        
        except Exception as e:
            logging.error(f"Failed to write to '{output_filepath}': {e}")

    def write_df_to_xml_loc(self, df, output_filepath: str):
        """
        Write the DataFrame to an XML file.
        """        
        # get the date and time from the DataFrame index
        df['date'] = df.index.date
        df['time'] = df.index.time
                
        # group the DataFrame by variable
        grouped = df.melt(id_vars=['date', 'time', 'location_id'], var_name='variable', value_name='value')
        grouped = grouped.groupby('variable')
        
        # write the XML file
        try: 
            with open(output_filepath, 'wb') as file:
                file.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
                file.write(self.template.encode().replace(b'></TimeSeries>', b'>'))

                # iterate over the groups and write the XML elements
                for var, group in grouped:
                    pattern = re.compile(r'([^\(]+)\((.*?)\)')
                    matches = pattern.findall(var)
                    param_id, unit = matches[0]
                    
                    # generate the header XML element
                    header_xml = self._generate_header_xml(
                        location_id=group['location_id'].iloc[0], 
                        parameter_id=param_id, 
                        start_date=group['date'].iloc[0].strftime('%Y-%m-%d'), 
                        start_time=group['time'].iloc[0].strftime('%H:%M:%S'),
                        end_date=group['date'].iloc[-1].strftime('%Y-%m-%d'), 
                        end_time= group['time'].iloc[-1].strftime('%H:%M:%S'),
                        unit=unit.replace('(', '').replace(')', '')
                        )
                    
                    file.write(b'<series>')
                    file.write(etree.tostring(header_xml, pretty_print=True))

                    # iterate over the rows in the group and write the event XML elements
                    for index, row in group.iterrows():
                        event_xml = etree.Element(
                            "event", 
                            date=str(row['date']), 
                            time=str(row['time']), 
                            value=str(row['value'])
                            )
                        
                        file.write(etree.tostring(event_xml, pretty_print=True))

                    file.write(b'</series>')
                file.write(b'</TimeSeries>')
                        
        except Exception as e:
            logging.error(f"Failed to write to '{output_filepath}': {e}")


# ----------------------------------------------------------------------------
# Read .nc file
# ----------------------------------------------------------------------------
class NetCDFReader:
    def __init__(self, filepath: str):
        """
        Initializes the NetCDFReader with a specific XML file.
        
        :param filepath: Path to the NetCDF file
        """
        try:
            self.filepath = filepath  # Store the file path for potential future reference.
            self.dataset = nc.Dataset(filepath, 'r')

        except Exception as e:
            logging.error(f"Failed to initialize NetCDF file '{filepath}': {e}")
            raise FileNotFoundError(f"NetCDF file '{filepath}' not found")
    
    def extract_variable_list(self, variable_name: str, missVal_attribute = None, missVal_fill = 0) -> List:
        """
        Extracts the list of values of a specific variable from the NetCDF file. 
        If a missing value attribute is provided, replaces missing values with fill.
        """
        try:
            # Check if the variable exists in the NetCDF file.
            if variable_name not in self.dataset.variables:
                raise KeyError(f"Variable '{variable_name}' not found.")
            
            # Extract all data from the variable as a list.
            var = self.dataset.variables[variable_name]
            var_lst = var[:].data.tolist()

            # Replace missing values with 0 if the missing value attribute is provided.
            if missVal_attribute is not None:
                target_value = var.getncattr(missVal_attribute) if missVal_attribute in var.ncattrs() else None
                if target_value:
                    filled_var_lst = DataUtilities.replace_missing_value(var_lst, target_value, fill_value=missVal_fill)
                    return filled_var_lst
                else:
                    raise KeyError(f"Missing value attribute '{missVal_attribute}' not found for variable '{variable_name}'.")
            else:
                if len(var_lst) > 0:
                    return var_lst
                else:
                    raise ValueError(f"Variable '{variable_name}' has no data.")    
            
        except Exception as e:
            logging.error(f"Failed to extract from '{self.filepath}': {e}")

    def extract_variable_value_with_conditions(self, condition_variable_name: str, condition_variable_value, search_variable_name: str, missVal_attribute = None) -> float:
        """
        Extracts the value of a specific variable based on conditions from other variables.
        """
        try:
            # Extract the list of values for the condition variable.
            big_byte_list = self.extract_variable_list(condition_variable_name)
            if big_byte_list is None:
                raise KeyError(f"Condition variable '{condition_variable_name}' not found.")
            
            # Decode the list of byte strings to regular strings.
            if any(isinstance(item,bytes) for sublist in big_byte_list for item in (sublist if isinstance(sublist, list) else [sublist])):
                decoded_var_list = DataUtilities.decode_big_byte_list_to_string_list(big_byte_list)
            else:
                decoded_var_list=big_byte_list
            
            # Find the index of the condition variable value in the decoded list.
            try:
                var_idx = decoded_var_list.index(condition_variable_value)
            except:
                raise KeyError(f"Condition variable value '{condition_variable_value}' not found in '{condition_variable_name}'.")
            
            # Extract the list of values for the search variable.
            search_var_list = self.extract_variable_list(search_variable_name, missVal_attribute=missVal_attribute)
            if search_var_list is None:
                raise KeyError(f"Search variable '{search_variable_name}' or missing value attribute '{missVal_attribute}' not found.")
            
            search_var_list = [sublist if isinstance(sublist[0], list) else [sublist] for sublist in search_var_list]
            # Transpose the search variable list and extract the value at the condition variable index.  
            transposed_list = DataUtilities.flatten_and_transpose(search_var_list)
            search_var_val = transposed_list[var_idx]

            if search_var_val:
                return search_var_val
            else:
                raise ValueError(f"Search variable '{search_variable_name}' has no data.")
        
        except Exception as e:
            logging.error(f"Failed to extract from '{self.filepath}': {e}")


# =============================================================================
# File Writing Utilities
# =============================================================================
# ----------------------------------------------------------------------------
# Write template file
# ----------------------------------------------------------------------------
class TemplateWriter:
    def __init__(self, template_filepath, output_filepath):
        self.template_filepath = template_filepath
        self.output_filepath = output_filepath

    def fill(self, replacements_dict):
        """
        Fill the variables in the template with the values in the replacements dictionary.
        """
        try:
            with open(self.template_filepath, 'r') as file:
                template = file.read()

            filled_template = template.format(**replacements_dict)
            output_dir = os.path.dirname(self.output_filepath)

            # Create the output directory if it does not exist.
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Write the filled template to the output file.
            with open(self.output_filepath, 'w') as file:
                file.write(filled_template)

        except Exception as e:
            
            logging.error(f"Failed to write to '{self.output_filepath}': {e}")
    
    def clear_empty_lines(self):
        """
        Remove empty lines from the output file.
        """
        try:
            with open(self.output_filepath, 'r') as file:
                lines = file.readlines()

            # Remove empty lines.
            non_empty_lines = [line for line in lines if line.strip()]

            # Write the non-empty lines back to the output file.
            with open(self.output_filepath, 'w') as file:
                file.writelines(non_empty_lines)

        except Exception as e:
            logging.error(f"Failed to clear empty lines in '{self.output_filepath}': {e}")



# =============================================================================
# Data Processing Utilities
# =============================================================================         
class DataUtilities:
    @staticmethod
    def decode_big_byte_list_to_string_list(big_byte_list: List[List[bytes]]) -> List[str]:
        """
        Converts a list of byte strings to a list of regular strings.
        """
        try: 
            decoded_list =  [''.join(byte.decode('utf-8') for byte in x if byte != b'') for x in big_byte_list]
            return decoded_list
        
        except Exception as e:
            logging.error(f"Failed to decode big_byte_list: {e}")

    @staticmethod
    def replace_missing_value(nested_list: List, target_value, fill_value) -> float:
        """
        Recursively replaces target_value with fill_value in a nested list structure.
        """
        try:
            for index, item in enumerate(nested_list):
                if isinstance(item, list):  # If item is a list, recursively call the function
                    nested_list[index] = DataUtilities.replace_missing_value(item, target_value, fill_value)
                elif item == target_value:  # If item is the target_value, replace it
                    nested_list[index] = fill_value
            return nested_list

        except Exception as e:
            logging.error(f"Failed to replace missing value as zero: {e}")

    @staticmethod
    def flatten_and_transpose(nested_list: List) -> List:
        """
        Flattens a nested list, extracting the first element of each sublist,
        and then transposes the resulting list.        
        """
        try:
            flattened_list = [item[0] for item in nested_list]
            transposed_list = list(map(list, zip(*flattened_list)))
            return transposed_list

        except Exception as e:
            logging.error(f"Failed to flatten and transpose list: {e}")

    @staticmethod
    def flatten(nested_list: List) -> List:
        """
        Recursively flattens a nested list until no sublists remain.
        """
        try:
            flat_list = []

            for item in nested_list:
                if isinstance(item, list): # If item is a list, recursively call the function
                    flat_list.extend(DataUtilities.flatten(item))
                else: # If item is not a list, add it to the flat_list
                    flat_list.append(item)

            return flat_list

        except Exception as e:
            logging.error(f"Failed to flatten list: {e}")


if __name__ == '__main__':
# #     logging.basicConfig(level=logging.DEBUG, filename='xml_utilities.log', format='%(asctime)s - %(levelname)s - %(message)s')

#     rain_filepath = r"S:\3_Projects\SHL00067\5_Technical\1_Adapter\RORB-FEWS-adapter\examples\talbingo_rog_local-rog\to_rorb\input_rain.nc"
#     rain = NetCDFReader(rain_filepath)
#     big_byte_list = rain.extract_variable_list('station_id')
#     print(DataUtilities.decode_big_byte_list_to_string_list(big_byte_list))
#     P_lst = rain.extract_variable_list('P', missVal_attribute='_FillValue')
#     # print(P_lst)
#     # print(DataUtilities.flatten_and_transpose(P_lst))

#     transfer_filepath = r"S:\3_Projects\SHL00067\5_Technical\1_Adapter\RORB-FEWS-adapter\examples\talbingo_rog_local-rog\to_rorb\input_transfer.nc"
#     transfer = NetCDFReader(transfer_filepath)
#     transfer.extract_variable_value_with_conditions('station_id', '410542', 'Qtrans_forecast', missVal_attribute='_FillValue')

    meteo_filepath = r"S:\3_Projects\SHL00067\5_Technical\1_Adapter\RORB-FEWS-adapter\examples\talbingo_rog_local-rog\to_rorb\input_meteo.nc"
    meteo = NetCDFReader(meteo_filepath)
    t = meteo.extract_variable_list('T_observed', missVal_attribute='_FillValue', missVal_fill=np.nan)
    print(t)

    # operation_filepath = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\input_operation.nc"
    # operation = NetCDFReader(operation_filepath)
    # t = operation.extract_variable_list('Outflow', missVal_attribute='_FillValue', missVal_fill=np.nan)
    # print(t)
