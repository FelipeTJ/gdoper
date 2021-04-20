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
from src.processing import *
from src.common import BASE_FOLDER  
# BASE_FOLDER is the directory where this file (gdoper.py) resides




if __name__ == '__main__':
  parse_input()

  #fov_test('50m-curve.csv',15)
  #fov_test('test_data.csv',15)

  # Input and output directories for Gdoper processing
  input_dir = BASE_FOLDER + os.sep + 'Tampere_flights_full'
  output_dir = input_dir + '_gdoper'

  # Process all files in 'input_dir' with Gdoper
  batch_process(input_dir, output_dir, single_gdoper)

  # Output directory for plots
  output_plots_dir = input_dir + os.sep + '_plots'

  # Plot data for all files in 'output_dir' and output plots to 'output_plots_dir'
  batch_process(output_dir, output_plots_dir, plotting_test)

  # Plot 
  sats2gdop_ratio(output_dir, output_plots_dir)
  alt2gdop_ratio(output_dir, output_plots_dir)
  get_batch_stats(input_dir, print_lvl=0, plot=True)

  
  pass