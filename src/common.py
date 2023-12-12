from pyproj.transformer import Transformer
from pathlib import Path
import datetime as d
import typing as t
import os

BASE_FOLDER = Path(__file__).resolve().parent.parent
RINEX_FOLDER = Path(BASE_FOLDER / 'rinex_files')
POS_DATA_FOLDER = Path(BASE_FOLDER / 'test_data')

if not os.path.isdir(RINEX_FOLDER):
    os.mkdir(RINEX_FOLDER)

# WGS84 constants
# TODO: put them here?


# Column header names as written in the postioning data csv files
CHN_LAT = 'latitude'
CHN_LON = 'longitude'
CHN_ALT = 'altitude_above_seaLevel(meters)'
CHN_UTC = 'datetime(utc)'
CHN_SAT = 'satellites'

CHN_DEFAULTS = (CHN_LON, CHN_LAT, CHN_ALT, CHN_UTC, CHN_SAT)



# Time intervals for which to calculate GDOP
GDOP_INTERVAL = d.timedelta(seconds=2)

# TODO: write in proper struct format
# Types of GDOP output 
GDOP_ALL = 0
GDOP_ONLY = 1

# Angle from horizon for FOV mask (in degrees)
LOS_ANGLE = 5


# Functions

def lla2ecef(lat, lon, alt) -> tuple:
  # https://epsg.io/4978 and http://epsg.io/4979
  # WGS84 lat,lon,alt    and WGS84 ECEF
  t = Transformer.from_crs("epsg:4979", "epsg:4978")
  return (t.transform(lat, lon, alt))