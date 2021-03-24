###############################################################################
# Gdoper v1.0                                                                 #
#                                                                             #
# File:  reader_pos_data.py
# Author: Felipe Tampier Jara
# Date:   1 Mar 2021
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
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import d_print as p
import common as c

os.chdir('..')


class PosData():
  def __init__(self, filename):
    self.filename = filename
    self.var_count = 0
    self.row_count = 0
    self.data = self.order_data()
    p.Print('debug', 'Done setup\n')

  def order_data(self):
    ordered = {}
    titles = []
    data = []
    titles, data = self.read_csv()

    for i in range(self.row_count):
      for j in range(self.var_count):
        if titles[j] not in ordered.keys():
          ordered[titles[j]] = [data[i][j]]
        else:
          ordered[titles[j]].append(data[i][j])

    return ordered
 
  # TODO: Use Dataset 
  def read_csv(self) -> c.t.Tuple[c.t.List[str], list]:
    titles = []
    data = []

    fn = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + self.filename
    with open(fn, 'r') as file:  # TODO: Implement proper file locations
      reader = csv.reader(file)
      i = 0
      for row in reader:
        if i == 0:
          titles = row
        else:
          data.append(row)
        i += 1


    p.Print('info', f'name of file: {self.filename}')
    p.Print('info', f'amount of variables: {len(titles)}')
    p.Print('info', f'amount of data rows: {len(data)}')
    self.var_count = len(titles)
    self.row_count = len(data)

    return titles, data

  def get_col(self, col_name):
    if col_name in self.data.keys():
      return self.data[col_name]
    else:
      p.Print('error', f'No such column with name {col_name} found.')
      self.print_titles()

  def get_merged_cols(self, *cols) -> dict:
    if len(cols) == 1 and type(cols[0]) == tuple:
      cols = cols[0]
      
    p.Print('debug', f'Merging columns: {cols}')

    new_cols = {}
    for i in cols:
      if i not in self.data.keys():
        p.Print('error', f'Variable \'{i}\' does not exist in this file.')
        return
    
      new_cols[i] = self.get_col(i)
    return new_cols

  def print_titles(self):
    p.Print('info', 'Variable names:')
    for i in list(self.data.keys()):
      p.Print('info', f' - {i}')
    print()


def test_run():
  print(os.getcwd())
  print()

  d = PosData('/test_data/test_data.csv')
  d.print_titles()
  d.get_merged_cols('latitude', 'longitude', 'altitude_above_seaLevel(meters)', 'datetime(utc)', 'satellites')
  d.get_merged_cols(c.CHN_LON, c.CHN_LAT, c.CHN_ALT, c.CHN_UTC, c.CHN_SAT)
  d.get_merged_cols(c.CHN_DEFAULTS)
  #print(f'longitudes: {d.get_col("longitude")}')


def main():
  test_run()



if __name__ == "__main__":
  main()


# %%
