"""
This module is used to format the input files for the RORB model.
Each class formats a specific input file for the RORB model:
- PARFormatter: formats the .par file
- STMFormatter: formats the .stm file
- SnowFormatter: formats the .dat file for snow
- TransferFormatter: formats the .dat file for transfer
Note that the gateops files are not here as they only require initial water level values.

A FormulaUtilities class is used to calculate:
- the number of data points from the start and end datetimes
- the baseflow timeseries based on parameters
- the snowpack density based on snow depth and water content

The attributes of each class are properties that return the formatted strings for each section of the input file, except transfers.
Formulas are used to calculate baseflows and snowpack densities, see the FormulatUtilities class.

Dependencies:
- input_compiler.py: contains the classes used to read the input files
- rorb_config.json: contains the rorb model configuration settings
- fews_config.json: contains the fews system settings
"""

from src.input_compiler import *
from numpy import interp
import datetime
import zoneinfo

# =============================================================================
# RORB file formatters
# =============================================================================   
class ConfigReader:
    def __init__(self):
        self.config = JsonReader("rorb_config.json")
        self.rorb_isa_list = self.config.extract("rorb_isa_list")
        self.rorb_bf_list = self.config.extract("rorb_bf_list")
        self.rorb_dam_list = self.config.extract("rorb_dam_list")
        self.rorb_snow_list = self.config.extract("rorb_snow_list")
        self.rorb_trans_list = self.config.extract("rorb_trans_list")
        self.rorb_meteo_list = self.config.extract("rorb_meteo_list")
        self.rorb_subarea_calc_order_list = self.config.extract("rorb_subarea_calc_order_list")
        self.rorb_hydrograph_calc_order_list = self.config.extract("rorb_hydrograph_calc_order_list")
        self.rorb_snowmelt_elezone_priority_dict = self.config.extract("rorb_snow_elezone_priority_dict")

        self.fewsconfig = JsonReader("fews_config.json")
        self.timezone = self.fewsconfig.extract("timezone")
        self.rain_timestep = self.fewsconfig.extract("rain_timestep_mins")
        self.gateops_timestep = self.fewsconfig.extract("gateops_timestep_mins")
        self.trans_timestep = self.fewsconfig.extract("trans_timestep_mins")
        self.operation_timestep = self.fewsconfig.extract("operation_override_timestep_mins")
        self.hydrograph_timestep = self.fewsconfig.extract("recorded_hydrograph_timestep_mins")


# ----------------------------------------------------------------------------
# Format .par file
# ----------------------------------------------------------------------------
class PARFormatter(ConfigReader):
    """
    A class to format the par files for the RORB model.
    
    Example Usage:
    formatter = PARFormatter(runinfo_xml, params_xml)
    formatter.loss_params_isa
    formatter.routing_params_isa
    """
    def __init__(self, runinfo_xml, params_xml):
        super().__init__()  # Initialize base class

        # Load data models
        self.runinfo = RunInfo(runinfo_xml)
        self.params_inst = Params(params_xml)

    @property
    def routing_params_isa(self):
        isa_params = self.params_inst.isa
        result_string = ""
        
        for id in self.rorb_isa_list:
            isa = isa_params.get(f"{id}")
            if isa:
                result_string += f"ISA  {id:<3}: {isa.Kc}, {isa.m}\n"

        return result_string.strip()
    
    @property
    def loss_params_isa(self):
        isa_params = self.params_inst.isa
        result_string = ""
        
        for id in self.rorb_isa_list:
            isa = isa_params.get(f"{id}")
            if isa:
                result_string += f"ISA  {id:<3}: {isa.IL}, {isa.CL}\n"

        return result_string.strip()
    

# ----------------------------------------------------------------------------
# Format .stm file
# ----------------------------------------------------------------------------
class STMFormatter(ConfigReader):
    """
    A class to format the stm files for RORB model. 
    
    Example Usage:
    STMFormatter.configure(runinfo_xml, rain_netcdf, params_xml)
    STMFormatter.stm_setting
    STMFormatter.pluvio_setting
    """
    def __init__(self, runinfo_xml, rain_netcdf, params_xml):
        super().__init__()  # Initialize base class

        # Load data models
        self.runinfo = RunInfo(runinfo_xml)
        self.rain_inst = Rain(rain_netcdf)
        self.params_inst = Params(params_xml)

        # Perform initial data calculations
        self.num_data = self._calculate_num_data_from_datetimes()
        self._validate_rain_data_length()

    def _calculate_num_data_from_datetimes(self):
        num_data = FormulatUtilities.calculate_num_data_from_datetimes(
            self.runinfo.startDateTime, self.runinfo.endDateTime, self.timezone, self.rain_timestep)

        return num_data
    
    def _validate_rain_data_length(self):
        try:
            # Calculate the number of rain data
            id_example = self.rorb_subarea_calc_order_list[0]
            rain_example = self.rain_inst.sub[id_example]
            num_rain = len(rain_example)     

            # Check if the number of rain data is equal to the calculation
            if num_rain != self.num_data:
                raise ValueError(f"Number of rain data ({num_rain}) does not match with calculated number of data ({self.num_data})")
            else:
                pass

        except Exception as e:
            logging.error(f"Failed to format stm file: {e}")
    
    @property
    def stm_setting(self):
        # Format: timestep, num_data, 1, num_subarea, 1
        lst = [str(self.rain_timestep/60), self.num_data, 1, len(self.rorb_subarea_calc_order_list), 1]
        return FormatUtilities.format_floats(lst, decimal=0, items_per_line=10, end_string=", -99")
    
    @property
    def pluvio_setting(self):
        # Format: start_burst1, end_burst1, start_burst2, end_burst2, ...
        lst = [0, self.num_data]
        return FormatUtilities.format_floats(lst, decimal=0, items_per_line=10, end_string=", -99")
    
    @property    
    def all_subarea_temporal_patterns(self):
        calc_order = self.rorb_subarea_calc_order_list

        result_string = ""  # Initialize the result string
        for i in range(0, len(calc_order)):
            id = calc_order[i]

            # Get the value of the sub-variable
            value = self.rain_inst.sub[f"{id}"]
            sub_total = sum(value)

            # Temporal pattern = value/sub_total*100
            temporal = [x / sub_total * 100 if sub_total != 0 else 0 for x in value]
            formatted_temporal = FormatUtilities.format_floats(temporal, decimal=2, items_per_line=10, end_string=", -99")
            
            # Add the formatted value to the result string
            if i > 0:
                result_string += "\n"  # Add a newline before each new entry except the first
            result_string += f"Calc_order_{i+1} temporal pattern with pre-burst (% of depth)\n{formatted_temporal}"
        
        return result_string
    
    @property   
    def subarea_rainfall(self):
        calc_order = self.rorb_subarea_calc_order_list

        # Calculate sub-total of each subarea in the calculation order
        sub_total_lst = []
        for i in range(0, len(calc_order)):
            id = calc_order[i]

            # Get the value of the sub-variable
            value = self.rain_inst.sub[f"{id}"]
            sub_total_lst.append(sum(value))

        # Format the sub-total list
        return FormatUtilities.format_floats(sub_total_lst, decimal=2, items_per_line=10, end_string=", -99")
    
    @property
    def pluvio_choice(self):
        # Format pluvio vchoice as [1, 2, 3, ... , num_subarea]
        num_sub = len(self.rorb_subarea_calc_order_list)+1
        pliuvio_lst = list(range(1, num_sub))
        return FormatUtilities.format_floats(pliuvio_lst, decimal=0, items_per_line=10, end_string=", -99")
    
    @property
    def baseflow_setting(self):
        # Format: start_burst1, end_burst1, start_burst2, end_burst2, ..., -99
        lst = [0, self.num_data-1] * len(self.rorb_bf_list)
        return FormatUtilities.format_floats(lst, decimal=0, items_per_line=20, end_string=", -99")
    
    @property
    def all_baseflow_hydrographs(self):
        calc_order = self.rorb_hydrograph_calc_order_list

        result_string = ""  # Initialize the result string
        for i in range(0, len(calc_order)):
            id = calc_order[i]
            
            # Get the baseflow parameters
            const_val = self.params_inst.bf.get(f"{id}").const
            multi_val = self.params_inst.bf.get(f"{id}").multi
            start_val = self.params_inst.bf.get(f"{id}").start

            # Calculate the start index of scaling in the timeseries
            # For example, if the start is 1(hr) and the timestep is 15 minutes, the start index is 5
            start_num = start_val * 60 / self.rain_timestep
            bf_lst = FormulatUtilities.calculate_baseflow(const_val, multi_val, start_num, self.num_data)
            formatted_bf = FormatUtilities.format_floats(bf_lst, decimal=2, items_per_line=10, end_string=", -99")
            
            # Add the formatted value to the result string
            if i > 0:
                result_string += "\n"
            result_string += f"Baseflow_calc_order_{i+1}\n{formatted_bf}"

        return result_string

 
# ----------------------------------------------------------------------------
# Format .dat file (snowmelt)
# ----------------------------------------------------------------------------
class SNOWFormatter(ConfigReader):
    """
    A class to format the dat files for snow in RORB model.
    
    Example Usage:
    SnowFormatter.configure(runinfo_xml, meteo_netcdf, state_xml)
    SnowFormatter.snowmelt_temperature_timeseries
    SnowFormatter.snowmelt_water_content_elezone
    """
    def __init__(self, runinfo_xml, meteo_netcdf, state_xml):
        super().__init__()  # Initialize base class

        # Load data models
        self.runinfo = RunInfo(runinfo_xml)
        self.meteo_inst = Meteo(meteo_netcdf)
        self.state_inst = State(state_xml)

    @property
    def temp_timeseries_lst(self):
        id = self.rorb_meteo_list[0]
        return self.meteo_inst.snow[id].T
    
    @property
    def wind_timeseries_lst(self):
        id = self.rorb_meteo_list[0]
        return self.meteo_inst.snow[id].W
    
    @property
    def temp_timeseries(self):
        temp = self.temp_timeseries_lst
        num_temp = len(temp)+1
        return FormatUtilities.format_floats(temp, decimal=1, items_per_line=num_temp, end_string="")
    
    @property
    def temp_number_increment(self):
        return len(self.temp_timeseries)+1
    
    @property      
    def wind_timeseries(self):
        wind = self.wind_timeseries_lst
        num_temp = len(wind)+1
        return FormatUtilities.format_floats(wind, decimal=1, items_per_line=num_temp, end_string="")
    
    @property
    def wind_number_increment(self):
        return len(self.wind_timeseries)+1
    
    def snow_param_elezone_priority_dict(self, param_name):
        param_dict = {}    

        # Loop through the elezone priority dictionary
        for key, value in self.rorb_snowmelt_elezone_priority_dict.items():
            elezone = key
            priority_lst = value

            # Create a list of the sub-variable values for each elezone
            elezone_list = []
            for id in priority_lst:
                # Get the value of the sub-variable
                attrib = self.state_inst.snow[f"{id}"]
                param_val = getattr(attrib, param_name)
                elezone_list.append(param_val)
            
            # Select the first non-missing value from the list
            # If all values are missing, set the default value to 0
            selected_val = FormulatUtilities.select_from_priority(data_list=elezone_list, missVal=None)
            if selected_val is None:
                selected_val = 0
                logging.warning(f"Missing {param_name} for elezone {elezone}. Default value is set to 0")
            
            # Add the selected value to the dictionary
            param_dict[elezone] = selected_val

        return param_dict
    
    @property
    def snowmelt_water_content_elezone(self):
        # Calculate the water content for each elezone
        WD_dict = self.snow_param_elezone_priority_dict(param_name="WD")

        # Format the water content values
        water_content_list = [value for key, value in WD_dict.items()]
        num = len(water_content_list)+1
        return FormatUtilities.format_floats(water_content_list, decimal=2, items_per_line=num, end_string="")
    
    @property
    def snowmelt_weighted_snowpack_density(self):
        # Calculate the snowpack density for each elezone
        WD_dict = self.snow_param_elezone_priority_dict(param_name="WD")
        SD_dict = self.snow_param_elezone_priority_dict(param_name="SD")
        snowpack_density_dict = {key: FormulatUtilities.calculate_snowpack_density(SD_dict[key], WD_dict[key]) for key in SD_dict}

        # Calculate the weighted snowpack density
        weighted_snowpack_density = FormulatUtilities.weight_snowpack_density_elezone(snowpack_density_dict)

        # Format the water content values
        return str(round(weighted_snowpack_density,2))

# ----------------------------------------------------------------------------
# Format .dat file (GateOps)
# ----------------------------------------------------------------------------
class GateOpsFormatter(ConfigReader):
    def __init__(self, state_xml):
        super().__init__()  # Initialize base class

        # Load data models
        self.state_inst = State(state_xml)
        self.timestep_hour = self.gateops_timestep/60

    def initial_storage(self, id, gateops_path):
        level = self.state_inst.dam.get(id).level
        HS_relationship = []

        try:
            with open(gateops_path, "r") as f:
                lines = f.readlines()
            
            gate_opening_num = int(lines[6].split("!")[0].strip()) # Get the number of gate-opening pairs
            if gate_opening_num > 1:
                config_line_num = 12
            else:
                config_line_num = 9
            
            SQ_relationship_pairs = int(lines[5].split("!")[0].strip()) # Get the number of storage-outflow pairs
            level_opening_paris = int(lines[7].split("!")[0].strip()) # Get the number of storage-opening pairs
            HS_relationship_pairs = int(lines[8].split("!")[0].strip()) # Get the number of storage-elevation pairs
            HS_start_index = config_line_num + SQ_relationship_pairs + level_opening_paris # Get the start index of the HS relationship pairs
            HS_lines = lines[HS_start_index:(HS_start_index + HS_relationship_pairs)]
            
            for line in HS_lines:
                elevation, storage = map(float, line.split())
                HS_relationship.append((elevation, storage))

            reference_storage = interp(level, [elevation for elevation, storage in HS_relationship], [storage for elevation, storage in HS_relationship])
        except Exception as e:
            raise RuntimeError(f"An error occurred while processing the file: {e}")

        return round(reference_storage)
        
# ----------------------------------------------------------------------------
# Format .dat file (transfer)
# ----------------------------------------------------------------------------
class TRANSFormatter(ConfigReader):
    """
    A class to format the dat files for transfer in RORB model.
    
    Example Usage:
    """
    def __init__(self, runinfo_xml, transfer_netcdf):
        super().__init__()  # Initialize base class

        # Load data models
        self.runinfo = RunInfo(runinfo_xml)
        self.trans_inst = Transfer(transfer_netcdf)
        
        # Perform initial data calculations
        self.num_data = self._calculate_num_data_from_datetimes()
        self.timestep_hour = self.trans_timestep/60

    def _calculate_num_data_from_datetimes(self):
        num_data = FormulatUtilities.calculate_num_data_from_datetimes(
            self.runinfo.startDateTime, self.runinfo.endDateTime, self.timezone, self.trans_timestep)
        return num_data
    
    def transfer_Qtrans(self, id):
        Qtrans = self.trans_inst.trans.get(f"{id}").Qtrans
        return FormatUtilities.format_floats(Qtrans, decimal=0, items_per_line=1, end_string="")
    
    def transfer_Qgen(self, id):
        Qgen = self.trans_inst.trans.get(f"{id}").Qgen
        return FormatUtilities.format_floats(Qgen, decimal=0, items_per_line=1, end_string="")


# ----------------------------------------------------------------------------
# Format .dat file (gate operation override)
# ----------------------------------------------------------------------------
class OpFormatter(ConfigReader):
    """
    A class to format the dat files for gate operation override in RORB model.
    
    Example Usage:
    """
    def __init__(self, runinfo_xml, operation_netcdf):
        super().__init__()  # Initialize base class

        # Load data models
        self.runinfo = RunInfo(runinfo_xml)
        self.operation_inst = Operation(operation_netcdf)
        
        # Perform initial data calculations
        self.timestep_hour = self.operation_timestep/60
    
    def override_outflow(self, id):
        Outflow = self.operation_inst.dam.get(f"{id}").Outflow
        Opening = self.operation_inst.dam.get(f"{id}").Opening
        formatted_outflow = FormatUtilities.format_floats(Outflow, decimal=4, items_per_line=1, end_string="")
        formatted_opening = FormatUtilities.format_floats(Opening, decimal=1, items_per_line=1, end_string="")

        # Split formatted strings into lists of individual values & combine into pairs
        outflow_list = formatted_outflow.split("\n")
        opening_list = formatted_opening.split("\n")
        combined_pairs = [f"{outflow},{opening}" for outflow, opening in zip(outflow_list, opening_list)]

        # Join pairs with newline characters
        result = "\n".join(combined_pairs)
        self.num_data = len(Outflow)
        return result
# ----------------------------------------------------------------------------
# Format .dat file (gate operation override)
# ----------------------------------------------------------------------------
class HydrographFormatter(ConfigReader):
    def __init__(self, runinfo_xml, hydrograph_netcdf):
        super().__init__()  # Initialize base class

        # Load data models
        self.runinfo = RunInfo(runinfo_xml)
        self.gauge_inst = Hydrograph(hydrograph_netcdf)
        
        # Perform initial data calculations
        self.timestep_hour = self.hydrograph_timestep/60

    def find_print_num(self, gauge, catg_path):
        try:
            with open(catg_path, "r") as f:
                lines = f.readlines()
                
            print_keywords = [
                "7.2                                              ,                                  PRINT",
                "7                                                ,                                  PRINT"
            ]

            catg_print_num = 0
            
            for i, line in enumerate(lines):
                if line.startswith("C"):
                    continue  # Ignore lines starting with "C"

                if gauge in line:
                    break

                if any(keyword in line for keyword in print_keywords):
                    catg_print_num += 1
            
            return catg_print_num
        except Exception as e:
            raise RuntimeError(f"An error occurred while processing the CATG file: {e}")

    def recorded_hydrograph(self, id):
        recorded_hydrograph = self.gauge_inst.gauge.get(f"{id}")
        recorded_hydrograph = recorded_hydrograph[0]
        self.num_data = len(recorded_hydrograph)
        return FormatUtilities.format_floats(recorded_hydrograph, decimal=14, items_per_line=1, end_string="")


# =============================================================================
# Formulat Utilities
# =============================================================================
class FormulatUtilities:
    @staticmethod
    def calculate_num_data_from_datetimes(startDateTime, endDateTime, timezone, timestep):
        """
        Calculate the number of data based on the start and end datetime, timezone, and timestep.
        Note timesteo is in minutes.
        """
        # Convert to datetime object
        start = datetime.datetime.strptime(startDateTime, "%Y-%m-%d %H:%M:%S")
        end = datetime.datetime.strptime(endDateTime, "%Y-%m-%d %H:%M:%S")

        # Localize the datetime (convert naive to aware datetime object)
        tz = zoneinfo.ZoneInfo(timezone)
        start_dateime = start.replace(tzinfo=tz)
        end_dateime = end.replace(tzinfo=tz)

        # Calculate the number of data
        total_minutes = (end_dateime-start_dateime).total_seconds() / 60
        num_data = int(total_minutes / timestep) + 1

        return num_data
    
    @staticmethod
    def calculate_baseflow(const, multi, start_num, length):
        """
        Calculate the baseflow timeseries using the formula:
        baseflow[i] = const if i < start_num
        baseflow[i] = baseflow[i] * multi if i >= start_num
        """
        # Ensure 'start' and 'length' are integers
        start_num = int(start_num)
        length = int(length)

        # Create the list with the constant value
        result = [const] * length
    
        # Apply the scaling factor starting from the 'start' index
        for i in range(start_num, length):
            result[i] = result[i-1] * multi
    
        return result
    
    @staticmethod
    def calculate_snowpack_density(SD, WD):
        """
        Calculate the snow water content using the formula:
        water_content = SD / WD
        """
        return SD / WD if WD != 0 else 0

    @staticmethod
    def weight_snowpack_density_elezone(snowpack_density_dict):
        """
        Calculate the weighted snowpack density using the formula:
        weighted_density = sum(snowpack_density_dict[elezone] * weighting_dict[elezone])
        """
        # Assign the weighting factor for each elezone, sum should be 1
        weighting_dict = {"1": 1/9, "2": 1/9, "3": 1/9, "4": 1/9, "5": 1/9, "6": 1/9, "7": 1/9, "8": 1/9, "9": 1/9}

        # Calculate the weighted snowpack density
        weighted_dict = {key: snowpack_density_dict[key] * weighting_dict[key] for key in snowpack_density_dict}
        return sum(weighted_dict.values())

    @staticmethod
    def select_from_priority(data_list, missVal):
        """
        Select the first non-missing value from a list of data.
        If all values are missing, return the fill_ifallmissing value.
        """
        for item in data_list:
            if item != missVal:
                return item
        return item
    
    
# =============================================================================
# Format Utilities
# =============================================================================
class FormatUtilities:
    @staticmethod
    def format_floats(data_list, decimal=1, items_per_line=10, end_string=", -99"):
        """
        Format a list of floats and strings into a string with a fixed number of items per line.
        Floats are formatted to a specified number of decimal places. Strings are included as is.
        The last item of each line is -99.
        """
        lines = []
        for i in range(0, len(data_list), items_per_line):
            line_items = []
            for item in data_list[i:i+items_per_line]:
                if isinstance(item, float):  # Check if the item is a float
                    formatted_item = f"{item:.{decimal}f}"  # Format float to specified decimal places
                else:
                    formatted_item = str(item)  # Convert non-floats to string without formatting
                line_items.append(formatted_item)
            lines.append(", ".join(line_items))

        # Add -99 at the end of each line and combine them into a single string
        return "\n".join(lines) + end_string
    
    @staticmethod
    def format_lists(list):
        return "\n".join(list)
    

# if __name__ == '__main__':
#     runinfo_xml = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\runinfo.xml"
#     state_xml = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\input_state.xml"
#     params_xml = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\params.xml"
#     transfer_netcdf = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\input_transfer.nc"
#     rain_netcdf = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\input_rain.nc"
#     meteo_netcdf = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\input_meteo.nc"
#     operation_netcdf = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\input_operation.nc"
#     hydrograph_netcdf = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\input_hydrograph.nc"

#     gateops = GateOpsFormatter(state_xml)
#     happy_jacks_filename = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\model\templates\Template_GateOps_HappyJacks.dat"

#     print(gateops.initial_storage("410571", happy_jacks_filename))


    # rain = Rain(rain_netcdf)
    # print(rain.sub['CR'])
    # print(FormatUtilities.format_floats(rain.sub['CR'], 2, 10))
    
    # stm = STMFormatter(runinfo_xml, rain_netcdf, params_xml)
    # # print(stm.subarea_rainfall())
    # print(stm.baseflow_setting)

    # par_formatter = PARFormatter(runinfo_xml, params_xml)
    # print(par_formatter.routing_params_isa)

    # storm_formatter = STMFormatter(runinfo_xml, rain_netcdf, params_xml)
    # print(storm_formatter.stm_setting)
    # print(STMFormatter.stm_setting())
    # print(STMFormatter.pluvio_setting())


    # trans = TRANSFormatter(runinfo_xml, transfer_netcdf)
    # print(trans.num_data)
    # print(trans.timestep_hour)
    # print(trans.trans_timestep)
    # print(trans.trans_inst.trans.get('410571').Qtrans)

    # snow = SNOWFormatter(runinfo_xml, meteo_netcdf, state_xml)
    # print(snow.temp_timeseries)

    # Operation = OpFormatter(runinfo_xml, operation_netcdf)
    # print(Operation.num_data)
    # print(Operation.timestep_hour)
    # print(Operation.operation_timestep)
    # id = 410545
    # print(Operation.override_outflow(id))

    # hydrograph = HydrographFormatter(runinfo_xml, hydrograph_netcdf)
    # template_folder = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\model\templates\Template_Talbingo_with_Blowering.catg"
    # id = "410574"
    # gauge = "YarrangobillyRiverAtRavine"
    # print(hydrograph.find_print_num(gauge, template_folder))
    # print(hydrograph.recorded_hydrograph(id))
    # print(hydrograph.num_data)