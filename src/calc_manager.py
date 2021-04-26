###############################################################################
# Gdoper v2.0                                                                 #
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
from typing import Dict, Mapping, List
from xarray import DataArray
from csv import writer
import datetime as dt
import time
import os


import src.common as cm
import src.reader_rinex as rr
import src.reader_pos_data as rpc
from src.fov_models import FOV_model, FOV_view_match
from src.calcs import Calc, Calc_gdop
from src.d_print import Stats, Debug, Info, Set_PrintLevel




class Calc_manager:
  def __init__(self, in_file,
              out_file = '',
              rinex_file = '',
              rinex_folder = cm.RINEX_FOLDER,
              data_folder = cm.POS_DATA_FOLDER,
              out_folder = cm.POS_DATA_FOLDER,
              ts = 5,
              debug = -1):

    # Sampling period
    self.Ts = dt.timedelta(seconds=ts)

    # Directories
    self.rinex_dir: str = rinex_folder
    self.pdata_dir: str = data_folder
    self.out_dir: str = out_folder

    # File names
    self.input_file: str = in_file
    self.output_file: str = (in_file[:-4] + '_gdoper.csv' if out_file == '' else out_file)

    # Objects
    self.pos_obj = rpc.Pos_data(self.pdata_dir + os.sep +  self.input_file)
    self.sat_obj = rr.Orbital_data(local_data=rinex_file)
    self.fov_obj = FOV_model()      # real obj created in setup_FOV()
    self.calcs_q: List[Calc] = []   # A queue for calculations
    self.req_vars = set()           # The variables required by FOV_model and Calc

    # Processed data
    self.output_map: Dict[str, list] = {}
    self.ordered_keys: List[str]        = []

    # Debug level for this class
    self.__debug = int(debug)
  

  def set_FOV(self, model: FOV_model) -> None:
    """
      Input the instance of an FOVmodel to be used in the calculations
    """
    self.fov_obj = model


  def add_calc(self, calc: Calc) -> None:
    """
      Add a Calc object to the queue to perform calculations on the data
    """
    if calc in self.calcs_q:
      return
    else:
      self.calcs_q.append(calc)

  def __reset(self) -> None:
    """
      Reset the local variables so new computations can be made
    """
    self.output_map.clear()
    self.ordered_keys.clear()
    self.req_vars.clear()


  def __setup(self) -> None:
    """
      Perform checks and do setups before starting to process data
    """
    if self.fov_obj == FOV_model():
      raise Exception("FOV_model is the base class, it cannot be used.\
                      Select an inherited model.")

    if not self.fov_obj.is_setup:
      raise Exception("FOV_model has not been setup.")
    
    if len(self.calcs_q) == 0:
      raise Exception("No calculations have been queued.\
                      Use the 'add_calc()' method to do so.")

    for i in self.calcs_q:
      if i == Calc():
        raise Exception("Calc cannot be used as a calculation.\
                        Select an inherited class.")
      else:
        self.req_vars.union(set(i.required_vars()))

    self.req_vars = self.req_vars.union(set(self.fov_obj.required_vars()))

    # Have readers check for existance of their files and folders
    self.pos_obj.setup()
    self.sat_obj.setup(self.pos_obj.get_first_utc())


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
    dif = dt.timedelta(seconds=self.Ts.seconds)
    last_saved =  dt.datetime.fromisoformat(self.pos_obj.get_first_utc()) - dif

    for i in range(all_pos_row_count):
      t = dt.datetime.fromisoformat(all_pos[cm.CHN_UTC][i])  # TODO: use proper name for utc

      if t-last_saved >= dif:

        # Add samples from this index
        for chn in chn_keys:
          # Do not sample invalid values
          if chn == cm.CHN_LAT and all_pos[chn][i] == '0': continue
          if chn == cm.CHN_LON and all_pos[chn][i] == '0': continue

          sampled[chn].append(all_pos[chn][i])
        
        last_saved = last_saved + dif

    return sampled  


  def __acquire_sats(self, pos_timestamps) -> Dict[str, DataArray]:
    """
      Return all satellites for all pos in time
    """
    return self.sat_obj.get_sats_pos(pos_timestamps)
    

  def __sats_in_fov(self, pos_pos, sats_pos):
    """
      Return all satellites in view from pos_pos, given sats_pos and FOV_model
    """
    return self.fov_obj.get_sats(pos_pos, sats_pos)
    

  def __do_calcs(self, pos_pos, sats_LOS_pos): # Positions in ECEF
    """
      Return dict with keys as calculation names, and values
      as lists of datapoints.\n
      The datapoints are in the same line as the values used
      for the calculation. 
    """
    if len(self.calcs_q) == 0:
      raise Exception("No calculations were queued")

    for calc in self.calcs_q:
      self.__add_dict_to_output_map(calc.do_calc(pos_pos, sats_LOS_pos))
  

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

    fn = self.out_dir + os.sep + self.output_file
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
    Info(f'Calc_manager setup:')
    Info(f'- sample time:\t{self.Ts}s')
    gd_p = self.pdata_dir.find("Gdoper")
    if gd_p != -1:
      Info(f'- input file:\t{self.pdata_dir[gd_p-1:] + os.sep + self.input_file}')
    else:

      Info(f'- input file:\t{self.pdata_dir + os.sep + self.input_file}')

    gd_po = self.out_dir.find("Gdoper")
    if gd_po != -1:
      Info(f'- output file:\t{self.out_dir[gd_po-1:] + os.sep + self.output_file}\n')
    else:
      Info(f'- output file:\t{self.out_dir + os.sep + self.output_file}\n')




  def process_data(self):
    """
      Acquire relevant data, process, and output into csv format
    """
    Set_PrintLevel(self.__debug)
    self.print_dirs()
    self.__reset()

    tot = time.perf_counter()
    now = time.perf_counter()
    Debug(1, f'Setting up...')
    self.__setup()
    Debug(1, f'Done. {time.perf_counter()-now:.3f}s\n')

    now = time.perf_counter()
    Debug(1, f'Sampling positions...')
    pos = self.__sample_pos()
    Debug(1, f'Done. {time.perf_counter()-now:.3f}s\n')

    # Add data used for calculation to output file
    for k in list(pos.keys()):
      if (k in self.req_vars) and (k not in self.ordered_keys):
        self.__add_to_output_map(k, pos[k])

    now = time.perf_counter()
    Debug(1, f'Aquiring satellite info...')
    all_sats = self.__acquire_sats(pos[cm.CHN_UTC]) # TODO: make CHNs more flexible
    Debug(1, f'Done. {time.perf_counter()-now:.3f}s\n')

    now = time.perf_counter()
    Debug(1, f'Calculating visible satellites...')
    los_sats = self.__sats_in_fov(pos, all_sats)
    Debug(1, f'Done. {time.perf_counter()-now:.3f}s\n')

    now = time.perf_counter()
    Debug(1, f'Performing calculations...')
    self.__do_calcs(pos, los_sats)
    Debug(1, f'Done. {time.perf_counter()-now:.3f}s\n')

    now = time.perf_counter()
    Debug(1, f'Writing to file...')
    self.__output_to_file()
    Debug(1, f'Done. {time.perf_counter()-now:.3f}s\n')

    Stats(0,f'Total runtime: {time.perf_counter() - tot:.3f}'
          + f' for {len(self.output_map[self.ordered_keys[0]])} output rows\n')




def test():
  drone_data = '/test_data_full.csv'
  #output = '/test_data/test_data-gdop.csv'

  gdoper = Calc_manager(drone_data, ts=10)
  gdoper.set_FOV(FOV_view_match())
  gdoper.add_calc(Calc_gdop())
  gdoper.process_data()

if __name__ == '__main__':
  test()
  print('Done running')
  pass


