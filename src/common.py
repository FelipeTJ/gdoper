import datetime as d
import typing as t
# Column header names as written in the postioning data csv files
CHN_LAT = 'latitude'
CHN_LON = 'longitude'
CHN_ALT = 'altitude_above_seaLevel(meters)'
CHN_UTC = 'datetime(utc)'
CHN_SAT = 'satellites'

CHN_DEFAULTS = (CHN_LON, CHN_LAT, CHN_ALT, CHN_UTC, CHN_SAT)



# Time intervals for which to calculate GDOP
GDOP_INTERVAL = d.timedelta(seconds=30)

# TODO: write in proper struct format
# Types of GDOP output 
GDOP_ALL = 0
GDOP_ONLY = 1

# Angle from horizon for FOV mask (in degrees)
LOS_ANGLE = 5

# FOV model types
FOV_CONSTANT = 0
FOV_SEGMENTS = 1
FOV_TERRAIN = 2

