###############################################################################
# Gdoper v1.2                                                                 #
#                                                                             #
# File:  reader_rinex.py
# Author: Felipe Tampier Jara
# Date:   5 Apr 2021
# Email:  felipe.tampierjara@tuni.fi
#
# Description:
# Program returns the data for GPS satellites' positions. It first checks if 
# data for a given day has already been aquired and if not, it retrieves the
# data from the UNAVCO database and processes it accordingly.
#                                                                             #
###############################################################################

#%%

import xarray as xr
from xarray.core.dataarray import DataArray
from xarray.core.dataset import Dataset
from typing import Mapping, List, Tuple
from dataclasses import dataclass
from enum import Enum
import georinex as gr
import datetime as dt
import numpy as np
import pyproj as pp
import typing as t
import wget as wget
import copy
import time
import os

from d_print import Enable_Debug
os.chdir(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
  import common as cm
  import unavco_stations as s
  from d_print import Info, Debug, Stats, Set_PrintLevel, RED, CEND
else:
  import src.common as cm
  import src.unavco_stations as s
  from src.d_print import Info, Debug, Stats, Set_PrintLevel, RED, CEND

# TODO: create directory if it doesn't exist
# Directory where downloaded rinex files are stored 
# The sublist of the path removes the /src directory part
R_FOLDER = os.path.dirname(os.path.abspath(__file__) )[:-4]+ '/rinex_files'

# Required tolerance for the eccentricity anomaly error
ECC_TOL = 0.001

DEFAULT_STATIONS = ['ac70','ab33','ac15']
DL_MAX_TRIES = 5

# TODO: rinex_reader options:
# A dict of kwargs with all the default settings
# the dict can be accessed and modified at gdoper.py level


# EPN database file example:
# ftp://igs.bkg.bund.de/EUREF/obs/2021/028/ORIV00FIN_R_20210280000_01D_MN.rnx.gz
# **station_data:
#   date_measured:  28.1.2021
#   station_name:   ORIV
#   country_code:   FIN (Finland)
#   data_source:    R
#   resolution:     01D
#   rinex_const:    MN  (Mixed constellation navigation/ephemeris RINEX 3)

class Repo(Enum):
  UNAVCO = 1
  EPN = 2

@dataclass
class Station:                # Defaults for would-be UNAVCO stations in comments
  date_measured: str
  name:          str = 'ORIV'   # ac70
  country_code:  str = 'FIN'    # ''
  data_source:   str = 'R'      # ''
  resolution:    str = '01D'    # ''      # TODO: implement time resolution checking
  rinex_const:   str = 'GN'     # n
  station_type: Repo = Repo.EPN # UNAVCO

class RinexFile:
  """
    Class for handling RINEX filename manipulation
  """
  def __init__(self, station:Station, local_file='') -> None:
    self.__date = None      # Date of the measurements as datetime object 
    self.__station = None   # Station dataclass object
    self.__local_fn = None  # Name of local file containing rinex data
    self.__remote_fn = None # Name of remote repo file where data is available
    self.__repo = None      # Publicly available RINEX data (repo name)
    self.__has_data = False

    self.__setup(station, local_file)

  def __setup(self, station:Station, local_file,):
    if local_file != '':
      self.__local_fn = local_file
      self.__has_data = True
      return

    self.set_date(station.date_measured)
    self.__station = station              # TODO: add checking if station is in EPN network
    self.__repo = station.station_type
    self.__remote_fn = self.__get_remote_n(station)
  
  def __get_remote_n(self, station:Station):
    year = self.__date.year
    gps_day = (self.__date - dt.datetime(year, 1, 1)).days
    two_year = (float(year)/100 - int(float(year)/100))*100

    if self.__repo == Repo.EPN:
      Ccode = station.country_code
      R = station.data_source
      res = station.resolution
      M = station.rinex_const

      rem_dir = 'ftp://igs.bkg.bund.de/EUREF/obs/'
      fn = f'{self.__station.name}00{Ccode}_{R}_{year}{gps_day:03}0000_{res}_{M}.rnx.gz'
      return f'{rem_dir}{year}/{gps_day:03}/{fn}'
      
    elif self.__repo == Repo.UNAVCO:
      rem_dir = 'data-out.unavco.org/pub/rinex/nav/'
      fn = f'{self.__station.name}{gps_day:03}0.{two_year}n.Z'
      return f'{rem_dir}{year}/{gps_day:03}/{fn}'
    
    else:
      raise Exception(f'Repository \'{self.__repo}\' not supported')

  def set_date(self, idate):
    # Update date
    self.__date = dt.datetime.fromisoformat(idate) # TODO: use proper ISO-8601 parsing

    # Update filename if obj is initialized
    if self.__repo != None:
      self.__remote_fn = self.__get_remote_n(self.__station)

  def get_date(self):
    return self.__date

  def set_station(self, station:Station):
    self.__station = station
    self.set_date(station)

  def has_local_file(self):
    return self.__has_data

  def set_local_file(self, local:str):
    self.__local_fn = local
    self.__has_data = True

  def get_local_file(self):
    if self.__has_data:
      return self.__local_fn
    return None

  def get_remote_url(self):
    return self.__remote_fn

  def get_filename(self):
    return self.__remote_fn.split('/')[-1]

  def get_filename_date(self):
    if self.__repo == 'EPN':
      return self.get_filename()[12:23]

    elif self.__repo == 'UNAVCO':
      return self.get_filename()[4:10]

class Reader_rinex:
  def __init__(self):
    # Dict containing all satellite objects
    self.__sats: t.Dict[str, _Satellite] = {}

    self.__rinex_dir = None
    self.__rinex_file = None
    self.__is_setup = False

  def setup(self, date, rinex_dir=cm.RINEX_FOLDER):
    # Do setup of RinexFile obj and download data if needed

    # TODO: add creation of Station object to reader_rinex creation options
    stat = Station(date)
    self.__rinex_file = RinexFile(stat)
    self.__rinex_dir = rinex_dir

    if not self.__local_rinex_exists():
      self.__download_rinex()

    self.__read_rinex()
    if len(self.__sats) == 0:
      raise Exception('No Satellites positions were read.')

    self.__is_setup = True
    
  def modify_station(self):
    # TODO: Change station parameters
    pass

  def __local_rinex_exists(self) -> bool:
    file = self.__rinex_file.get_filename()
    if file in os.listdir(self.__rinex_dir):
      Debug(1, f'File exists locally: {file}')
      Debug(2, f'dir: {self.__rinex_dir}')
      full_local_dir = self.__rinex_dir + os.sep + file
      self.__rinex_file.set_local_file(full_local_dir)
      return True
    return False

  def __download_rinex(self):
    Enable_Debug()
    
    url = self.__rinex_file.get_remote_url()
    out = self.__rinex_dir + os.sep + url.split('/')[-1]

    fn = url.split('/')[-1]

    Info(f'Downloading \'{fn}\'...')
    Debug(0, f'From: {url}', nofunc=True)
    try:
      file = wget.download(url, out)
      if file == out:
        print()
        Info(f'File downloaded successfully: {fn}')

      else:
        raise Exception('File output was not as expected: {file}')
    except:
      # TODO: Query ftp to see which file formats are available for station
      raise Exception('Something failed')

    self.__rinex_file.set_local_file(out)

  def __read_rinex(self):
    Enable_Debug(2)

    Stats(1,f'Reading Rinex file "{self.__rinex_file.get_filename()}"...')
    now = time.perf_counter()
    
    # TODO: read only necessary constellations             v <- reads only GPS
    nav = gr.load(self.__rinex_file.get_local_file(), use='G')

    date = self.__rinex_file.get_date().date()

    for n in nav['sv']:
      sat = np.array2string(n).strip('\'')
      Debug(2,f'Satellite: {sat}\t date: {date}')

      # Create or add data to Satellite object at date of measurement
      if sat not in self.__sats.keys():
        self.__sats[sat] = _Satellite(sat, date, nav.sel(sv=sat).dropna(dim="time", how="all"))
      elif not self.__sats[sat].has_date(date):
        self.__sats[sat].add_date(date, nav.sel(sv=sat).dropna(dim="time", how="all"))

    Stats(1,f'Done. ({time.perf_counter()-now:.3f}s for {len(self.__sats)} satellites)')
    Stats(1,'')


  def get_sats_pos(self, time_list: List[dt.datetime]):
    Enable_Debug(2)

    if not self.__is_setup:
      raise Exception('Reader_rinex object has not been setup.')

    times = time_list.copy()

    # Convert to datetime objects if time_list is list of str
    if len(times) != 0:
      for i in range(len(times)):
        if type(times[i]) == str:
          times[i] = dt.datetime.fromisoformat(times[i])

    now = time.perf_counter()
    Stats(1,f'Calculating satellite positions "{self.__rinex_file.get_filename()}"...')

    results = {}
    for t in time_list:
        results[t] = {}
    
    for prn in list(self.__sats.keys()):
      data_array = self.__sats[prn].get_position(times)

      for t in times:
        results[t.isoformat(sep=' ')][prn] =  data_array.sel(time=t).values

    Stats(1,f'Done. ({time.perf_counter()-now:.3f}s for {len(self.__sats)*len(times)} positions)')
    Stats(1,'')

    # Output order is:  times{} -> prn{} = (x,y,z)
    return results


class _Satellite:
  def __init__(self, prn: str, date: dt.date, gps_data: Dataset):
    self.prn = prn
    self.dates = [date]
    self.gps_data = {self.dates[0]: gps_data}
    Debug(3, f'Created Satellite object (PRN: {prn})')
    Debug(3, f'data: {self.gps_data[self.dates[0]]["time"]}')


  def get_position(self, times: t.List[dt.datetime] = []):
    if len(times) == 0:
      raise Exception('list of times cannot be empty.')
    mes_date = dt.date(times[0].year, times[0].month, times[0].day)
    #Debug(f'Requesting pos for date: {mes_date}')
    if mes_date not in self.dates:
      raise Exception('Data for this date doesn\'t exist')

    # Select the nearest recorded NAV message 
    close_nav = self.gps_data[mes_date].sel(time=times, method='nearest')

    Debug(3, f'Satellite PRN: {self.prn}')
    Debug(3, f'NAV GPS message from times:')
    for i in close_nav["time"].values:
      Debug(3, f'- {i}')

    Debug(3, f'Requested compute at times:')
    for i in times:
      Debug(3, f'- {i}')

    # Get the time of the NAV message
    td = close_nav["time"].values.astype('datetime64[us]').astype(dt.datetime)

    Debug(3, f'Difference between NAV message and requested times (- before, + after NAV):')
    for i,j in zip(times, td):
      dif = i-j
      if dif < dt.timedelta(days=0):
        Debug(3, f' -{-dif}')
      else:
        Debug(3, f' +{dif}')

    Debug(3, f'After: {close_nav}')

    ecef = gr.keplerian.keplerian2ecef(close_nav)
    da = xr.DataArray(list(ecef), dims=['space', 'time'], coords=[['x','y','z'], times])
    return da

  def add_date(self, datetime: dt.datetime, gps_data: Dataset):
    if not self.has_date(datetime):
      self.gps_data[datetime.date] = gps_data
    else:
       Debug(1,  f'Data for {datetime.date} already exists.')

  def has_date(self, date: dt.date) -> bool:
    return date in self.gps_data.keys()


class Orbital_data:
  def __init__(self, utc: str = '1900-01-01 00:00:00', local_data = ''):
    # Date parameters
    d_utc = dt.datetime.fromisoformat(utc)
    y_utc = d_utc.year
    self.utc = dt.date(y_utc, d_utc.month, d_utc.day)
    self.gps_year = y_utc - 2000                              # TODO: convert properly
    self.gps_day = (self.utc - dt.date(y_utc, 1, 1)).days + 1    # Adjust for date

    # File name parameters
    self.is_file_available = False
    self.station = DEFAULT_STATIONS[0]
    self.rinex_file = f'{self.station}{self.gps_day:03}0.{self.gps_year}n.Z'
    self.filedir_remote = ''
    self.filedir_local = local_data

    self.user_provided_rinex = False
    if local_data != '':
      self.user_provided_rinex = True
      self.rinex_file = local_data[-14:]

    # Dict containing all satellite objects
    self.sats: t.Dict[str, _Satellite] = {}

    self.done_setup = False
 
  def print_data(self):
    #self.setup_check()
    
    print()
    Info(f'Variables for: {self}')
    for i in list(self.__dict__.keys()):
      Info(f' - {i:15} : {(self.__dict__[i] if type(self.__dict__[i]) != dict else "<dict>")}')
    print()

  # TODO: Create setup function
  def setup(self, utc: str = ''):
    try:
      d_utc = dt.datetime.fromisoformat(utc)

      if d_utc.year >= 2000:
        self.change_date(d_utc)
      else:
        raise Exception('Input date\'s year cannot be older than 2000')
    except:
      if self.utc.year == 1900:
        raise Exception('Setup needs an initial date to look for satellite data.')

    if not os.path.exists(cm.RINEX_FOLDER):
      os.mkdir(cm.RINEX_FOLDER)

    self.done_setup = True

    if not self.user_provided_rinex:
      self.filedir_local = self.get_file()
    else:
      self.change_rin_file(self.rinex_file)
      Debug(f'User given local dir: {self.filedir_local}, {self.rinex_file}, {self.utc}')
    
    self.filedir_remote = self.get_remote_dir()

    self.read_rinex()

    #Debug('Done setup\n')

  def setup_check(self):
    if not self.done_setup: 
      raise Exception('Orbital_data has not been set up.')
 
  def change_rin_file(self, fn: str):
    self.rinex_file = fn
    self.filedir_local = cm.RINEX_FOLDER + os.sep + fn
    self.station = self.rinex_file[:4]

    self.gps_day = int(self.rinex_file[4:7])
    self.gps_year = int(self.rinex_file[-5:-3])
    dt_dt = dt.datetime.strptime(f"{self.gps_day:03} {self.gps_year}", "%j %y")
    self.utc = dt.date(dt_dt.year, dt_dt.month, dt_dt.day)
    self.is_file_available = True
    
  def change_station(self, new_station: str):
    if not self.user_provided_rinex:
      self.station = new_station
      self.rinex_file = f'{self.station}{self.gps_day:03}0.{self.gps_year}n.Z'
      self.filedir_remote = self.get_remote_dir()
      self.filedir_local = f'{cm.RINEX_FOLDER}/{self.rinex_file}'
      self.is_file_available = False

  def change_date(self, new_datetime: dt.datetime):    
    #Debug(f'Current date: {self.utc}  -> {new_datetime}')    
    self.utc = (dt.datetime.fromisoformat(new_datetime) if (type(new_datetime) == str) else new_datetime)
    self.gps_year = self.utc.year - 2000
    self.gps_day = (self.utc - dt.datetime(self.utc.year, 1, 1)).days + 1  # Adjust for date
    self.utc = dt.date(self.utc.year, self.utc.month, self.utc.day)
    self.change_station(self.station) # Update all filenames and directories

  def get_remote_dir(self) -> str:
    """
    Based on the date, return a string corresponding to the location
    of the station data in the remote file repository.
    """  
    return f'{s.get_nav()}20{self.gps_year}/{self.gps_day:03}/' + self.rinex_file

  def local_file_exists(self) -> bool:
    self.setup_check()
    
    Debug(3, f'local_file_exists()')
    for file in os.listdir(cm.RINEX_FOLDER):
      # Check if file with same day exists
      #Debug(f'comparing self.rinex_file: {self.rinex_file[4:11]} vs {file[4:11]}')
      if self.rinex_file[4:11] in file[4:11]:
        self.change_rin_file(file)

        gd_p = self.filedir_local.find("Gdoper")
        if gd_p != -1:
          Debug(1, f'File exists locally: {self.filedir_local[gd_p-1:]}', True)
        else:
          Debug(1, f'File exists locally: {self.filedir_local}', True)

        return True
    return False

  def get_file(self) -> str:
    self.setup_check()
    
    Debug(3, f'get_file()')
    if not self.local_file_exists():
      downloaded = False
      tries = 0
      while not downloaded:
        Info(f'Downloading...')

        # If current station is unavailable at self.utc: try other stations
        if 1 <= tries and tries < len(DEFAULT_STATIONS):
          self.change_station(DEFAULT_STATIONS[tries])
        elif 1 <= tries:
          self.change_station(s.get_station())

        if tries >= DL_MAX_TRIES:
          raise Exception(f'Maximum download request attempts ({DL_MAX_TRIES}) reached.')

        url = f'ftp://{s.get_url()}{self.filedir_remote}'
        out = f'{cm.RINEX_FOLDER}/{self.rinex_file}'

        Debug(0, f'Remote URL: {url}')
        Debug(0, f'Local dir: {out}')

        tries = tries+1
        try:
          file = wget.download(url, out)
          if file == out:
            print()
            Info(f'File downloaded successfully: {out}')
          downloaded = True
        
        except Exception as e:
          Info(f'Unable to download file: {url}')
          Info(f'Error message: {e}')
    
    self.is_file_available = True
    return f'{cm.RINEX_FOLDER}/{self.rinex_file}'

  def read_rinex(self):
    self.setup_check()
    
    Debug(3, f'read_rinex()')
    if not self.is_file_available:
      self.filedir_local = self.get_file()

    # Read only GPS SVs from Rinex file
    Debug(2,f'Reading Rinex file "{self.rinex_file}"...')
    nav = gr.load(self.filedir_local, use='G')

    now = time.perf_counter()
    # TODO: reset to normal operation (this is testing mode)
    for n in nav['sv']:
      sat = np.array2string(n).strip('\'')
      #Debug(f'Satellite: {sat}\t date: {self.utc}')

      # Create or add data to Satellite object at date of self.utc
      if sat not in self.sats.keys():
        self.sats[sat] = _Satellite(sat, self.utc, nav.sel(sv=sat).dropna(dim="time", how="all"))
      elif not self.sats[sat].has_date(self.utc):
        self.sats[sat].add_date(self.utc, nav.sel(sv=sat).dropna(dim="time", how="all"))
      else:
        pass

    Stats(2,f'Done. ({time.perf_counter()-now:.3f}s for {len(self.sats)} satellites)')

  def get_sats_pos(self, time_list: List[dt.datetime]) -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
    """
      Input a list of times for when to compute the positions of the satellites.
      Inputs can be either ISO formatted strings or datetime objects.
    """
    self.setup_check()
    
    Debug(3, f'get_sats_pos()')
    if not self.is_file_available:
      self.read_rinex()
    
    if len(self.sats) == 0:
      Debug(-1, f'{RED}No Satellite objects in this instance (no file has been read yet){CEND}')
      return

    times = time_list.copy()

    if len(times) != 0:
      for i in range(len(times)):
        if type(times[i]) == str:
          times[i] = dt.datetime.fromisoformat(times[i])

    now = time.perf_counter()
    Debug(2, f'Calculating satellite positions for "{self.utc.year}-{self.utc.month}-{self.utc.day}"...')

    results = {}
    for t in time_list:
        results[t] = {}
    
    # TODO: fix output format to: time{} -> prn{} = (x,y,z)
    for prn in list(self.sats.keys()):
      dr = self.sats[prn].get_position(times)

      for t in times:
        results[t.isoformat(sep=' ')][prn] =  dr.sel(time=t).values

    Stats(2,f'Done. ({time.perf_counter()-now:.3f}s for {len(self.sats)*len(times)} positions)')

    # Output order is:  times{} -> prn{} = (x,y,z)

    return results


if __name__ == '__main__':

  #o = Orbital_data('2019-07-10 07:25:31')
  #o.setup()
  #o.print_data()
  #print("Results:\n",o.get_sats_pos(['2019-07-10 08:25:31', '2019-07-10 14:25:31']))
  #o.get_sats_pos(['2019-07-10 08:25:31', '2019-07-10 14:25:31'])

  r = Reader_rinex()
  r.setup('2019-07-10 07:25:31')
  r.get_sats_pos(['2019-07-10 08:25:31', '2019-07-10 14:25:31'])

# %%
'ftp://data-out.unavco.org/pub/rinex/nav/2021/057/ac070570.21n.Z'
'ftp://data-out.unavco.org/pub/rinex/nav/2021/57/ac70570.21n.Z'