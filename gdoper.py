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

from numpy.core.numeric import Inf

os.chdir(os.path.dirname(os.path.abspath(__file__)))
from src.processing import *
from src.common import BASE_FOLDER  
# BASE_FOLDER is the directory where this file (gdoper.py) resides




if __name__ == '__main__':
  parse_input()

  #fov_test('50m-curve.csv',15,5)
  #fov_test('test_data.csv',15)
  #plotting_test('fov_test_gdoper_15.csv',sat_name='sats')

  # Input and output directories for Gdoper processing
  input_dir = BASE_FOLDER + os.sep + 'Tampere_flights'
  output_dir = input_dir + '_gdoper'

  # Process all files in 'input_dir' with Gdoper
  #batch_process(input_dir, output_dir, single_gdoper, skip_existing=True)

  # Output directory for plots
  output_plots_dir = input_dir + '_plots'

  # Plot data for all files in 'output_dir' and output plots to 'output_plots_dir'
  #batch_process(output_dir, output_plots_dir, plotting_test)

  # Plot data for DOPs vs sats in view and DOPS vs altitude
  #sats2gdop_ratio(output_dir, output_plots_dir)
  #alt2gdop_ratio(output_dir, output_plots_dir)
  #alt2sats_ratio(output_dir, output_plots_dir, True)

  # Get statistics from total set of data in 'input_dir'
  #get_batch_stats(input_dir, print_lvl=0, plot=True)

  #plotting_test('TUT_back_50m-curve_gdoper.csv', in_dir=output_dir, out_dir=output_plots_dir)
  plotting_test('TUT_back_parking_gdoper.csv', in_dir=output_dir, out_dir=output_plots_dir)
  #plotting_test('TUT_front_lawn_gdoper.csv', in_dir=output_dir, out_dir=output_plots_dir)

  pass
