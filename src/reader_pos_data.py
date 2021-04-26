###############################################################################
# Gdoper v1.2                                                                 #
#                                                                             #
# File:  reader_pos_data.py
# Author: Felipe Tampier Jara
# Date:   5 Apr 2021
# Email:  felipe.tampierjara@tuni.fi
#
# Description:
# Reads csv data from a file that has positional data. Methods can be used to
# return this data properly formatted for further processing.
#                                                                             #
###############################################################################


# %%
import os
import csv
import xarray as xr
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from src.d_print import Debug,Info
import src.common as cm

os.chdir('..')  # gdoper.py directory


class Pos_data():
  def __init__(self, filename):
    self.filename = filename
    self.var_count = 0
    self.row_count = 0
    self.data = {}
    self.done_setup = False
    self.debuging = 'none'


  # TODO: Create setup function
  def setup(self):
    if not os.path.exists(self.filename):
      raise Exception(f'"{self.filename}" does not exist. Input full dir.')
    
    self.done_setup = True
    self.data = self.get_ordered_data()

    #Debug('Done setup\n')

  def setup_check(self):
    if not self.done_setup: 
      raise Exception('Pos_data has not been set up.')


  def get_ordered_data(self) -> dict:
    self.setup_check()

    ordered = {}
    titles = []
    data = []
    titles, data = self.read_csv()

    # Convert the rows of all data into columns with header names (transpose)
    for i in range(self.row_count):
      for j in range(self.var_count):
        chn = titles[j].strip()
        if chn not in ordered.keys():
          ordered[chn] = [data[i][j]]
        else:
          ordered[chn].append(data[i][j])

    return ordered
 

  def read_csv(self) -> cm.t.Tuple[cm.t.List[str], list]:
    self.setup_check()

    titles = []
    data = []

    fn = self.filename
    with open(fn, 'r') as file:  # TODO: Implement proper file locations
      reader = csv.reader(file)
      i = 0
      for row in reader:
        if i == 0:
          titles = row
        else:
          data.append(row)
        i += 1

    #Debug(1,f'name of file: {self.filename}')
    #Debug(1,f'amount of variables: {len(titles)}')
    #Debug(1,f'amount of data rows: {len(data)}')
    self.var_count = len(titles)
    self.row_count = len(data)

    return titles, data


  def get_col(self, col_name):
    self.setup_check()

    if col_name in self.data.keys():
      return self.data[col_name]
    else:
      raise Exception(f'No column with name {col_name} found.')
      self.print_titles()


  def get_merged_cols(self, *cols) -> dict:
    self.setup_check()

    if len(cols) == 1 and (type(cols[0]) == tuple or type(cols[0]) == list):
      cols = cols[0]
      
    Debug(2,f'Merging columns: {cols}')
    new_cols = {}
    for i in cols:
      if i not in self.data.keys():
        raise Exception(f'Variable \'{i}\' does not exist in this file.{self.filename}')
        return
    
      new_cols[i] = self.get_col(i)

    Debug(3,f'new_cols: {new_cols}')
    return new_cols


  def get_first_utc(self) -> str:
    """
      Returns the first available date in the data
    """
    self.setup_check()

    # TODO: make the column names more flexible
    return self.get_col(cm.CHN_UTC)[0]


  def print_titles(self):
    self.setup_check()

    Info('Variable names:')
    for i in list(self.data.keys()):
      Info(f' - {i}')
    print()


def test_run():
  print('Current dir:',os.getcwd())
  print()

  test_file = cm.POS_DATA_FOLDER + os.sep + 'test_data.csv'

  d = Pos_data(test_file)
  d.setup()
  d.print_titles()
  d.get_merged_cols('latitude', 'longitude', 'altitude_above_seaLevel(meters)', 'datetime(utc)', 'satellites')
  d.get_merged_cols(cm.CHN_LON, cm.CHN_LAT, cm.CHN_ALT, cm.CHN_UTC, cm.CHN_SAT)
  d.get_merged_cols(cm.CHN_DEFAULTS)
  #print(f'longitudes: {d.get_col("longitude")}')


def main():
  test_run()



if __name__ == "__main__":
  main()


# %%
