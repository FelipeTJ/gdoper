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
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from src.calc_manager import Calc_manager
from src.fov_models import FOV_view_match
from src.calcs import Calc_gdop


def test():

  drone_data = '/test_data_full.csv'

  gdoper = Calc_manager(drone_data, ts=5)  # ts is the sampling time from position data
  gdoper.set_FOV(FOV_view_match())
  gdoper.add_calc(Calc_gdop())
  gdoper.process_data()


if __name__ == '__main__':
  test()
  pass