from typing import List, Mapping, Tuple
from pyproj import Transformer
import math
import numpy as np
import datetime as dt

import src.common as c
from src.d_print import Debug, GREEN, RED, VIOLET, CEND

class FOV_model:
  def __init__(self):
    self.is_setup = False

  def setup(self, **args) -> None:
    """
      Sets the constants and values used for calculating FOV in a model
    """
    raise Exception('SubClass.setup() not defined')

  def required_vars(self) -> List[str]:
    """
      Return the variables required to calculate FOV for a model
    """
    raise Exception('SubClass.required_vars() not defined')

  def get_sats(self, pos_data, sats_data) -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
    """
      Return a container with the positions of all
      visible satellites at every given time.\n
      The heirarchy is: {'time': {'prn': (x,y,z) } }
    """
    raise Exception('SubClass.get_sats() not defined')


class FOV_view_match(FOV_model):
  def __init__(self):
    super().__init__()
    # Model calls setup on init as it needs no additional setup
    self.setup()

  def setup(self) -> None:
    """
      FOV_view_match model doesn't require any additional setup.\n
      This method is automatically called on initialization.
    """
    self.is_setup = True

  def required_vars(self) -> List[str]:
    """
      Return the variables required to calculate FOV for this model
    """
    return [c.CHN_LAT, c.CHN_LON, c.CHN_ALT, c.CHN_UTC, c.CHN_SAT]

  def get_sats(self, pos_pos, sats_pos) -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
    """
      Calculate the satellites in view, given the measured amount of
      visible satellites, at every time and place.
    """
    # Sats pos is ordered like:  times{} -> prn{} = (x,y,z)

    # initialize output map
    sats_LOS = {}
    for t in pos_pos[c.CHN_UTC]:
      sats_LOS[t] = {}

    # Go through each timestamp and calculate SVs in FOV
    for i in range(len(pos_pos[c.CHN_UTC])):
      t   = pos_pos[c.CHN_UTC][i] # Timestamps from pos_data
      n_s = int(pos_pos[c.CHN_SAT][i]) # n. of visible sats at 't'

      lat = pos_pos[c.CHN_LAT][i]
      lon = pos_pos[c.CHN_LON][i]
      alt = pos_pos[c.CHN_ALT][i]
      if lon == '0' or lat == '0':
        raise Exception('Positioning data contains \'0\' values, remove them and retry.')
      Debug(2,f' lat: {lat}   lon: {lon}   alt: {alt}')

      u = np.array(c.lla2ecef(lat, lon, alt))
      u = c.normalize(u)

      dots = {}
      # Calculate dot prod to all sats
      for sat in sats_pos[t]:
        p_s = np.array(sats_pos[t][sat])
        p_s = c.normalize(p_s)
        Debug(2,f'dot: {np.dot(u,p_s)}  u: {u}  p_s: {p_s}  sat: {sat}')
        dots[np.dot(u,p_s)] = sat

      # Order in terms of largest abs value
      ordered = sorted(dots.keys(), key=np.abs, reverse=True)

      # Set the n_s most visible satellites as the ones in FOV
      for j in range(n_s):
        dot = ordered[j]
        sat = dots[dot]
        sats_LOS[t][sat] = sats_pos[t][sat]
    
    # sats_LOS is ordered like:  times{} -> prn{} = (x,y,z)
    return sats_LOS

class FOV_constant_mask(FOV_model):
  def __init__(self, mask_angle = -999):
    super().__init__()
    self.m_a = int(mask_angle)/180*math.pi # Mask angle
  
  def setup(self, mask) -> None:
    """
      FOV_constant_mask is setup with a specified mask angle (degrees)
    """
    mask_a = 0

    try:
      mask_a = int(mask)
    except:
      raise Exception('Input mask angle must be convertible to int type')

    if self.m_a != -999:
      Debug(1,f'Changing mask angle: ({self.m_a}) -> ({mask_a})')

    self.m_a = mask_a/180*math.pi
    self.is_setup = True

  def required_vars(self) -> List[str]:
    """
      Return the variables required to calculate FOV for this model
    """
    return [c.CHN_LAT, c.CHN_LON, c.CHN_ALT, c.CHN_UTC]

  def get_sats(self, pos_pos, sats_pos) -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
    """
      Calculate the satellites in view, given the measured amount of
      visible satellites, at every time and place.
    """

    # initialize output map
    sats_LOS = {}
    for t in pos_pos[c.CHN_UTC]:
      sats_LOS[t] = {}

    # Go through each timestamp and calculate SVs in FOV
    for i in range(len(pos_pos[c.CHN_UTC])):
      t   = pos_pos[c.CHN_UTC][i] # Timestamps from pos_data

      lat = float(pos_pos[c.CHN_LAT][i])
      lon = float(pos_pos[c.CHN_LON][i])
      alt = float(pos_pos[c.CHN_ALT][i])

      u = np.array(c.lla2ecef(lat, lon, alt))
      n_u = c.normalize(u)

      """ Calculate threshold point from user location """

      # Angle between user and threshold point
      t_a = math.pi/2 - self.m_a  -\
            math.asin(math.cos(self.m_a) / c.NOM_GPS_RAD \
                      * np.linalg.norm(u))

      # Mask vector length
      m_l = math.sin(t_a)*c.NOM_GPS_RAD/math.sin(self.m_a + math.pi/2)

      # Create user pos projection on ecuatorial plane
      z_ax = np.array([0, 0, 1])
      u_p = u - np.dot(u, z_ax)*z_ax
      u_p = c.normalize(u_p)

      # Angle of the horizon
      h = (lat - 90)/180 * math.pi

      # Create mask vector (from user to threshold point)
      m_v = u_p*math.cos(h + self.m_a) + z_ax*math.sin(h + self.m_a)
      m_v = m_v * m_l


      # Threshold point vector (from ECEF origin to the point)
      p_t = u + m_v
      p_t = c.normalize(p_t)

      threshold = np.dot(n_u, p_t)
      Debug(3,f'Threshold value: {RED}{threshold}{CEND}')

      # Calculate dot prod to all sats
      for sat in sats_pos[t]:
        p_s = np.array(sats_pos[t][sat])
        p_s = c.normalize(p_s)
        d = np.dot(n_u,p_s)
        if d >= threshold:
          sats_LOS[t][sat] = sats_pos[t][sat]
          Debug(3,f'dot for {sat}: {GREEN}{d}{CEND}')
        else:
          Debug(3,f'dot for {sat}: {VIOLET}{d}{CEND}')

    return sats_LOS


class FOV_theoretical_horizon(FOV_model):
  def __init__(self):
    super().__init__()
    # Model calls setup on init as it needs no additional setup
    self.setup()
    raise Exception('Model is not yet usable')
  
  def setup(self, **args) -> None:
    """
      FOV_theoretical_horizon model doesn't require any additional setup.\n
      This method is automatically called on initialization.
    """
    self.is_setup = True

  def required_vars(self) -> List[str]:
    """
      Return the variables required to calculate FOV for this model
    """
    return [c.CHN_LAT, c.CHN_LON, c.CHN_ALT, c.CHN_UTC]

  def get_sats(self, pos_pos, sats_pos) -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
    """
      Calculate the satellites in view, given the measured amount of
      visible satellites, at every time and place.
    """

    # initialize output map
    sats_LOS = {}
    for t in pos_pos[c.CHN_UTC]:
      sats_LOS[t] = {}

    # Go through each timestamp and calculate SVs in FOV
    for i in range(len(pos_pos[c.CHN_UTC])):
      t   = pos_pos[c.CHN_UTC][i] # Timestamps from pos_data

      lat = float(pos_pos[c.CHN_LAT][i])
      lon = float(pos_pos[c.CHN_LON][i])
      alt = float(pos_pos[c.CHN_ALT][i])

      u = np.array(c.lla2ecef(lat, lon, alt))
      n_u = u/np.linalg.norm(u)


      """ Calculate threshold point from user location """

      # Create user pos projection on ecuatorial plane
      z_ax = np.array([0, 0, 1])
      
      u_pz = np.dot(u, z_ax)*z_ax
      u_pz_mag = np.linalg.norm(u_pz)

      u_px = u - u_pz
      u_px_mag = np.linalg.norm(u_px)

      u_pz = u_pz/u_pz_mag  # normalized
      u_px = u_px/u_px_mag  # normalized

      A = u_pz_mag
      B = u_px_mag  
      #Debug(2, f'calc u = {A*u_pz + B*u_px}') # Coords in our plane
      #Debug(2, f'real u = {u}') 

      a = float(c.WGS_A)
      b = float(c.WGS_B)

      b2 = b**2
      a2 = a**2
      a2b2 = a2/b2
      b2a2 = b2/a2
      Debug(-1,f'\nb²  : {b2}\nb2a2: {b2a2}\nmaxx: {b2/b2a2}')

      xa, xb = c.quadratic(A**2 * b2a2**2 + b2a2, -2*b2*b2a2*A, b2**2+b2)
      m1 = - b2a2 * xa/(math.sqrt(b2 - b2a2*(xa**2)))
      m2 = - b2a2 * xb/(math.sqrt(b2 - b2a2*(xb**2)))

      Debug(-1, f'upos inplane = {A},{B}') # Coords in our plane
      Debug(-1, f'xa: {xa}, xb: {xb}, m1: {m1}, m2: {m2}') # Coords in our plane
      #Debug(-1, f'calc tan point = {xa*u_pz + *u_px}') # Coords in our plane

      # Angle of the horizon
      h = (lat - 90)/180 * math.pi




      threshold = 0 #np.dot(n_u, p_t)
      Debug(1,f'Threshold value: {RED}{threshold}{CEND}')

      # Calculate dot prod to all sats
      for sat in sats_pos[t]:
        p_s = np.array(sats_pos[t][sat])
        p_s = p_s/np.linalg.norm(p_s)
        d = np.dot(n_u,p_s)
        if d >= threshold:
          sats_LOS[t][sat] = sats_pos[t][sat]
          Debug(1,f'dot for {sat}: {GREEN}{d}{CEND}')
        else:
          Debug(1,f'dot for {sat}: {VIOLET}{d}{CEND}')

    return sats_LOS