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
import src.reader_pos_data as rps
import datetime as dt
from src.common import *

from src.calc_manager import Calc_manager
from src.fov_models import FOV_view_match
from src.calcs import Calc_gdop

# TODO: implement parsing
def parse_input() -> dict:
  sys.argv
  pass

# TODO: implement batch processing
def batch_process():
  pass

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


def plotting_test(in_file):
  drone_data = POS_DATA_FOLDER + os.sep + in_file[:-4] + '_gdoper.csv'
  
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

  fn = drone_data[:-11] + '_plot_path'

  plt.title('Path followed by drone', pad=2.0)
  plt.savefig(fn, format='pdf')
  plt.show()


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

  ax1.legend()
  ax1.set_xlim(-5,t[-1]+5)
  ax1.set_xlabel('Seconds')

  ax2.legend()
  ax2.set_xlim(-5,t[-1]+5)
  ax2.set_xlabel('Seconds')

  fn = drone_data[:-11] + '_plot_DOPS'

  plt.savefig(fn, format='pdf')
  plt.show()






if __name__ == '__main__':
  plotting_test('50m-curve.csv')

  pass