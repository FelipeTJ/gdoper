import matplotlib.pyplot as plt
import numpy as np
import time
import sys
import os

import src.reader_pos_data as rps
import datetime as dt
import src.common as cm

from src.calc_manager import CalcManager, ManagerOptions
from src.fov_models import *
from src.calcs import Calc_gdop
from src.d_print import Debug,Info, Stats, Set_PrintLevel

SAMPLING = 5
SE = os.sep

mean_speed = []
max_speed = 0.0
tot_time = dt.timedelta(seconds=0)

# TODO: implement parsing
def parse_input() -> dict:
  argn = len(sys.argv)
  
  if argn <= 1:
    return
  
  for i in range(argn):
    if sys.argv[i] == 'demo':
      fn = 'test_data_full.csv'
      default_test(fn)

def single_gdoper(in_file, in_dir, out_dir):

  m_opts = ManagerOptions(folder_input=in_dir, folder_output=out_dir)

  gdoper = CalcManager(in_file, m_opts=m_opts)
  gdoper.set_FOV(FOV_view_match())
  gdoper.add_calc(Calc_gdop())
  gdoper.process_data()

def batch_process(in_dir, out_dir, func, stats=True, skip_existing=True):
  if not os.path.exists(in_dir):
      raise Exception(f'"{in_dir}" does not exist. Input full directory path')

  if out_dir != '' and not os.path.exists(out_dir):
    os.mkdir(out_dir)

  start = time.perf_counter()

  if func.__name__ == 'single_gdoper' and skip_existing:
    Info(f'Skipping files that have already been processed.')
    Info(f'In dir: {out_dir}')
    Info(f'Set skip_existing=False to re-process the files\n')

  for file in os.listdir(in_dir):
    if file[-4:] != '.csv': continue

    if skip_existing and os.path.exists(out_dir + os.sep + file[:-4]+'_gdoper.csv'): 
      Info(f'Skipped {file}')
      continue

    func(file, in_dir, out_dir)

  end = time.perf_counter()

  if stats:
    print()
    Stats(msg=f'Process: {func.__name__}')
    Stats(msg=f'Total processing time: {end-start:.2f}s')

def flight_time_counter(in_file, in_dir, out_dir):
  global tot_time

  f_dir = in_dir + SE + in_file

  r = rps.ReaderPos(f_dir)
  r.setup()

  data = r.get_merged_cols(cm.CHN_UTC)
  
  t0 = dt.datetime.fromisoformat(data[cm.CHN_UTC][0])
  t1 = dt.datetime.fromisoformat(data[cm.CHN_UTC][-1])

  tot_time = tot_time + (t1-t0)

def speed_counter(in_file, in_dir, out_dir):
  global max_speed
  global mean_speed

  f_dir = in_dir + SE + in_file

  r = rps.ReaderPos(f_dir)
  r.setup()

  data = r.get_merged_cols('speed(m/s)')

  
  for i in data['speed(m/s)']:
    sp = float(i)
    mean_speed.append(sp)
    if sp > max_speed:
      max_speed = sp

  pass

def fov_test(in_file, out_file, mask_a, mask_m):

  drone_data = in_file

  fov = FOV_constant_mask2()
  fov.setup(mask_a)

  m_opts = ManagerOptions(file_oname=out_file)

  gdoper = CalcManager(drone_data, m_opts=m_opts, debug=1)  # ts is the sampling time from position data
  gdoper.set_FOV(fov)
  gdoper.add_calc(Calc_gdop())
  gdoper.process_data()

  #gdoper.opts.file_output = out_name[:-4] + '_2.csv'
  #gdoper.set_FOV(FOV_treeline(mask_a, min_mask=mask_m))
  #gdoper.process_data()

  #plotting_test(out_name)

  #fov.setup(mask_a - 5)
  #gdoper.output_file = out_name[:-6]+f'{mask_a - 5}.csv'
  #gdoper.process_data()
  #plotting_test(gdoper.output_file)

def rinex_test(in_file):
  drone_data = in_file

  gdoper = CalcManager(drone_data, ts=5, debug=1, rinex_file='FINS00FIN_R_20210280000_01D_MN.rnx')  # ts is the sampling time from position data
  gdoper.set_FOV(FOV_view_match())
  gdoper.add_calc(Calc_gdop())
  gdoper.process_data()
  pass

def default_test(in_file):
  drone_data = in_file

  gdoper = CalcManager(drone_data, ts=5, debug=1)  # ts is the sampling time from position data
  gdoper.set_FOV(FOV_view_match())
  gdoper.add_calc(Calc_gdop())
  gdoper.process_data()

def plotting_test(in_file, in_dir=cm.POS_DATA_FOLDER, out_dir=cm.POS_DATA_FOLDER, sat_name=cm.CHN_SAT, grid=False, lims=True):

  drone_data = in_dir + os.sep + in_file
  out_file = out_dir + os.sep + in_file[:-4]
  
  r = rps.ReaderPos(drone_data)
  r.setup()

  data = r.get_merged_cols(cm.CHN_LON, cm.CHN_LAT, cm.CHN_ALT, cm.CHN_UTC, sat_name, 'GDOP', 'HDOP', 'VDOP')


  """          Drone path plot            """

  lat = [float(i) for i in data[cm.CHN_LAT]]
  lon = [float(i) for i in data[cm.CHN_LON]]
  alt = [float(i) for i in data[cm.CHN_ALT]]

  fig = plt.figure()
  ax = fig.add_subplot(projection='3d')
  #plt.gca().invert_xaxis()

  ax.plot(lat, lon, alt, label='Drone path')

  ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1), frameon=True)

  xstart = 61.4502
  xticks = 7
  if "back_50" in in_file:
    xstart = 61.4498
    xticks = 8
  elif "front_lawn" in in_file:
    xstart = 61.4484
    xticks = 7
  elif "back_parking" in in_file:
    xstart = 61.4502
    xticks = 7

  xstep = 0.0002
  #xstop = xstart + xticks*xstep
  xlabs = [f'{xstart:.4f}']
  xl = []
  for i in range(xticks):
    xl.append(xstart+i*xstep)
    if i == 0 or i == xticks-1: continue
    xlabs.append(f'+{i*xstep:.4f}')
  xlabs.append('')

  ystart = 23.8620
  yticks = 9
  ystep = 0.0005
  if "back_50" in in_file:
    ystart = 23.8602
    yticks = 9
    ystep = 0.0002
  elif "front_lawn" in in_file:
    ystart = 23.8545
    yticks = 7
    ystep = 0.0005
  elif "back_parking"in in_file:
    ystart = 23.8620
    yticks = 9
    ystep = 0.0005
  #ystop = ystart + yticks*ystep
  ylabs = ['', f'{ystart:.4f}']
  yl = []
  for i in range(yticks):
    yl.append(ystart+i*ystep)
    if i == 0 or i == yticks-1: continue
    ylabs.append(f'+{i*ystep:.4f}')

  ax.set_xlabel('Latitude (°)', labelpad=12.0)
  ax.set_xticks(xl)
  ax.set_xticklabels(xlabs, fontsize='small', rotation=15.0)
  #ax.set_xticklabels([])

  ax.set_ylabel('Longitude (°)', labelpad=14.0)
  ax.set_yticks(yl)
  ax.set_yticklabels(ylabs, fontsize='small', rotation=-10.0)
  #ax.set_yticklabels([])

  ax.set_zlabel('Altitude above sea (m)')

  ax.view_init(elev=30, azim=-55)

  fn = out_file + '_plot_path'

  plt.grid()
  #plt.title('Path followed by drone', pad=2.0)
  plt.savefig(fn+'.pdf', format='pdf', bbox_inches='tight')
  plt.close('all')

  Info(f'Plotted path for: {out_file.split(os.sep)[-1]}')


  """        GDOP and sats plot           """

  g = [float(i) for i in data['GDOP']]
  v = [float(i) for i in data['VDOP']]
  h = [float(i) for i in data['HDOP']]
  s = [float(i) for i in data[sat_name]]

  t0 = data[cm.CHN_UTC][0]
  t0 = dt.datetime.fromisoformat(t0)
  t = [(dt.datetime.fromisoformat(i) - t0).seconds for i in data[cm.CHN_UTC]]

  plt.clf()
  plt.cla()

  fig, (ax1,ax2) = plt.subplots(nrows=2, ncols=1, figsize=(9,8))

  #fig.suptitle('Satellites in view and DOPs',y=0.92)

  ax1.plot(t, s, label='Satellites in view')
  ax2.plot(t, g, label='GDOP')
  ax2.plot(t, v, label='VDOP')
  ax2.plot(t, h, label='HDOP')

  ax1.legend(loc='best')
  ax1.set_xlabel('time (s)')
  ax1.set_ylabel('Number of visible satellites')
  if lims: ax1.set_xlim(-5,t[-1]+5)
  if lims: ax1.set_ylim(10, 25)
  if grid: ax1.grid()

  ax2.legend()
  ax2.set_xlabel('time (s)')
  ax2.set_ylabel('DOP value')
  if lims: ax2.set_xlim(-5,t[-1]+5)
  if lims: ax2.set_ylim(0.1, 1.7)
  if grid: ax2.grid()

  fn = out_file + '_plot_DOPS'

  plt.savefig(fn+'.pdf', format='pdf', bbox_inches='tight')
  plt.close('all')

  Info(f'Plotted DOPS and Sats for: {out_file.split(os.sep)[-1]}')

# TODO: finish plots
def fov_plots(in_file, in_dir=cm.POS_DATA_FOLDER, out_dir=cm.POS_DATA_FOLDER):
  drone_data = in_dir + SE + in_file
  out_file = out_dir + SE + in_file[:-4]
  
  r = rps.ReaderPos(drone_data)
  r.setup()

  s1_n = 'sats_treeline'
  s2_n = 'sats_const_mask'

  data = r.get_merged_cols(cm.CHN_UTC, cm.CHN_SAT, s1_n, s2_n)

  """            Sats plot s              """

  s = [float(i) for i in data[cm.CHN_SAT]]
  s1 = [float(i) for i in data[s1_n]]
  s2 = [float(i) for i in data[s2_n]]

  t0 = data[cm.CHN_UTC][0]
  t0 = dt.datetime.fromisoformat(t0)
  t = [(dt.datetime.fromisoformat(i) - t0).seconds for i in data[cm.CHN_UTC]]

  plt.clf()
  plt.cla()

  fig, (ax1,ax2) = plt.subplots(nrows=2, ncols=1, figsize=(9,8))

  fig.suptitle('Satellites in view and DOPs',y=0.92)

  ax1.plot(t, s, label='Satellites in view')
  ax2.plot(t, s1, label='FOV_treeline')
  ax2.plot(t, s2, label='FOV_constant_mask')


  ax1.legend(loc='best')
  ax1.set_xlim(-5,t[-1]+5)
  ax1.set_xlabel('Seconds')
  ax1.set_ylim(10, 25)
  #if grid: ax1.grid()

  ax2.legend()
  ax2.set_xlim(-5,t[-1]+5)
  ax2.set_xlabel('Seconds')
  ax2.set_ylim(0.1, 1.7)
  #if grid: ax2.grid()

  fn = out_file + '_plot_DOPS'

  plt.savefig(fn+'.pdf', format='pdf', bbox_inches='tight')
  plt.close('all')

def alt2gdop_getter(in_file, in_dir, out_dir, d):

  drone_data = in_dir + SE + in_file
  
  r = rps.ReaderPos(drone_data)
  r.setup()

  data = r.get_merged_cols(cm.CHN_ALT, 'GDOP', 'VDOP', 'HDOP')

  inter = 5
  last = int(float(data[cm.CHN_ALT][0])/10)*10 - inter

  for i in range(len(data['GDOP'])):

    altitude = float(data[cm.CHN_ALT][i])

    if altitude >= last + inter:
      last = last + inter

    altitude = last

    if altitude not in d['GDOP'].keys():
      d['GDOP'][altitude] = [float(data['GDOP'][i])]
      d['VDOP'][altitude] = [float(data['VDOP'][i])]
      d['HDOP'][altitude] = [float(data['HDOP'][i])]
    else:
      d['GDOP'][altitude].append(float(data['GDOP'][i]))
      d['VDOP'][altitude].append(float(data['VDOP'][i]))
      d['HDOP'][altitude].append(float(data['HDOP'][i]))

def alt2gdop_ratio(in_dir, out_dir, stats=False):
  """    Number of sats to GDOP ratio    """

  if not os.path.exists(in_dir):
      raise Exception(f'"{in_dir}" does not exist. Input full directory path')

  start = time.perf_counter()

  out_file = out_dir + SE + 'alt2gdop_ratio'

  vis_sats = {'GDOP':{}, 'VDOP':{}, 'HDOP':{}}

  for file in os.listdir(in_dir):
    alt2gdop_getter(file, in_dir, out_dir, vis_sats)

  x = sorted(list(vis_sats['GDOP'].keys()))
  gs = [vis_sats['GDOP'][i] for i in x]
  vs = [vis_sats['VDOP'][i] for i in x]
  hs = [vis_sats['HDOP'][i] for i in x]

  y_g = [np.mean(i) for i in gs]
  er_g = [np.var(i, ddof=1) for i in gs]

  y_v = [np.mean(i) for i in vs]
  er_v = [np.var(i, ddof=1) for i in vs]

  y_h = [np.mean(i) for i in hs]
  er_h = [np.var(i, ddof=1) for i in hs]

  fig, ax = plt.subplots()

  ax.errorbar(x, y_g, yerr=er_g, capsize=3, label='GDOP')
  ax.errorbar(x, y_v, yerr=er_v, capsize=3, label='VDOP')
  ax.errorbar(x, y_h, yerr=er_h, capsize=3, label='HDOP')
  ax.set_title('DOPs vs Altitude above sea level',pad=10.0)
  ax.legend()
  ax.grid(axis='y')
  ax.set_ylabel('Mean DOP values')
  ax.set_xlabel('Altitude')

  #plt.show()
  plt.savefig(out_file+'.pdf', format='pdf')
  plt.close('all')
  
  end = time.perf_counter()
  if stats:
    print()
    Stats(msg=f'Process: alt2gdop_ratio')
    Stats(msg=f'Total processing time: {end-start:.2f}s\n')

def sats2gdop_getter(in_file, in_dir, out_dir, d):

  drone_data = in_dir + SE + in_file
  
  r = rps.ReaderPos(drone_data)
  r.setup()

  data = r.get_merged_cols(cm.CHN_SAT, 'GDOP', 'VDOP', 'HDOP')

  for i in range(len(data['GDOP'])):

    n_vis_sats = data[cm.CHN_SAT][i]
    if n_vis_sats not in d['GDOP'].keys():
      d['GDOP'][n_vis_sats] = [float(data['GDOP'][i])]
      d['VDOP'][n_vis_sats] = [float(data['VDOP'][i])]
      d['HDOP'][n_vis_sats] = [float(data['HDOP'][i])]
    else:
      d['GDOP'][n_vis_sats].append(float(data['GDOP'][i]))
      d['VDOP'][n_vis_sats].append(float(data['VDOP'][i]))
      d['HDOP'][n_vis_sats].append(float(data['HDOP'][i]))

def sats2gdop_ratio(in_dir, out_dir, stats=False):
  """    Number of sats to GDOP ratio    """

  if not os.path.exists(in_dir):
      raise Exception(f'"{in_dir}" does not exist. Input full directory path')

  start = time.perf_counter()

  out_file = out_dir + SE + 'sats2gdop_ratio'

  vis_sats = {'GDOP':{}, 'VDOP':{}, 'HDOP':{}}

  for file in os.listdir(in_dir):
    sats2gdop_getter(file, in_dir, out_dir, vis_sats)

  x = sorted(list(vis_sats['GDOP'].keys()))
  gs = [vis_sats['GDOP'][i] for i in x]
  vs = [vis_sats['VDOP'][i] for i in x]
  hs = [vis_sats['HDOP'][i] for i in x]

  y_g = [np.mean(i) for i in gs]
  er_g = [np.var(i, ddof=1) for i in gs]

  y_v = [np.mean(i) for i in vs]
  er_v = [np.var(i, ddof=1) for i in vs]

  y_h = [np.mean(i) for i in hs]
  er_h = [np.var(i, ddof=1) for i in hs]

  fig, ax = plt.subplots()

  ax.errorbar(x, y_g, yerr=er_g, capsize=3, label='GDOP')
  ax.errorbar(x, y_v, yerr=er_v, capsize=3, label='VDOP')
  ax.errorbar(x, y_h, yerr=er_h, capsize=3, label='HDOP')
  ax.set_title('DOPs vs Number of visible satellites',pad=10.0)
  ax.legend()
  ax.grid(axis='y')
  ax.set_ylabel('Mean DOP values')
  ax.set_xlabel('Satellites in view')

  #plt.show()
  plt.savefig(out_file+'.pdf', format='pdf')
  plt.close('all')
  
  end = time.perf_counter()

  if stats:
    print()
    Stats(msg=f'Process: sats2gdop_ratio')
    Stats(msg=f'Total processing time: {end-start:.2f}s\n')

def alt2sats_getter(in_file, in_dir, out_dir, d):

  drone_data = in_dir + SE + in_file
  
  r = rps.ReaderPos(drone_data)
  r.setup()

  data = r.get_merged_cols(cm.CHN_ALT, cm.CHN_SAT)
  #print(in_file)
  #Debug(0, f'len alts: {len(data[c.CHN_ALT])}, len sats: {len(data[c.CHN_SAT])}')

  inter = 5
  last = int(float(data[cm.CHN_ALT][0])/10)*10 - inter

  for i in range(len(data[cm.CHN_SAT])):

    altitude = float(data[cm.CHN_ALT][i])

    if altitude >= last + inter:
      last = last + inter

    altitude = last

    if altitude not in d.keys():
      d[altitude] = [float(data[cm.CHN_SAT][i])]
    else:
      d[altitude].append(float(data[cm.CHN_SAT][i]))

def alt2sats_ratio(in_dir, out_dir, stats=False):
  """    Number of sats to GDOP ratio    """

  if not os.path.exists(in_dir):
      raise Exception(f'"{in_dir}" does not exist. Input full directory path')

  start = time.perf_counter()

  out_file = out_dir + SE + 'alt2sats_ratio'

  vis_sats = {}

  for file in os.listdir(in_dir):
    alt2sats_getter(file, in_dir, out_dir, vis_sats)

  x = sorted(list(vis_sats.keys()))
  gs = [vis_sats[i] for i in x]
  maxs = [max(vis_sats[i]) for i in x]
  mins = [min(vis_sats[i]) for i in x]
  c = 0
  for i in x:
    c += len(vis_sats[i])
  dist = [len(vis_sats[i])/c for i in x]
  print(c)

  y_g = [np.mean(i) for i in gs]
  er_g = [np.var(i, ddof=1) for i in gs]

  fig, (ax1, ax2) = plt.subplots(nrows=2, figsize=(9,8))

  ax1.plot(x, maxs, label='Max visible', marker='.')
  ax1.plot(x, y_g, label='Mean visible', marker='.')
  ax1.plot(x, mins, label='Min visible', marker='.')
  

  ax1.set_title('SVs in view vs Altitude above sea level',pad=10.0)
  ax1.legend()
  ax1.grid(axis='y')
  ax1.set_ylabel('SVs in view')
  ax1.set_xlabel('Altitude')

  ax2.plot(x, dist, label='Distribution of samples', marker='.')
  #ax2.fill_between(x, dist)
  ax2.legend()
  ax2.grid(axis='y')
  ax2.set_xlabel('Altitude')

  #plt.show()
  plt.savefig(out_file+'.pdf', format='pdf', bbox_inches='tight')
  plt.close('all')
  
  end = time.perf_counter()
  if stats:
    print()
    for i in list(vis_sats.keys()):
      Stats(0, msg=f'alt: {i:>5} m\tmax in view: {max(vis_sats[i])}\tmin in view: {min(vis_sats[i])}\tdata points: {len(vis_sats[i])}')
    Stats(msg=f'Process: alt2sat_ratio')
    Stats(msg=f'Total processing time: {end-start:.2f}s\n')
   
def get_batch_stats(in_dir, print_lvl, plot=False):
  global mean_speed
  global max_speed
  global tot_time

  Set_PrintLevel(print_lvl)

  start = time.perf_counter()

  batch_process(in_dir, '', flight_time_counter, stats=False, skip_existing=False)
  batch_process(in_dir, '', speed_counter, stats=False, skip_existing=False)

  if plot:
    plt.cla()
    plt.clf()
    fig, ax = plt.subplots()
    ax.grid(axis='both')

    ax.hist(mean_speed, 40, (0,20), log=True, density=True, edgecolor='gray')
    ax.set_title('Speed distribution of all flights in the set')
    ax.set_ylabel('Sample density')
    ax.set_xlabel('Speed m/s')
    ax.set_ylim(0, 1)
    ax.set_xlim(0, 20)

    plt.savefig(in_dir+'_plots'+os.sep+'speeds.pdf', format='pdf')
    plt.close('all')

  pts = len(mean_speed)
  med = np.median(mean_speed)
  mean_speed = np.mean(mean_speed)


  end = time.perf_counter()

  print()
  Stats(-1, f'Total flight time: {str(tot_time):>8} hrs')
  Stats(-1, f'Max speed:         {max_speed:>8.3f} m/s')
  Stats(-1, f'Mean speed:        {mean_speed:>8.3f} m/s')
  Stats(-1, f'Median speed:      {med:>8} m/s')
  Stats(-1, f'Amount of samples: {pts:>12}')


  print()
  Stats(1,f'Process: get_batch_stats')
  Stats(1,f'Total processing time: {end-start:.2f}s')
