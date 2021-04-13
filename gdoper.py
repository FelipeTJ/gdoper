###############################################################################
# Gdoper v2.0                                                                 #
#     a GDOP calculating, automatic batch processing program                  #
#
# File:  gdoper.py
# Author: Felipe Tampier Jara
# Date:   5 Apr 2021
# Email:  felipe.tampierjara@tuni.fi
#
# Description:
# This program takes as input a folder in which drone positioning files can be
# found. Said files must contain column headers with the names 'latitude', 
# 'longitude', 'datetime(utc)', and an equivalent of '# of visible satellites'.
# The program will process the data in those columns and output the calculated
# GDOP based on satellite positioning data retreived from UNAVCO. 
#
# Required external packages:
# - georinex
# - unlzw3
# - pyproj
# - wget
#                                                                             #
###############################################################################

#%%
import os
import sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import matplotlib.pyplot as plt
import numpy as np
import time

import src.reader_pos_data as rps
import datetime as dt
from src.common import *

from src.calc_manager import Calc_manager
from src.fov_models import FOV_view_match
from src.calcs import Calc_gdop

SAMPLING = 5
SE = os.sep

# TODO: implement parsing
def parse_input() -> dict:
  sys.argv
  pass

def single_gdoper(in_file, in_dir, out_dir):
  gdoper = Calc_manager(in_file, data_folder=in_dir, out_folder=out_dir, ts=SAMPLING)
  gdoper.set_FOV(FOV_view_match())
  gdoper.add_calc(Calc_gdop())
  gdoper.process_data()

def batch_process(in_dir, out_dir, func):
  if not os.path.exists(in_dir):
      raise Exception(f'"{in_dir}" does not exist. Input full directory path')

  start = time.perf_counter()

  for file in os.listdir(in_dir):
    func(file, in_dir, out_dir)

  end = time.perf_counter()

  print(f'\nTotal processing time: {end-start:.2f}s')







def local_file_test(in_file):

  drone_data = in_file
  r_rile = '/home/felipe/Documents/TUNI_thesis/Gdoper/rinex_files/metg0570.21d.Z'

  gdoper = Calc_manager(drone_data, rinex_file=r_rile, ts=5)  # ts is the sampling time from position data
  gdoper.set_FOV(FOV_view_match())
  gdoper.add_calc(Calc_gdop())
  gdoper.process_data()

def default_test(in_file):
  drone_data = in_file

  gdoper = Calc_manager(drone_data, ts=5)  # ts is the sampling time from position data
  gdoper.set_FOV(FOV_view_match())
  gdoper.add_calc(Calc_gdop())
  gdoper.process_data()

def plotting_test(in_file, in_dir=POS_DATA_FOLDER, out_dir=POS_DATA_FOLDER):

  drone_data = in_dir + SE + in_file
  out_file = out_dir + SE + in_file[:-4]
  
  r = rps.Pos_data(drone_data)
  r.setup()

  data = r.get_merged_cols(CHN_LON, CHN_LAT, CHN_ALT, CHN_UTC, CHN_SAT, 'GDOP', 'HDOP', 'VDOP')


  """          Drone path plot            """

  lat = [float(i) for i in data[CHN_LAT]]
  lon = [float(i) for i in data[CHN_LON]]
  alt = [float(i) for i in data[CHN_ALT]]

  fig = plt.figure()
  ax = fig.add_subplot(projection='3d')

  ax.plot(lat, lon, alt, label='Drone path')

  ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1), frameon=True)

  ax.set_xlabel('Latitude', labelpad=1.0)
  ax.set_xticklabels([], fontsize='small')

  ax.set_ylabel('Longitude', labelpad=1.0)
  ax.set_yticklabels([], fontsize='small')

  ax.set_zlabel('Altitude')

  ax.view_init(elev=30, azim=-55)

  fn = out_file + '_plot_path'

  plt.title('Path followed by drone', pad=2.0)
  plt.savefig(fn, format='pdf')
  #plt.show()


  """        GDOP and sats plot           """

  g = [float(i) for i in data['GDOP']]
  v = [float(i) for i in data['VDOP']]
  h = [float(i) for i in data['HDOP']]
  s = [float(i) for i in data[CHN_SAT]]

  t0 = data[CHN_UTC][0]
  t0 = dt.datetime.fromisoformat(t0)
  t = [(dt.datetime.fromisoformat(i) - t0).seconds for i in data[CHN_UTC]]

  fig, (ax1,ax2) = plt.subplots(nrows=2, ncols=1, figsize=(9,8))

  fig.suptitle('Satellites in FOV and DOPs',y=0.92)

  ax1.plot(t, s, label='Satellites in view')
  ax2.plot(t, g, label='GDOP')
  ax2.plot(t, v, label='VDOP')
  ax2.plot(t, h, label='HDOP')

  ax1.legend(loc='best')
  ax1.set_xlim(-5,t[-1]+5)
  ax1.set_xlabel('Seconds')
  ax1.set_ylim(10,25)

  ax2.legend()
  ax2.set_xlim(-5,t[-1]+5)
  ax2.set_xlabel('Seconds')
  ax2.set_ylim(0.1,2)

  fn = out_file + '_plot_DOPS'

  plt.savefig(fn, format='pdf')
  #plt.show()

def sats2gdop_getter(in_file, in_dir, out_dir, d):

  drone_data = in_dir + SE + in_file
  
  r = rps.Pos_data(drone_data)
  r.setup()

  data = r.get_merged_cols(CHN_SAT, 'GDOP')#, 'HDOP', 'VDOP')

  for i in range(len(data['GDOP'])):

    n_vis_sats = data[CHN_SAT][i]
    if n_vis_sats not in d.keys():
      d[n_vis_sats] = [float(data['GDOP'][i])]
    else:
      d[n_vis_sats].append(float(data['GDOP'][i]))


def sats2gdop_ratio(in_dir, out_dir):
  """    Number of sats to GDOP ratio    """

  if not os.path.exists(in_dir):
      raise Exception(f'"{in_dir}" does not exist. Input full directory path')

  start = time.perf_counter()

  out_file = out_dir + SE + 'sats2gdop_ratio'

  vis_sats = {}

  for file in os.listdir(in_dir):
    sats2gdop_getter(file, in_dir, out_dir, vis_sats)

  x = sorted(list(vis_sats.keys()))
  its = [vis_sats[i] for i in x]
  y = [np.mean(i) for i in its]
  er = [np.var(i, ddof=1) for i in its]

  fig, ax = plt.subplots()

  ax.bar(x, y, yerr=er, capsize=3)
  ax.set_title('GDOP vs Number of visible satellites',pad=10.0)
  ax.set_ylabel('Mean GDOP value')
  ax.set_xlabel('Satellites in view')

  #plt.show()
  plt.savefig(out_file, format='pdf')
  
  end = time.perf_counter()
  print(f'\nTotal processing time: {end-start:.2f}s')
  pass



if __name__ == '__main__':
  #plotting_test('50m-curve.csv')
  #default_test('test_data_full.csv')

  f_in = BASE_FOLDER + SE + 'Tampere_flights'
  f_out = f_in + '_gdoper'

  #batch_process(f_in, f_out, single_gdoper)
  #batch_process(f_out, BASE_FOLDER + SE + 'Tampere_plots', plotting_test)
  sats2gdop_ratio(f_out, BASE_FOLDER + SE + 'Tampere_plots')

  pass