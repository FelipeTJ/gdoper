###############################################################################
# Gdoper v3.0                                                                 #
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

from xarray import DataArray
from xarray.core.dataset import Dataset
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum
from georinex import load, keplerian2ecef
import datetime as dt
import numpy as np
import copy
import time
import os

from ftputil import FTPHost


os.chdir(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
  import common as cm
  from common import CSTL
  import unavco_stations as s
  from d_print import Enable_Debug, Info, Debug, Stats, Set_PrintLevel, RED, GREEN, VIOLET, CEND
else:
  import src.common as cm
  from src.common import CSTL
  import src.unavco_stations as s
  from src.d_print import Enable_Debug,Info, Debug, Stats, Set_PrintLevel, RED, GREEN, VIOLET, CEND

# Directory where downloaded rinex files are stored 
# The index at the end ([:-4]) removes the /src directory part
R_FOLDER = os.path.dirname(os.path.abspath(__file__) )[:-4]+ '/rinex_files'

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
  UNAVCO = 'data-out.unavco.org/pub/rinex/nav/'
  EPN = 'igs.bkg.bund.de/EUREF/obs/'


# Unavco uses Rinex v2.11, only 2 constellations available
# (https://www.unavco.org/data/gps-gnss/ftp/ftp.html)
class UnvC(Enum):
  GPS = 'n' # GPS
  GAL = 'g' # Galileo
  MET = 'm' # METEO data

# Constellation names in EPN format from BKGE 
# (https://www.epncb.oma.be/ftp/center/data/BKGE.RDC)
class EpnC(Enum):
  GPS = 'GN'    # GPS
  GLO = 'RN'    # GLONASS
  GAL = 'EN'    # Galileo
  QZS = 'JN'    # QZSS
  BDS = 'CN'    # BeiDou
  SBS = 'SN'    # SBAS
  MIXED = 'MN'  # Mixed constellation file
  METEO = 'MM'  # METEO data
  VERIFIED = 'MO' # Verified GNSS obs data in compressed format

@dataclass
class StationOptions:             # Defaults for would-be UNAVCO stations in comments
  date_measured: str = None
  name:          str = 'ORIV'     # ac70
  country_code:  str = 'FIN'      # ''
  data_source:   str = 'R'        # ''
  resolution:    str = '01D'      # ''      # TODO[epic=rinex++]: implement time resolution checking
  data_repo:    Repo = Repo.EPN   # Repo.UNAVCO
  constellation:CSTL = CSTL.MIX   # CSTL.GPS

  def get_filename(self) -> str:
    if self.date_measured == None: 
      raise Exception(f'Date has not been defined for this object: {self.__repr__}')

    d = None
    if type(self.date_measured) == str:
      d = cm.iso_to_dateobj(self.date_measured)
    else:
      d = self.date_measured

    gps_day = (d - dt.datetime(d.year, 1, 1)).days + 1 

    if self.data_repo == Repo.EPN:
      return f'{self.name}00{self.country_code}_{self.data_source}_'\
              f'{d.year}{gps_day:03}0000_{self.resolution}_'\
              f'{self.constellation.value}N.rnx.gz'
    
    elif self.data_repo == Repo.UNAVCO:
      two_year = (float(d.year)/100 - int(float(d.year)/100))*100
      cstl = self.constellation.value
      if cstl == 'G':
        cstl = 'n'
      elif cstl == 'R':
        cstl = 'g'
      else:
        raise Exception(f'Constellation \'{self.constellation.name}\''\
                          ' not supported in UNAVCO network.')
      return f'{self.name}{gps_day:03}0.{two_year}{cstl}.Z'

    else:
      raise Exception(f'Station type "{self.data_repo}" not supported')

  def get_filedir(self) -> str:
    if self.date_measured == None: 
      raise Exception(f'Date has not been defined for this object: {self.__repr__}')
      
    d = cm.iso_to_dateobj(self.date_measured)
    gps_day = (d - dt.datetime(d.year, 1, 1)).days + 1
    
    base_dir = self.data_repo.value
    base_dir = base_dir[base_dir.find('/'):]  # get string from the first '/'
    
    return f'{base_dir}{d.year}/{gps_day:03}'


class _RinexFile:
  """
    Class for handling RINEX filename manipulation
  """
  def __init__(self, station:StationOptions, local_file='') -> None:
    self.__date = None      # Date of the measurements as datetime object 
    self.__station = None   # Station dataclass object
    self.has_data = False

    self.__setup(station, local_file)

  def __setup(self, station:StationOptions, local_file,) -> None:
    self.set_date(station.date_measured)
    self.__station = station            # TODO[epic=rinex++]: add checking if station is in EPN network

  def setup_from_filename(self, fn: str) -> None:
    # This function is only called when local file exists
    station = StationOptions()

    if len(fn) <= 14:
      # TODO: process UNAVCO (Rinex 2.11)
      pass

    else:
      # Process Rinex 3
      station.name = fn[:4]
      station.country_code = fn[6:9]
      station.data_source = fn [10]

      dt_str = fn[12:23]
      #day = int(dt_str[4:7]) + 1
      #dt_str = dt_str[:4] + f'{day:03}' + dt_str[7:]

      station.date_measured = dt.datetime.strptime(dt_str, "%Y%j%H%M")

      station.resolution = fn[-13:-10]
      station.data_repo = Repo.EPN

      for i in EpnC:
        if i.value == fn[-9:-7]:
          station.constellation = i
          break

    self.__station = station
    self.has_data = True

  def set_date(self, idate) -> None:
    self.__date = cm.iso_to_dateobj(idate) 
    self.has_data = False

  def get_date(self) -> dt.datetime:
    return self.__date

  def set_station(self, station:StationOptions) -> None:
    if station.date_measured != None:
      new_date = cm.iso_to_dateobj(station.date_measured)
      if new_date != self.__date:
        raise Exception('\'date_measured\' property in StationOptions should ONLY be modified with set_date().')
    self.__station = station
    self.has_data = False
  
  def get_station(self) -> StationOptions:
    return self.__station

  def set_cstl(self, cstl: CSTL) -> None:
    self.__station.constellation = cstl

  def get_cstl(self) -> CSTL:
    return self.__station.constellation

  def get_remote_url(self) -> str:
    return self.__station.data_repo.value.split('/')[0]

  def get_remote_dir(self) -> str:
    return self.__station.get_filedir()

  def get_filename(self, station = None) -> str:
    return self.__station.get_filename()

  # Helps with finding the appropriate file
  def get_filename_date(self) -> str:
    if self.__station.data_repo.name == 'EPN':
      return self.get_filename()[12:23]

    elif self.__station.data_repo.name == 'UNAVCO':
      return self.get_filename()[4:10]


@dataclass
class RinexOptions:
  cstls: List[CSTL] = None
  folder_rinex: str = cm.RINEX_FOLDER
  station_params: StationOptions = StationOptions()

class ReaderRinex:
  def __init__(self, r_opts: RinexOptions = RinexOptions()):
    # Dict containing all satellite objects
    self.__sats: Dict[str, _Satellite] = {}

    self.__opts = r_opts
    self.__rinex_obj = None
    self.__is_setup = False
    self.is_mixed = True

  def setup(self, date, cstls: List[CSTL], r_opts:RinexOptions = RinexOptions()):
    # ANCHOR Create rinex file folder if it doesn't exist
    if not os.path.exists(self.__opts.folder_rinex):
      os.mkdir(self.__opts.folder_rinex)

    # Update RinexOptions only if r_opts is not default
    if self.__opts != r_opts and r_opts != RinexOptions():
      self.__opts = r_opts
    self.__opts.station_params.date_measured = date

    # No need to check because calc_manager handles CSTL errors
    self.__opts.cstls = cstls

    self.__rinex_obj = _RinexFile(self.__opts.station_params)

    # ANCHOR Multi-file reading
    if self.__rinex_obj.get_cstl() == CSTL.MIX:
      # Handle downloading files for multiple constellations
      if self.__local_rinex_exist():
        # Mixed file exists
        self.__read_rinex()

      else:
        # Check if the files for required constellation exist
        cstls_are_local = True
        r_temp = copy.deepcopy(self.__rinex_obj)

        for cst in self.__opts.cstls:
          r_temp.set_cstl(cst)
          if not self.__local_rinex_exist(r_temp.get_filename()):
            cstls_are_local = False
            break
        
        if cstls_are_local:
          # They all exists, they are read
          for cst in self.__opts.cstls:
            r_temp.set_cstl(cst)
            self.__read_rinex(r_temp)

        else:
          # Some or all of required files don't exist

          if self.__download_rinex():
            # Read the downloaded mixed file
            self.__read_rinex()
            
          else:
            # Mixed file doesn't exist in repo,
            # download and read indiviual constellation files 
            for cst in self.__opts.cstls:
              r_temp.set_cstl(cst)

              if not self.__download_rinex(r_temp):
                raise Exception(f'{cst.name} constellation not'\
                  f' available for this station: {r_temp.get_station().name}')
              self.__read_rinex(r_temp)
    else:
      # Download a file for a single constellation
      if self.__local_rinex_exist():
        # Single file exists, read it
        self.__read_rinex()

      elif self.__download_rinex():
        # Download and read the constellation file if it exists in repo
        self.__read_rinex()

      else:
        # Download and read the mixed file if it exists
        og = copy.copy(self.__rinex_obj.get_cstl())
        self.__rinex_obj.set_cstl(CSTL.MIX)
        if self.__download_rinex():
          self.__read_rinex()
        else:
          raise Exception(f'{self.__rinex_obj.get_cstl().name}'\
            ' constellation not available for this station:'\
            f' {og.name}')

    if len(self.__sats) == 0:
      raise Exception('No Satellites positions were read.')

    self.__is_setup = True

  def __local_rinex_exist(self, fn:str = None) -> bool:
    if fn == None:
      fn = self.__rinex_obj.get_filename()

    if fn in os.listdir(self.__opts.folder_rinex):
      return True
    return False

  def __download_rinex(self, rinex:_RinexFile = None) -> bool:
    Enable_Debug()
    if rinex == None:
      rinex = self.__rinex_obj
    
    r_url = rinex.get_remote_url()
    r_dir = rinex.get_remote_dir()
    fn  = rinex.get_filename()
    out = self.__opts.folder_rinex + os.sep + fn

  
    with FTPHost(r_url, 'anonymous', 'anonymous') as ftp:
      ftp.chdir(r_dir)

      if ftp.path.exists(fn):
        Info(f'Downloading \'{fn}\'...')
        Debug(1, f'From: {r_url}', nofunc=True)
        
        ftp.download(fn, out)
        rinex.has_data = True
        return True

      else:
        return False

        # Debugging for what files are available for that station
        # stat_name = rinex.get_station().name
        # Info(f'Requested file does not exist: {fn}')
        # Info(f'Files available for {stat_name} station:')
        # mix = False
        # for file in ftp.listdir(ftp.curdir):
        #   if stat_name in file:
        #     Info(f'- {file}')
        #     if EpnC.MIXED.value in file:
        #       mix = True
              
        # Download the mixed file if it exists
        # if mix:
        #   temp = rinex.get_station()
        #   temp.constellation = EpnC.MIXED
        #   rinex.set_station(temp)
        #   fn  = rinex.get_filename()
        #   out = self.__opts.folder_rinex + os.sep + fn
        #   ftp.download(fn, out)
        #   Info(f'Downloaded mixed constellation file \'{fn}\'')
        #   rinex.setup_from_filename(fn)
        #   return True
        # else:
        #   return False

  def __read_rinex(self, rinex: _RinexFile = None):
    Enable_Debug()
    if rinex == None:
      rinex = self.__rinex_obj

    Debug(1,f'Reading Rinex file "{rinex.get_filename()}"...')
    now = time.perf_counter()
    
    # TODO Read only constellations required from FOVs
    cstl = rinex.get_station().constellation.value[0]

    for i in self.__opts.cstls:
      if i.value not in cm.SUPPORTED_CSTLS and cstl != 'M':
        raise Exception(f'Constellation type \'{cstl}\'is not supported')

    nav = None
    fn = rinex.get_filename()
    if cstl == 'M':
      nav = load(self.__opts.folder_rinex + os.sep + fn)
      nav._attrs['svtype'] = ['E','G']
    else:
      nav = load(self.__opts.folder_rinex + os.sep + fn, use=cstl)
      nav._attrs['svtype'] = [cstl]

    date = rinex.get_date().date()

    for n in nav['sv']:
      sat = np.array2string(n).strip('\'')

      # Avoid duplicate entries and unknown constellations
      if '_' in sat or not ('G' in sat or 'E' in sat): continue 

      Debug(2,f'Satellite: {sat}\t date: {date}')

      # Create or add data to Satellite object at date of measurement
      if sat not in self.__sats.keys():
        self.__sats[sat] = _Satellite(sat, date, nav.sel(sv=sat).dropna(dim="time", how="all"))
      elif not self.__sats[sat].has_date(date):
        self.__sats[sat].add_date(date, nav.sel(sv=sat).dropna(dim="time", how="all"))

    Debug(1,f'Done. ({time.perf_counter()-now:.3f}s for {len(self.__sats)} satellites)')
    Debug(1,'')

  def get_sats_pos(self, time_list: List[dt.datetime]):
    Enable_Debug()

    if not self.__is_setup:
      raise Exception('Reader_rinex object has not been setup.')

    Debug(1,f'Extrapolating ({len(self.__sats)}) satellite positions...')

    times = time_list.copy()

    # Convert to datetime objects if time_list is list of str
    if len(times) != 0:
      for i in range(len(times)):
        if type(times[i]) == str:
          times[i] = dt.datetime.fromisoformat(times[i])

    results = {}
    for t in time_list:
        results[t] = {}
    
    for prn in list(self.__sats.keys()):
      Debug(1, f'Extrapolating positions for: {prn}')
      data_array = self.__sats[prn].get_position(times)

      for t in times:
        # TODO[epic=formats, id=time]: make sure that get_sats_pos()'s output time is in the same format as PosData time
        results[t.isoformat(sep=' ')][prn] =  data_array.sel(time=t).values 

    # Output order is:  times{} -> prn{} = (x,y,z)
    return results


class _Satellite:
  def __init__(self, prn: str, date: dt.date, gps_data: Dataset):
    #Enable_Debug(0)
    self.prn = prn
    self.dates = [date]
    self.gps_data = {self.dates[0]: gps_data}
    
    Debug(0, f'Created Satellite object (PRN: {prn})')
    Debug(1, f'svtype: {self.gps_data[self.dates[0]]._attrs["svtype"]}')


  def get_position(self, times: List[dt.datetime] = []):
    #Enable_Debug(1)
    
    if len(times) == 0:
      raise Exception('list of times cannot be empty.')
    mes_date = dt.date(times[0].year, times[0].month, times[0].day)
    #Debug(f'Requesting pos for date: {mes_date}')
    if mes_date not in self.dates:
      raise Exception('Data for this date doesn\'t exist')

    # Select the nearest recorded NAV message 
    close_nav = self.gps_data[mes_date].sel(time=times, method='nearest')

    Debug(1, f'Satellite PRN: {VIOLET}{self.prn}{CEND}')
    Debug(3, f'NAV GPS message from times:')
    for i in close_nav["time"].values:
      Debug(3, f'- {i}')

    Debug(3, f'Requested compute at times:')
    for i in times:
      Debug(3, f'- {i}')

    # Get the time of the NAV message
    td = close_nav["time"].values.astype('datetime64[us]').astype(dt.datetime)

    Debug(1, f'Difference between NAV message and requested times (- before, + after NAV):')
    avg = []
    for i,j in zip(times, td):
      dif = i-j
      if dif < dt.timedelta(days=0):
        Debug(3, f' {GREEN}-{-dif}{CEND}')
        avg.append(-dif)
      else:
        Debug(3, f' {RED}+{dif}{CEND}')
        avg.append(dif)


    # giving datetime.timedelta(0) as the start value makes sum work on tds 
    avg_td = sum(avg, dt.timedelta(0)) / len(avg)
    if avg_td < dt.timedelta(0):
      avg_td = -avg_td
      Debug(1, f'RINEX mean time delta: -{(VIOLET if avg_td < dt.timedelta(hours=4) else RED)}{avg_td}{CEND}')
    else:
      Debug(1, f'RINEX mean time delta: +{(VIOLET if avg_td < dt.timedelta(hours=4) else RED)}{avg_td}{CEND}')

    Debug(3, f'After: {close_nav}')

    if 'G' in self.prn:
      close_nav._attrs['svtype'] = ['G']
    elif 'E' in self.prn:
      close_nav._attrs['svtype'] = ['E']
    else:
      raise Exception('Constellation not supported')

    ecef = keplerian2ecef(close_nav)
    da = DataArray(list(ecef), dims=['space', 'time'], coords=[['x','y','z'], times])
    return da

  def add_date(self, datetime: dt.datetime, gps_data: Dataset):
    if not self.has_date(datetime):
      self.gps_data[datetime.date] = gps_data
    else:
       Debug(1,  f'Data for {datetime.date} already exists.')

  def has_date(self, date: dt.date) -> bool:
    return date in self.gps_data.keys()


if __name__ == '__main__':

  #o = Orbital_data('2019-07-10 07:25:31')
  #o.setup()
  #o.print_data()
  #print("Results:\n",o.get_sats_pos(['2019-07-10 08:25:31', '2019-07-10 14:25:31']))
  #o.get_sats_pos(['2019-07-10 08:25:31', '2019-07-10 14:25:31'])

  r = ReaderRinex()
  r.setup('2019-07-10 07:25:31', [CSTL.GPS, CSTL.GAL])
  print(r.get_sats_pos(['2019-07-10 08:25:31', '2019-07-10 14:25:31']))

# %%
'ftp://data-out.unavco.org/pub/rinex/nav/2021/057/ac070570.21n.Z'
'ftp://data-out.unavco.org/pub/rinex/nav/2021/57/ac70570.21n.Z'