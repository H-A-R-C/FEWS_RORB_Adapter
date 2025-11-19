"""
This module is used to compile the input files from Delft-FEWS to a dataclass object.
Each class compiles a specific input file (xml or netCDF):
- RunInfo: compiles runinfo.xml file
- Params: compiles params.xml file
- State: compiles input_state.xml file
- Rain: compiles input_rain.nc file
- Meteo: compiles input_meteo.nc file
- Transfer: compiles input_transfer.nc file

The attribute of the dataclass is set as two-level nested dataclass:
- level 1: rorb-category (e.g. isa, bf, sub, etc.)
- level 2: sub-attribute (e.g. IL, CL, Kc, m, etc.)
from level 1, the dataclass is nested into dictionary with key as the category_ID
The list of category_ID is extracted from the rorb_config.json file at the start.

Dependencies:
- utils.py: contains the XMLReader and NetCDFReader classes
- rorb_config.json: contains the rorb model configuration settings
"""

from src.utils import *
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Any, Dict
import logging

# =============================================================================
# Compile input files to dataclass
# =============================================================================
class RORBConfig:
    def __init__(self):
        self.config = JsonReader("rorb_config.json")
        self.rorb_isa_list = self.config.extract("rorb_isa_list")
        self.rorb_bf_list = self.config.extract("rorb_bf_list")
        self.rorb_dam_list = self.config.extract("rorb_dam_list")
        self.rorb_snow_list = self.config.extract("rorb_snow_list")
        self.rorb_trans_list = self.config.extract("rorb_trans_list")
        self.rorb_meteo_list = self.config.extract("rorb_meteo_list")


# ----------------------------------------------------------------------------
# Compile RunInfo.xml
# ----------------------------------------------------------------------------
@dataclass
class RunInfo:
    """
    Class to compile runinfo.xml file to a dataclass RunInfoManager
    :param runinfo_xml: Path to the runinfo.xml file

    Example Usage:
    runinfo = RunInfo(runinfo_xml)
    runinfo.inputMeteoFile
    """
    runinfo_xml: str

    def __post_init__(self):
        self._compile_runinfo()

    def _compile_runinfo(self):
        xml = XMLReader(self.runinfo_xml)
        self.startDateTime = xml.extract_datetime_from_element('startDateTime')
        self.endDateTime = xml.extract_datetime_from_element('endDateTime')
        self.time0 = xml.extract_datetime_from_element('time0')
        self.inputParameterFile = xml.extract_element_text('inputParameterFile')
        self.inputRainFile = xml.extract_element_text("inputNetcdfFile", index=0)
        self.inputMeteoFile = xml.extract_element_text("inputNetcdfFile", index=1)
        self.inputStateFile = xml.extract_element_text('inputTimeSeriesFile', index=2)
        self.inputTransferFile = xml.extract_element_text("inputNetcdfFile", index=3)
        self.inputOperationFile = xml.extract_element_text("inputNetcdfFile", index=4)
        self.inputHydrographFile = xml.extract_element_text("inputNetcdfFile", index=5)
        self.outputGaugeFlow = xml.extract_element_text('outputTimeSeriesFile', index=0)
        self.outputReservoirOperation = xml.extract_element_text('outputTimeSeriesFile', index=1)
        self.outputRainfallExcess = xml.extract_element_text('outputTimeSeriesFile', index=2)
        self.model_folder = xml.extract_properties_value_from_key("model_folder")
        self.tororb_folder = xml.extract_properties_value_from_key("tororb_folder")
        self.fromrorb_folder = xml.extract_properties_value_from_key("fromrorb_folder")
        self.rorb_folder = xml.extract_properties_value_from_key("rorb_folder")
        self.rorb_exe = xml.extract_properties_value_from_key("rorb_exe")

# ----------------------------------------------------------------------------
# Compile Params.xml
# ----------------------------------------------------------------------------
@dataclass
class ISAGroupSubManager:
    IL: Optional[float] = None
    CL: Optional[float] = None
    Kc: Optional[float] = None
    m: Optional[float] = None

@dataclass
class BaseflowSubManager:
    const: Optional[float] = None
    multi: Optional[float] = None
    start: Optional[float] = None

@dataclass
class GateOpsSubManager:
    procedure: Optional[int] = None

@dataclass
class Params(RORBConfig):
    """
    Class to compile params.xml file to a dataclass ParamsManager
    :param params_xml: Path to the params.xml file
    
    Example Usage:
    params = Params(params_xml)
    params.isa["1"].IL
    params.num_burst
    """
    params_xml: str

    def __post_init__(self):
        RORBConfig.__init__(self) 
        self.isa = self._compile_isa_groups()
        self.bf = self._compile_baseflow()
        self.gateops = self._compile_gateops()
        self._compile_settings()

    def _compile_settings(self):
        xml = XMLReader(self.params_xml)
        self.snow_setting = xml.extract_rorb_parameter_value('snow module and bursts', 'rorbSnow', 'stringValue')
        self.num_burst = int(xml.extract_rorb_parameter_value('snow module and bursts', 'rorbBursts', 'stringValue'))
        self.num_isa = int((len(self.rorb_isa_list))+1)

    def _compile_isa_groups(self) -> Dict[str, ISAGroupSubManager]:
        isa_dict = {}
        xml = XMLReader(self.params_xml)
        for i in self.rorb_isa_list:
            key = f"{i}"  
            isa = ISAGroupSubManager(
                IL=float(xml.extract_rorb_parameter_value_with_conditions('Loss parameters', 'rorb.isaId', f"{i}", 'rorbIL1', 'dblValue')),
                CL=float(xml.extract_rorb_parameter_value_with_conditions('Loss parameters', 'rorb.isaId', f"{i}", 'rorbCL1', 'dblValue')),
                Kc=float(xml.extract_rorb_parameter_value_with_conditions('Routing parameters', 'rorb.isaId', f"{i}", 'rorbKc', 'dblValue')),
                m=float(xml.extract_rorb_parameter_value_with_conditions('Routing parameters', 'rorb.isaId', f"{i}", 'rorbM', 'dblValue'))
            )
            isa_dict[key] = isa
        return isa_dict
    
    def _compile_baseflow(self) -> Dict[str, BaseflowSubManager]:
        bf_dict = {}
        xml = XMLReader(self.params_xml)
        for i in self.rorb_bf_list:
            bf_dict[f"{i}"] = BaseflowSubManager(
                const=xml.extract_rorb_parameter_value_with_conditions('Baseflow parameters', 'rorbId', f"{i}", 'rorbBF', 'dblValue'),
                multi=xml.extract_rorb_parameter_value_with_conditions('Baseflow parameters', 'rorbId', f"{i}", 'rorbBmult', 'dblValue'),
                start=xml.extract_rorb_parameter_value_with_conditions('Baseflow parameters', 'rorbId', f"{i}", 'rorbBFstart', 'intValue'),
            )
        return bf_dict    

    def _compile_gateops(self) -> Dict[str, GateOpsSubManager]:
        go_dict = {}
        xml = XMLReader(self.params_xml)
        for i in self.rorb_dam_list:
            go_dict[f"{i}"] = GateOpsSubManager(
                procedure=xml.extract_rorb_parameter_value_with_conditions('Gate parameters', 'rorbId', f"{i}", 'rorbGate', 'intValue'),
            )
        return go_dict    

# ----------------------------------------------------------------------------
# Compile State.xml
# ----------------------------------------------------------------------------
@dataclass
class DamSubManager:
    level: Optional[float] = None
@dataclass
class SnowSubManager:
    SD: Optional[float] = None
    WD: Optional[float] = None
@dataclass
class State(RORBConfig):
    """
    Class to compile input_state.xml file to a dataclass StateManager
    :param state_xml: Path to the input_state.xml file
    
    Example Usage:
    state = State(state_xml)
    state.dam["410571"].level
    state.snow["DeepCreek"].SD 
    """
    state_xml: str

    def __post_init__(self):
        RORBConfig.__init__(self) 
        self.dam = self._compile_dam()
        self.snow = self._compile_snow()

    def _compile_dam(self) -> Dict[str, DamSubManager]:
        dam_dict = {}
        xml = XMLReader(self.state_xml)
        for i in self.rorb_dam_list:
            dam_dict[f"{i}"] = DamSubManager(
                level=xml.extract_event_state_variable(i, 'H_observed')
            )
        return dam_dict  
    
    def _compile_snow(self) -> Dict[str, SnowSubManager]:
        snow_dict = {}
        xml = XMLReader(self.state_xml)
        for i in self.rorb_snow_list:
            snow_dict[f"{i}"] = SnowSubManager(
                SD=xml.extract_event_state_variable(f'{i}SnowCourse', 'SD_observed', missVal_fill=None),
                WD=xml.extract_event_state_variable(f'{i}SnowCourse', 'WC_observed', missVal_fill=None)
            )
        return snow_dict  


# ----------------------------------------------------------------------------
# Compile Rain.nc
# ----------------------------------------------------------------------------
@dataclass
class Rain(RORBConfig):
    """
    Class to compile input_rain.nc file to a dictionary of rain data
    :param rain_netcdf: Path to the input_rain.nc file

    Example Usage:
    rain = Rain(rain_netcdf)
    rain.sub['CR']
    """
    rain_netcdf: str

    def __post_init__(self):
        RORBConfig.__init__(self) 
        self.sub = self._compile_rain()

    def _compile_rain(self) -> Dict[str, List[float]]:
        netcdf = NetCDFReader(self.rain_netcdf)
        station_extracted_lst = netcdf.extract_variable_list('station_id')
        station_lst = DataUtilities.decode_big_byte_list_to_string_list(station_extracted_lst)

        P_extracted_lst = netcdf.extract_variable_list('P', missVal_attribute='_FillValue', missVal_fill=0)
        P_lst = DataUtilities.flatten_and_transpose(P_extracted_lst)

        rain_dict = {}
        for i, station in enumerate(station_lst):
            rain_dict[f"{station}"] = P_lst[i]
        
        return rain_dict


# ----------------------------------------------------------------------------
# Compile Transfer.nc
# ----------------------------------------------------------------------------
@dataclass
class TransferManager:
    Qtrans: Optional[List[float]] = None
    Qgen: Optional[List[float]] = None

@dataclass
class Transfer(RORBConfig):
    """
    Class to compile input_transfer.nc file to a dictionary of transfer data
    :param transfer_netcdf: Path to the input_transfer.nc file

    Example Usage:
    transfer = Transfer(transfer_netcdf)
    transfer.trans['410571'].Qtrans
    """
    transfer_netcdf: str

    def __post_init__(self):
        RORBConfig.__init__(self) 
        self.trans = self._compile_trans()

    def _compile_trans(self) -> Dict[str, TransferManager]:
        netcdf = NetCDFReader(self.transfer_netcdf)

        trans_dict = {}
        for i in self.rorb_trans_list:
            trans_dict[f"{i}"] = TransferManager(
                Qtrans=netcdf.extract_variable_value_with_conditions('station_id', f"{i}", 'Qtrans_forecast', missVal_attribute='_FillValue'),
                Qgen=netcdf.extract_variable_value_with_conditions('station_id', f"{i}", 'Qgen_forecast', missVal_attribute='_FillValue')
                # Qoutlet=netcdf.extract_variable_value_with_conditions('station_id', f"{i}", 'Qoutlet_forecast', missVal_attribute='_FillValue')
            )
        return trans_dict  


# ----------------------------------------------------------------------------
# Compile Meteo.nc
# ----------------------------------------------------------------------------
@dataclass
class MeteoManager:
    T: Optional[List[float]] = None
    W: Optional[List[float]] = None

@dataclass
class Meteo(RORBConfig):
    """
    Class to compile input_meteo.nc file to a dictionary of meteo data
    :param meteo_netcdf: Path to the input_meteo.nc file

    Example Usage:
    meteo = Meteo(meteo_netcdf)
    meteo.snow["14].T
    """
    meteo_netcdf: str

    def __init__(self, meteo_netcdf: str):
        RORBConfig.__init__(self) 
        self.meteo_netcdf = meteo_netcdf   
        self.snow = self._compile_meteo()

    def _compile_meteo(self) -> Dict[str, MeteoManager]:
        netcdf = NetCDFReader(self.meteo_netcdf)
        station_extracted_lst = netcdf.extract_variable_list('station_id')
        station_lst = DataUtilities.decode_big_byte_list_to_string_list(station_extracted_lst)
        
        meteo_dict = {}
        for i in station_lst:
            if i in self.rorb_meteo_list:
                temp_extracted = netcdf.extract_variable_list('T_observed', missVal_attribute='_FillValue', missVal_fill=0)
                wind_extracted = netcdf.extract_variable_list('W_observed', missVal_attribute='_FillValue', missVal_fill=0)

                meteo_dict[f"{i}"] = MeteoManager(
                    T=DataUtilities.flatten(temp_extracted),
                    W=DataUtilities.flatten(wind_extracted)
                )

        return meteo_dict


# ----------------------------------------------------------------------------
# Compile Operation.nc
# ----------------------------------------------------------------------------
@dataclass
class OperationManager:
    outflow: Optional[List[float]] = None
    opening: Optional[List[float]] = None

@dataclass
class Operation(RORBConfig):
    """
    Class to compile operation.nc file to a dictionary of operation data
    :param operation_netcdf: Path to the operation.nc file

    Example Usage:
    operation = Operation(operation_netcdf)
    operation.dam['410571'].Outflow
    """
    operation_netcdf: str

    def __post_init__(self):
        RORBConfig.__init__(self) 
        self.dam = self._compile_operation()

    def _compile_operation(self) -> Dict[str, OperationManager]:
        netcdf = NetCDFReader(self.operation_netcdf)
        station_extracted_lst = netcdf.extract_variable_list('station_id')

        operation_dict = {}
        for i in station_extracted_lst:
            operation_dict[f"{i}"] = OperationManager(
                outflow=netcdf.extract_variable_value_with_conditions('station_id', i, 'Outflow', missVal_attribute='_FillValue'),
                opening=netcdf.extract_variable_value_with_conditions('station_id', i, 'GateOpening', missVal_attribute='_FillValue')
            )
        return operation_dict  
    
if __name__ == '__main__':
    # runinfo_xml = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\runinfo.xml"
    # runinfo = RunInfo(runinfo_xml)
    # print(runinfo.inputStateFile)
    # print(runinfo.inputMeteoFile)

    params_xml = r"C:\RORB_FEWS_Adapter\examples\to_rorb\params.xml"
    params = Params(params_xml)
    print(params.gateops["410542"].procedure)

    operation_nc = r"C:\RORB_FEWS_Adapter\examples\to_rorb\input_operation.nc"
    operation = Operation(operation_nc)
    for key, value in operation.dam.items():
        print(f"{key}")

    # state_xml = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\input_state.xml"
    # state = State(state_xml)
    # print(state.dam["410571"].level)
    # print(state.snow["DeepCreek"].SD)

    # rain_netcdf = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\input_rain.nc"
    # rain = Rain(rain_netcdf)
    # print(rain.sub['CR'])

    # transfer_netcdf = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\input_transfer.nc"
    # transfer = Transfer(transfer_netcdf)
    # print(transfer.trans['410571'].Qtrans)

    # meteo_netcdf = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\input_meteo.nc"
    # meteo = Meteo(meteo_netcdf)
    # print(meteo.snow['14'].T)

    # hydrograph_netcdf = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\input_hydrograph.nc"
    # hydrograph = Hydrograph(hydrograph_netcdf)
    # print(hydrograph.gauge['410542'])

    # operation_netcdf = r"T:\Zijian\RORB_FEWS_Adaptor\RORB-FEWS-adapter\examples\Updated_RORB_28_Nov_24\to_rorb\input_operation.nc"
    # operation = Operation(operation_netcdf)
    # print(operation.dam['410545'].Outflow)


 