###############################################################################
# Gdoper v3.0                                                                 #
#                                                                             #
# File:  calc_manager.py
# Author: Felipe Tampier Jara
# Date:   5 Apr 2021
# Email:  felipe.tampierjara@tuni.fi
# TODO: update description
# Description:***
# Gets positioning data using reader_pos_data.py and for every row of data,
# uses reader_rinex.py to aquire satellite data and calculates the GDOP +
# other data. Outputs processed data + corresponding original data to csv.
#                                                                             #
############################################################################### 


# %%
from dataclasses import dataclass
from typing import Tuple, Dict, Mapping, List, Set
from xarray import DataArray
from csv import writer
import datetime as dt
import time
import os


import src.common as cm
import src.reader_rinex as rr
from src.reader_rinex import ReaderRinex, RinexOptions
from src.reader_pos_data import ReaderPos
from src.fov_models import FOV_model, FOV_view_match
from src.calcs import Calc, Calc_gdop
from src.d_print import Stats, Debug, Info, Enable_Debug

@dataclass
class ManagerOptions:
  file_iname:     str = None  # Input file name must be left empty by user
  file_oname:     str = ''    # Output filename can be set freely
  folder_input:   str = cm.POS_DATA_FOLDER
  folder_output:  str = folder_input
  sample_period:  int = 5


class CalcManager:
  def __init__(self,
               in_file:str,
               m_opts:ManagerOptions = ManagerOptions(), 
               r_opts:RinexOptions = RinexOptions(),
               debug = -1
               ):

    if m_opts.file_iname != None:
      raise Exception('\'file_input\' property in ManagerOptions should not be modified.')

    if r_opts.cstls != None:
      raise Exception('\'cstls\' property in RinexOptions should not be modified.')

    if r_opts.station_params.date_measured != None:
      r_opts.station_params.date_measured = None
      raise Exception('\'date_measured\' property in StationOptions should not be modified.')

    # CalcManager options
    self.opts = m_opts
    self.opts.file_iname = in_file
    if m_opts.file_oname == '':
      self.opts.file_oname = in_file.split('.csv')[0] + '_gdoper.csv'

    # Objects
    self.pos_obj = ReaderPos(self.opts.folder_input + os.sep +  self.opts.file_iname)
    self.rin_obj = ReaderRinex(r_opts=r_opts)
    
    # Processing data
    self.req_vars = set()               # The variables required by FOV_model and Calc
    self.cstls: Set[cm.CSTL] = set()    # Set of constellations as required by FOV models 
    self.proc_q: List[FOV_model] = []   # The processing queue 

    # Processed data
    self.rinex_sats:  Dict[str, Dict[str, Tuple[float,float,float]]] = {}
    self.sampled_pos: Dict[str, list] = {}
    self.output_map:  Dict[str, list] = {}
    self.ordered_keys:  List[str]     = []

    # Debug level for this class
    self.__debug = int(debug)

    self.is_setup = False

  def add_FOV(self, fov: FOV_model):
    """
      Add an FOV object to the processing queue
    """
    if fov not in self.proc_q:
      self.proc_q.append(fov)
    else:
      Info(f'FOV object has already been added to the processing queue')


  def __reset(self) -> None:
    """
      Reset the local variables so new computations can be made
    """
    self.output_map.clear()
    self.ordered_keys.clear()
    self.req_vars.clear()
    self.is_setup = False


  def __is_setup(self) -> bool:
    
    if not self.pos_obj.is_setup:
      return False

    for i in self.proc_q:
      if not i.is_setup:
        return False
  
    return True


  def __do_setup(self, force=False) -> None:
    """
      Perform checks and do setups before starting to process data
    """

    if len(self.proc_q) == 0:
      raise Exception("No calculations have been queued.\
                      Use the 'add_calc()' method to do so.")

    for i in self.proc_q:

      if i == FOV_model():
            raise Exception("FOV_model cannot be used as an FOV model.\
                            Select an inherited model.")
                
      if not i.is_setup:
        raise Exception(f"FOV_model '{i.__str__()}' has not been setup.")

      self.req_vars = self.req_vars.union(i.required_vars())
      self.cstls = self.cstls.union(set(i.cstls))

    if force:
      self.pos_obj.setup()
      self.rin_obj.setup(self.pos_obj.get_first_utc(), list(self.cstls))
    else:
      if not self.pos_obj.is_setup:
        self.pos_obj.setup()
        self.rin_obj.setup(self.pos_obj.get_first_utc(), list(self.cstls))
    
    self.is_setup = True


  def __sample_pos(self) -> Dict[str, list]:
    """
      Get the position data from file and return a sampled version
    """
    # Get pos data
    all_pos = self.pos_obj.get_merged_cols(list(self.req_vars))
    all_pos_row_count = self.pos_obj.row_count
    chn_keys = list(all_pos.keys())
    sampled = {}

    # Setup empty lists for each CHN
    for i in chn_keys:
      sampled[i] = []

    # Sample
    dif = dt.timedelta(seconds=self.opts.sample_period)
    last_saved =  dt.datetime.fromisoformat(self.pos_obj.get_first_utc()) - dif

    for i in range(all_pos_row_count):
      t = dt.datetime.fromisoformat(all_pos[cm.CHN_UTC][i])  # TODO: use proper name for utc AND proper datetime conversion

      if t-last_saved >= dif:

        # Add samples from this index
        for chn in chn_keys:
          # Do not sample invalid values
          if chn == cm.CHN_LAT and all_pos[chn][i] == '0': continue
          if chn == cm.CHN_LON and all_pos[chn][i] == '0': continue

          sampled[chn].append(all_pos[chn][i])
        
        last_saved = last_saved + dif

    self.sampled_pos = sampled
    return self.sampled_pos 


  def __acquire_sats(self) -> Dict[str, Dict[str, Tuple[float,float,float]]]:
    """
      Return all satellites for all pos in time
    """
    self.rinex_sats = self.rin_obj.get_sats_pos(self.sampled_pos[cm.CHN_UTC])
    return self.rinex_sats
      

  def __do_calcs(self) -> None:
    """
      Return dict with keys as calculation names, and values
      as lists of datapoints. 
    """
    if len(self.proc_q) == 0:
      raise Exception("No calculations were queued")

    for p in self.proc_q:
      p.get_sats(self.sampled_pos, self.rinex_sats)
      self.__add_dict_to_output_map(p.do_calcs(self.sampled_pos))
  

  def __add_dict_to_output_map(self, data: dict):
    """
      Add a title to the data and store in the output mapping.
    """
    self.ordered_keys.extend(data.keys())
    self.output_map.update(data)


  def __add_to_output_map(self, chn: str, data: list):
    """
      Add a title to the data and store in the output mapping.
    """
    self.ordered_keys.append(chn)
    self.output_map[chn] = data


  def __output_to_file(self):
    """
      Writes all data in self.output_map to a file in csv format.\n
      File name is "self.out_dir + self.output_file"
    """
    if not os.path.exists(self.opts.folder_output):
      os.mkdir(self.opts.folder_output)

    fn = self.opts.folder_output + os.sep + self.opts.file_oname
    map_keys = self.ordered_keys
    row_count = len(self.output_map[map_keys[0]])

    with open(fn, 'w') as csvfile:
      wr = writer(csvfile)
      wr.writerow(map_keys)

      for row in range(row_count):
        temp = []
        for col in map_keys:
          temp.append(self.output_map[col][row])

        wr.writerow(temp) 


  def print_dirs(self):
    Info(f'Calc_manager properties:')
    Info(f'- sample period:\t{self.opts.sample_period}s')
    Info(f'- Constellation:\t{[i.__str__() for i in self.cstls]}')
    Info(f'- Processing Q :\t{[i.__str__() for i in self.proc_q]}')
    Info(f'- input file   :\t{self.opts.file_iname}')
    Debug(0,f'- input dir    :\t{self.opts.folder_input}')
    Info(f'- output file  :\t{self.opts.file_oname}\n')
    Debug(0,f'- output dir   :\t{self.opts.folder_output}')


  def process_data(self):
    """
      Acquire relevant data, process, and output into csv format
    """
    Enable_Debug(self.__debug)
    self.__reset()

    tot = time.perf_counter()
    now = time.perf_counter()

    if not self.__is_setup():
      Debug(1, f'Setting up...')
      self.__do_setup()
      Enable_Debug(self.__debug)
      Debug(1, f'Done. {time.perf_counter()-now:.3f}s\n')

    self.print_dirs()

    now = time.perf_counter()
    Debug(1, f'Sampling positions...')
    pos = self.__sample_pos()
    Enable_Debug(self.__debug)
    Debug(1, f'Done. {time.perf_counter()-now:.3f}s\n')

    # Add data used for calculation to output file's chns
    for k in list(pos.keys()):
      if (k in self.req_vars) and (k not in self.ordered_keys):
        self.__add_to_output_map(k, pos[k])

    now = time.perf_counter()
    Debug(1, f'Aquiring satellite info...')
    self.__acquire_sats()
    Enable_Debug(self.__debug)
    Debug(1, f'Done. {time.perf_counter()-now:.3f}s\n')

    now = time.perf_counter()
    Debug(1, f'Performing calculations...')
    self.__do_calcs()
    Enable_Debug(self.__debug)
    Debug(1, f'Done. {time.perf_counter()-now:.3f}s\n')

    now = time.perf_counter()
    Debug(1, f'Writing to file...')
    self.__output_to_file()
    Enable_Debug(self.__debug)
    Debug(1, f'Done. {time.perf_counter()-now:.3f}s\n')

    Info(f'Done running')
    Stats(0,f'Duration: {time.perf_counter() - tot:.3f}'
          + f' for {len(self.output_map[self.ordered_keys[0]])} output rows\n')




def test():
  drone_data = '/test_data_full.csv'
  #output = '/test_data/test_data-gdop.csv'

  gdoper = CalcManager(drone_data)

  fov = FOV_view_match([cm.CSTL.GPS, cm.CSTL.GAL])
  fov.add_calc(Calc_gdop(cm.CSTL.GPS))

  gdoper.add_FOV(fov)
  gdoper.process_data()

if __name__ == '__main__':
  test()
  print('Done running')
  pass


