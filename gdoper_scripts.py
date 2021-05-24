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

  #mask = 20
  #out = f'fov_constm_{mask}_mixed.csv'

  #fov_test(out, out, mask, 5)
  #fov_test('test_data.csv',15)
  #plotting_test(out,sat_name='sats_FOV', lims=False)
  #plotting_test('fov_t_5_gps.csv',sat_name='sats_FOV', lims=False)

  # Input and output directories for Gdoper processing
  input_dir = BASE_FOLDER + os.sep + 'Thesis_data'
  output_dir = input_dir + '_gdoper'


  # Output directory for plots
  output_plots_dir = input_dir + '_plots'

  # Plots for thesis
  # fn = 'TUT_back_50m-curve.csv'
  # basic_test(fn, input_dir)
  # fov_test(fn[:-4]+'_gdoper.csv','',0,0)

  # fn = 'TUT_back_parking.csv'
  # basic_test(fn, input_dir)
  # fov_test(fn[:-4]+'_gdoper.csv','',0,0)

  fn = 'TUT_front_lawn.csv'
  basic_test(fn, input_dir)
  fov_test(fn[:-4]+'_gdoper.csv','',0,0)

  # FOV models in thesis
  #fn = 'TUT_back_50m-curve.csv'
  #basic_test2(fn, input_dir)
  #fov_test(fn[:-4]+'_models_gdoper.csv','',0,0)

  # Process all files in 'input_dir' with Gdoper
  #batch_process(input_dir, output_dir, single_gdoper)

  # Plot data for all files in 'output_dir' and output plots to 'output_plots_dir'
  #batch_process(output_dir, output_plots_dir, plotting_test)

  # Plot data for DOPs vs sats in view and DOPS vs altitude
  #sats2gdop_ratio(output_dir, output_plots_dir)
  #alt2gdop_ratio(output_dir, output_plots_dir)
  #alt2sats_ratio(output_dir, output_plots_dir, True)

  # Get statistics from total set of data in 'input_dir'
  #get_batch_stats(input_dir, print_lvl=0, plot=True)

  #plotting_test('TUT_back_50m-curve_gdoper.csv', in_dir=output_dir, out_dir=output_plots_dir)
  #plotting_test('TUT_back_parking_gdoper.csv', in_dir=output_dir, out_dir=output_plots_dir)
  #plotting_test('TUT_front_lawn_gdoper.csv', in_dir=output_dir, out_dir=output_plots_dir)

  pass
