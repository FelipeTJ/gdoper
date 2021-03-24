###############################################################################
# Gdoper v1.0                                                                 #
#                                                                             #
# File:  reader_rinex.py
# Author: Felipe Tampier Jara
# Date:   1 Mar 2021
# Email:  felipe.tampierjara@tuni.fi
#
# Description:
# Program returns the data for GPS satellites' positions. It first checks if 
# data for a given day has already been aquired and if not, it retrieves the
# data from the UNAVCO database and processes it accordingly.
#                                                                             #
###############################################################################

#%%

from xarray.core.dataset import Dataset
from typing import Tuple, Dict
import georinex as gr
import datetime as dt
import pyproj as pp
import wget as wget
import time
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import unavco_stations as s
import d_print as p


# Directory where downloaded rinex files are stored 
# The sublist of the path removes the /src directory part
R_FOLDER = os.path.dirname(os.path.abspath(__file__) )[:-4]+ '/rinex_files'

# Required tolerance for the eccentricity anomaly error
ECC_TOL = 0.001

DEFAULT_STATIONS = ['ac70','ab33','ac15']
DL_MAX_TRIES = 5


class Satellite:
  def __init__(self, prn: str, date: dt.datetime, gps_data: Dataset):
    self.prn = prn
    self.gps_data = {date.date: gps_data}
    p.Print('debug0', f'Created Satellite object (PRN: {prn})')

  # TODO: Allow for large Datasets to be calculated all at once
  def get_position(self, req_date: dt.datetime, times = []):
    if not self.has_date(req_date):
      raise Exception('Data for this date doesn\'t exist')

    close_nav = self.gps_data[req_date.date].sel(time=req_date, method='nearest')
    p.Print('\\debug0', f'Satellite PRN: {self.prn}')
    p.Print('debug0', f'NAV GPS message from time: {close_nav["time"].values}')
    p.Print('debug0', f'Requested compute at time: {req_date}')
    td = close_nav["time"].values.astype('datetime64[us]').astype(dt.datetime)
    if td > req_date:
      p.Print('debug\\0', f'Time difference from data: -{td-req_date}')
    else:
      p.Print('debug\\0', f'Time difference from data: +{req_date-td}')

    # Set the requested time
    if len(times) == 0:
      close_nav['time'] = req_date
      close_nav = close_nav.expand_dims("time")
      p.Print('debug\\0', f'close_nav 1: {close_nav["time"].values}')
    else:
      close_nav['time'] = times
      p.Print('debug\\0', f'close_nav X: {close_nav["time"]}')
  

    # TODO: Implement function below manually
    ecef = gr.keplerian.keplerian2ecef(close_nav)

    return (ecef[0][0], ecef[1][0], ecef[2][0])

  def add_date(self, datetime: dt.datetime, gps_data: Dataset):
    if not self.has_date(datetime):
      self.gps_data[datetime.date] = gps_data
    else:
       p.Print('debug', f'Data for {datetime.date} already exists.')

  def has_date(self, date: dt.datetime) -> bool:
    return date.date in self.gps_data.keys()


class Orbital_data:
  def __init__(self, utc):
    # Date parameters
    self.utc = dt.datetime.strptime(utc, '%Y-%m-%d %H:%M:%S')
    self.gps_year = self.utc.year - 2000
    self.gps_day = (self.utc - dt.datetime(self.utc.year, 1, 1)).days + 1  # Adjust for date

    # File name parameters
    self.is_file_available = False
    self.station = DEFAULT_STATIONS[0]
    self.rinex_file = f'{self.station}{self.gps_day}0.{self.gps_year}n.Z'
    self.filedir_remote = self.get_remote_dir()
    self.filedir_local = self.get_file()

    # Dict containing all satellite objects
    self.sats: Dict[str, Satellite] = {}
    self.read_rinex()
 
  def print_data(self):
    print()
    p.Print('info',f'Variables for: {self}')
    for i in list(self.__dict__.keys()):
      p.Print('info',f' - {i:15} : {(self.__dict__[i] if type(self.__dict__[i]) != dict else "<dict>")}')
    print()
 
  def change_station(self, new_station: str):
    self.station = new_station
    self.rinex_file = f'{self.station}{self.gps_day}0.{self.gps_year}n.Z'
    self.filedir_remote = self.get_remote_dir()
    self.filedir_local = f'{R_FOLDER}/{self.rinex_file}'
    self.is_file_available = False

  def change_date(self, new_datetime: dt.datetime):
    
    self.utc = (dt.datetime.fromisoformat(new_datetime) if (type(new_datetime) == str) else new_datetime)
    self.gps_year = self.utc.year - 2000
    self.gps_day = (self.utc - dt.datetime(self.utc.year, 1, 1)).days + 1  # Adjust for date
    self.change_station(self.station) # Update all filenames and directories

  def get_remote_dir(self) -> str:
    """
    Based on the date, return a string corresponding to the location
    of the station data in the remote file repository.
    """
    return f'{s.get_nav()}20{self.gps_year}/{self.gps_day}/' + self.rinex_file

  def local_file_exists(self) -> bool:
    p.Print('debug0', f'local_file_exists()')
    for file in os.listdir(R_FOLDER):
      # Check if file with same day exists
      if file.endswith(self.rinex_file[4:]):
        self.change_station(file[:4])
        p.Print('debug0',f'File exists locally: {self.filedir_local}')
        return True
    return False

  def get_file(self) -> str:
    p.Print('debug0', f'get_file()')
    if not self.local_file_exists():
      downloaded = False
      tries = 0
      while not downloaded:
        p.Print('info', f'Downloading...')

        # If current station is unavailable at self.utc: try other stations
        if 1 <= tries and tries < len(DEFAULT_STATIONS):
          self.change_station(DEFAULT_STATIONS[tries])
        elif 1 <= tries:
          self.change_station(s.get_station())

        if tries >= DL_MAX_TRIES:
          raise Exception(f'Maximum download request attempts ({DL_MAX_TRIES}) reached.')

        url = f'ftp://{s.get_url()}{self.filedir_remote}'
        out = f'{R_FOLDER}/{self.rinex_file}'

        p.Print('debug', f'Remote URL: {url}')
        p.Print('debug', f'Local dir: {out}')

        tries = tries+1
        try:
          file = wget.download(url, out)
          if file == out:
            p.Print('info', f'File downloaded successfully: {out}')
          downloaded = True
        
        except:
          p.Print('info', f'Unable to download file: {url}')
    
    self.is_file_available = True
    return f'{R_FOLDER}/{self.rinex_file}'

  def read_rinex(self):
    p.Print('debug0', f'read_rinex()')
    if not self.is_file_available:
      self.filedir_local = self.get_file()

    # Read all the data from Rinex file
    p.Print('info0', f'Reading Rinex file "{self.rinex_file}"...')
    nav = gr.load(self.filedir_local)

    now = time.perf_counter()
    for n in range(1, nav['sv'].size + 1):
      sat = "G"+f'{n:02}'
      #p.Print('\\debug',f'Satellite: {sat}')

      # Create or add data to Satellite object at date of self.utc
      if sat not in self.sats.keys():
        self.sats[sat] = Satellite(sat, self.utc, nav.sel(sv=sat).dropna(dim="time", how="all"))
      elif not self.sats[sat].has_date(self.utc):
        self.sats[sat].add_date(self.utc, nav.sel(sv=sat).dropna(dim="time", how="all"))
      else:
        pass

    p.Print('info\\0',f'Done. ({time.perf_counter()-now:.3f}s for {len(self.sats)} satellites)')

  def get_sats_pos(self) -> dict:
    p.Print('debug0', f'get_sats_pos()')
    if not self.is_file_available:
      self.read_rinex()
    
    if len(self.sats) == 0:
      p.Print('\\error\\', f'[get_sats_pos] No Satellite objects in this instance (no file has been read yet)')
      return

    now = time.perf_counter()
    p.Print('info0', f'Calculating satellite positions at "{self.utc}"...')
    mapping = {}
    for prn in list(self.sats.keys()):
      mapping[prn] = self.sats[prn].get_position(self.utc)

    p.Print('info\\0',f'Done. ({time.perf_counter()-now:.3f}s for {len(self.sats)} positions)')

    return mapping


if __name__ == '__main__':

  o = Orbital_data('2019-07-10 07:25:31')
  o.print_data()
  print(o.get_sats_pos())
  #o.get_sats_pos()

