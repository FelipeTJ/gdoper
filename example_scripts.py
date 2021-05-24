
from src.calc_manager import CalcManager, ManagerOptions, RinexOptions
from src.fov_models import FOV_view_match, FOV_constant_mask, FOV_treeline
from src.processing import Plotter
from src.common import CSTL, BASE_FOLDER
from src.calcs import Calc_gdop, Calc_wgdop

from os import sep

def simple_test(in_file, in_dir):
	"""
		A test to demonstrate the basic functionality of Gdoper.
		Test data from a drone is located in:
				gdoper/test_data/test_data_full.csv
		Output data is saved as:
				gdoper/test_data_gdoper/test_data_full_gdoper.csv
	"""

	# ManagerOptions objects allows specification of several parameters
	out_dir = in_dir+'_gdoper'
	opts = ManagerOptions(folder_input=in_dir, folder_output=out_dir)

	# FOV model is initiated with GPS and GAL constellations to indicate
	# that these were the constellations supported by the GNSS receiver 
	fov = FOV_view_match([CSTL.GPS, CSTL.GAL])

	# GDOP calculations can only be performed for a single constellation
	fov.add_calc(Calc_gdop(CSTL.GPS))
	fov.add_calc(Calc_gdop(CSTL.GAL))

	# WGDOP uses all satellites seen by the FOV model
	fov.add_calc(Calc_wgdop())

	# CalcManager is the object that orchestrates the processing
	manager = CalcManager(in_file, opts, debug=1)
	manager.add_FOV(fov)

	# Data is processed and output according to the parameters of ManagerOptions
	manager.process_data()

	# Create a Plotter object to give visual information about the processed data
	p = Plotter(manager)
	p.do_plots()



def default_test():
  """
    A test using default parameters. 
    - File is assumed to be in the directory 'test_data'.
    - Processed data is output to the same directory.
  """

  data_file = 'test_data_full.csv'

  fov = FOV_view_match([CSTL.GPS, CSTL.GAL])
  fov.add_calc(Calc_wgdop())

  manager = CalcManager(data_file, debug=1)
  manager.add_FOV(fov)

  manager.process_data()


if __name__ == '__main__':

  test_file = 'test_data_full.csv'
  test_dir = BASE_FOLDER + sep + 'test_data'

  simple_test(test_file, test_dir)

  #default_test()