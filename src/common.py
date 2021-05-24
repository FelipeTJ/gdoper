from pyproj.transformer import Transformer
import datetime as d
import numpy as np
import math
import os
from enum import Enum


############################ Calculation constants ############################

# WGS84 constants
WGS_A = 6378137
WGS_B = 6356752.314245179

NOM_GPS_RAD = 26600000  # in meters



######################## File and dir name constants ##########################

G_SUFFIX = '_gdoper'

BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))[:-4]
RINEX_FOLDER = BASE_FOLDER + os.sep + 'rinex_files'
POS_DATA_FOLDER = BASE_FOLDER + os.sep + 'test_data'

# Column header names as written in the postioning data csv files
# (CHN for user provided data)
CHN_LAT = 'latitude'
CHN_LON = 'longitude'
CHN_ALT = 'altitude_above_seaLevel(meters)'
CHN_UTC = 'datetime(utc)'
CHN_SAT = 'satellites'

CHN_DEFAULTS = (CHN_LON, CHN_LAT, CHN_ALT, CHN_UTC, CHN_SAT)


########################## Implementation constants ###########################

SUPPORTED_CSTLS = ['G', 'GN', 'GPS', 'E', 'EN', 'GAL']

# Constellation satellite prn id
class CSTL(Enum):
    GPS = 'G'
    GLO = 'R'
    GAL = 'E'
    QZS = 'J'
    BDS = 'C'
    SBS = 'S'
    MIX = 'M'
    NONE = ''


NO_CSTL = CSTL.NONE
NO_ANGLE = -999


############################## Common Functions ###############################

def iso_to_dateobj(date_str) -> d.datetime:
    # TODO: use proper ISO-8601 parsing
    date = d.datetime.fromisoformat(date_str)
    return date


def lla2ecef(lat, lon, alt) -> tuple:
    # https://epsg.io/4978 and http://epsg.io/4979
    # WGS84 lat,lon,alt    and WGS84 ECEF
    t = Transformer.from_crs("epsg:4979", "epsg:4978")
    return (t.transform(lat, lon, alt))


def ecef2lla(x, y, z):
    # https://epsg.io/4978 and http://epsg.io/4979
    # WGS84 lat,lon,alt    and WGS84 ECEF
    t = Transformer.from_crs("epsg:4978", "epsg:4979")
    return (t.transform(x, y, z))


def rad2deg(n):
    return n*180/math.pi


def deg2rad(n):
    return n*math.pi/180


def quadratic(a, b, c) -> tuple:
    disc = b**2 - 4*a*c
    if disc < 0:
        raise Exception('Discriminant is negative (a:{a}, b:{b}, c:{c})')
    first = -b/(2*a)
    sec = np.sqrt(disc)
    return (first+sec, first-sec)
