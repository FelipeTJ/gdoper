from pyproj.transformer import Transformer
import datetime as d
import typing as t
import numpy as np
import math
import os

BASE_FOLDER = os.path.dirname(os.path.abspath(__file__) )[:-4]
RINEX_FOLDER = BASE_FOLDER + os.sep + 'rinex_files'
POS_DATA_FOLDER = BASE_FOLDER + os.sep + 'test_data'

GDOPER_SUFFIX = '_gdoper'


# WGS84 constants
WGS_A = 6378137
WGS_B = 6356752.314245179


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

NOM_GPS_RAD = 26600000  # in meters


# Functions

def lla2ecef(lat, lon, alt) -> tuple:
  # https://epsg.io/4978 and http://epsg.io/4979
  # WGS84 lat,lon,alt    and WGS84 ECEF
  t = Transformer.from_crs("epsg:4979", "epsg:4978")
  return (t.transform(lat, lon, alt))

def ecef2lla(x,y,z):
  # https://epsg.io/4978 and http://epsg.io/4979
  # WGS84 lat,lon,alt    and WGS84 ECEF
  t = Transformer.from_crs("epsg:4978","epsg:4979")
  return (t.transform(x, y, z))

def rad2deg(n):
  return n*180/math.pi

def deg2rad(n):
  return n*math.pi/180

def normalize(vector: np.array) -> np.array:
  return vector/np.linalg.norm(vector)

def quadratic(a,b,c) -> tuple:
  disc = b**2 - 4*a*c
  if disc < 0:
    raise Exception('Discriminant is negative (a:{a}, b:{b}, c:{c})')
  first = -b/(2*a)
  sec = np.sqrt(disc)
  return (first+sec, first-sec)