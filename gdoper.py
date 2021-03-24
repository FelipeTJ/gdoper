###############################################################################
# Gdoper v1.0                                                                 #
#     a GDOP calculating, automatic batch processing program                  #
#
# File:  gdoper.py
# Author: Felipe Tampier Jara
# Date:   1 Mar 2021
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

from src import gdop_calculation as gc

# Create DroneData object and return required columns
def read_pos_file():
  pass

# Create Gdop object and return calculated GDOP for file
def calc_gdop():
  pass

def test():
  drone_data = '/test_data/test_data_full.csv'
  output = drone_data[:-4] + "-gdop.csv"

  gdop = gc.Gdop(drone_data, output)

  

if __name__ == '__main__':
  test()
  pass