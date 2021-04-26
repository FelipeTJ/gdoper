from typing import List, Mapping, Tuple
from numpy import linalg
from pyproj import Transformer
import math
import numpy as np
import datetime as dt

import src.common as cm
from src.d_print import Debug, GREEN, RED, VIOLET, CEND
from decimal import *

class FOV_model:
  def __init__(self):
    self.is_setup = False

  def __str__(self) -> str:
    """
      Return the name of the class
    """
    raise Exception('SubClass.__str__() is not defined.')

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

  def __str__(self) -> str:
      return 'FOV_view_match'

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
    return [cm.CHN_LAT, cm.CHN_LON, cm.CHN_ALT, cm.CHN_UTC, cm.CHN_SAT]

  def get_sats(self, pos_pos, sats_pos) -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
    """
      Calculate the satellites in view, given the measured amount of
      visible satellites, at every time and place.
    """
    if not self.is_setup:
      raise Exception(f'{self.__str__} has not been setup')

    # Sats pos is ordered like:  times{} -> prn{} = (x,y,z)

    # initialize output map
    sats_LOS = {}
    for t in pos_pos[cm.CHN_UTC]:
      sats_LOS[t] = {}

    # Go through each timestamp and calculate SVs in FOV
    for i in range(len(pos_pos[cm.CHN_UTC])):
      t   = pos_pos[cm.CHN_UTC][i] # Timestamps from pos_data
      n_s = int(pos_pos[cm.CHN_SAT][i]) # n. of visible sats at 't'

      lat = pos_pos[cm.CHN_LAT][i]
      lon = pos_pos[cm.CHN_LON][i]
      alt = pos_pos[cm.CHN_ALT][i]
      if lon == '0' or lat == '0':
        raise Exception('Positioning data contains \'0\' values, remove them and retry.')
      Debug(2,f' lat: {lat}   lon: {lon}   alt: {alt}')

      u = np.array(cm.lla2ecef(lat, lon, alt))
      u = cm.normalize(u)

      dots = {}
      # Calculate dot prod to all sats
      for sat in sats_pos[t]:
        s = np.array(sats_pos[t][sat])
        s = cm.normalize(s)
        Debug(2,f'dot: {np.dot(u,s)}  u: {u}  s: {s}  sat: {sat}')
        dots[np.dot(u,s)] = sat

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
    self.m_a = cm.deg2rad(int(mask_angle)) # Mask angle
  
  def __str__(self) -> str:
      return 'FOV_constant_mask'

  def setup(self, mask) -> None:
    """
      FOV_constant_mask is setup with a specified mask angle (degrees)
    """
    mask_a = 0

    try:
      mask_a = int(mask)
    except:
      raise Exception('Input mask angle must be convertible to int type')

    if self.m_a != cm.deg2rad(-999):
      Debug(1,f'Changing mask angle: ({cm.rad2deg(self.m_a)}º) -> ({mask_a}º)')

    self.m_a = cm.deg2rad(mask_a)
    self.is_setup = True

  def required_vars(self) -> List[str]:
    """
      Return the variables required to calculate FOV for this model
    """
    return [cm.CHN_LAT, cm.CHN_LON, cm.CHN_ALT, cm.CHN_UTC]

  def get_sats(self, pos_pos, sats_pos) -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
    """
      Calculate the satellites in view, given the measured amount of
      visible satellites, at every time and place.
    """
    if not self.is_setup:
      raise Exception(f'{self.__str__} has not been setup')

    # initialize output map
    sats_LOS = {}
    for t in pos_pos[cm.CHN_UTC]:
      sats_LOS[t] = {}

    # Go through each timestamp and calculate SVs in FOV
    for i in range(len(pos_pos[cm.CHN_UTC])):
      t   = pos_pos[cm.CHN_UTC][i] # Timestamps from pos_data

      lat = float(pos_pos[cm.CHN_LAT][i])
      lon = float(pos_pos[cm.CHN_LON][i])
      alt = float(pos_pos[cm.CHN_ALT][i])

      u = np.array(cm.lla2ecef(lat, lon, alt))
      n_u = u/np.linalg.norm(u)

      """ Calculate threshold point from user location """

      # Angle between user and threshold point
      th_a = math.pi/2 - self.m_a  -\
            math.asin(math.cos(self.m_a) / cm.NOM_GPS_RAD \
                      * np.linalg.norm(u))

      # # Mask vector length
      # m_l = math.sin(th_a)*c.NOM_GPS_RAD/math.sin(self.m_a + math.pi/2)

      # # Create user pos projection on ecuatorial plane
      # z_ax = np.array([0, 0, 1])
      # u_p = u - np.dot(u, z_ax)*z_ax
      # u_p = c.normalize(u_p)

      # # Angle of the horizon
      # h = (lat - 90)/180 * math.pi

      # # Create mask vector (from user to threshold point)
      # m_v = u_p*math.cos(h + self.m_a) + z_ax*math.sin(h + self.m_a)
      # m_v = m_v * m_l


      # # Threshold point vector (from ECEF origin to the point)
      # th_v = u + m_v
      # th_v = c.normalize(th_v)

      threshold = math.cos(th_a) #np.dot(n_u, th_v)
      Debug(2,f'Threshold value: {RED}{threshold}{CEND}')

      # Calculate dot prod to all sats
      for sat in sats_pos[t]:
        s = np.array(sats_pos[t][sat])
        d = np.dot(n_u, s/np.linalg.norm(s))
        if d >= threshold:
          sats_LOS[t][sat] = sats_pos[t][sat]
          Debug(3,f'dot for {sat}: {GREEN}{d}{CEND}')
        else:
          Debug(3,f'dot for {sat}: {VIOLET}{d}{CEND}')

    return sats_LOS


class FOV_treeline(FOV_model):
  def __init__(self, max_mask:int = -999, tree_height:float = -999, min_mask:int = 5):
    super().__init__()
    self.mx_m_a = cm.deg2rad(max_mask)
    self.tl_h = tree_height
    self.mn_m_a = cm.deg2rad(min_mask)
  
  def __str__(self) -> str:
      return 'FOV_treeline'

  def setup(self, max_mask=15, tree_line=20, min_mask:int = 5) -> None:
    """
      FOV_theoretical_horizon model doesn't require any additional setup.\n
      This method is automatically called on initialization.
    """
    mask_a = 0
    mask_m = 0
    tree_h = 0

    try:
      mask_a = int(max_mask)
      mask_m = int(min_mask)
    except:
      raise Exception('Input mask angle must be convertible to int type')

    if mask_a < mask_m:
      raise Exception(f'The MAXimum mask angle ({mask_a})\
         cannot be smaller than the MINimum mask angle ({mask_m})')

    if self.mx_m_a != cm.deg2rad(-999) and self.mx_m_a != cm.deg2rad(mask_a):
      Debug(1,f'Changing max mask angle: ({cm.rad2deg(self.mx_m_a)}º) -> ({mask_a}º)')

    self.mx_m_a = cm.deg2rad(mask_a)

    if self.mn_m_a != cm.deg2rad(5) and self.mn_m_a != cm.deg2rad(mask_m):
      Debug(1,f'Changing min mask angle: ({cm.rad2deg(self.mn_m_a)}º) -> ({mask_m}º)')

    self.mn_m_a = cm.deg2rad(mask_m)

    try:
      tree_h = float(tree_line)
    except:
      raise Exception('Input tree line height must be convertible to float type')

    if self.mx_m_a != -999 and self.tl_h != tree_h:
      Debug(1,f'Changing tree line height: ({self.tl_h}m) -> ({tree_h}m)')

    self.is_setup = True

  def required_vars(self) -> List[str]:
    """
      Return the variables required to calculate FOV for this model
    """
    return [cm.CHN_LAT, cm.CHN_LON, cm.CHN_ALT, cm.CHN_UTC]

  def get_sats(self, pos_pos, sats_pos) -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
    """
      Calculate the satellites in view, given the measured amount of
      visible satellites, at every time and place.
    """
    if not self.is_setup:
      raise Exception(f'{self.__str__} has not been setup')

    # initialize output map
    sats_LOS = {}
    for t in pos_pos[cm.CHN_UTC]:
      sats_LOS[t] = {}

    # Minimum height
    mins = [float(i) for i in pos_pos[cm.CHN_ALT]]
    i_h = min(mins)

    mask = self.mx_m_a

    # Go through each timestamp and calculate SVs in FOV
    for i in range(len(pos_pos[cm.CHN_UTC])):
      t   = pos_pos[cm.CHN_UTC][i] # Timestamps from pos_data

      lat = float(pos_pos[cm.CHN_LAT][i])
      lon = float(pos_pos[cm.CHN_LON][i])
      alt = float(pos_pos[cm.CHN_ALT][i])

      u = np.array(cm.lla2ecef(lat, lon, alt))
      n_u = u/np.linalg.norm(u)


      """ Calculate threshold point from user location """

      # Create user pos projection on ecuatorial plane
      z_ax = np.array([0, 0, 1])
      
      u_pz = np.dot(u,z_ax)*z_ax
      Debug(2,f'u_pz: {u_pz}')
      u_pz_mag = np.linalg.norm(u_pz)

      u_px = u - u_pz
      u_px_mag = np.linalg.norm(u_px)

      u_pz = u_pz/u_pz_mag  # normalized
      u_px = u_px/u_px_mag  # normalized

      c = u_px_mag
      d = u_pz_mag  

      Debug(2, f'proj u = {u_px}  {u_pz}') # Coords in our plane
      Debug(2, f'mags u = {u_px_mag}  {u_pz_mag}') # Coords in our plane
      Debug(2, f'calc u = {c*u_px + d*u_pz}') # Coords in our plane
      Debug(2, f'real u = {u}') 

      a = float(cm.WGS_A) + i_h
      b = float(cm.WGS_B) + i_h

      a2 = a*a
      b2 = b*b

      c2 = c*c
      d2 = d*d

      under = False

      e = c2/a2 + d2/b2 -1

      x1 = (c + d*a/b*math.sqrt(e) )/(e + 1)
      x2 = (c - d*a/b*math.sqrt(e) )/(e + 1)

      y1 = (d - c*b/a*math.sqrt(e) )/(e + 1)
      y2 = (d + c*b/a*math.sqrt(e) )/(e + 1)

      m1 = math.atan((y1-d)/(x1-c))*180/math.pi
      m2 = math.atan((y2-d)/(x2-c))*180/math.pi

      Debug(0, f'')
      Debug(2, f'a : {a:>15.0f}\tb : {b:>15.0f}')
      Debug(2, f'c : {c:>15.0f}\td : {d:>15.0f}')
      Debug(1, f'x1: {x1:>15.0f}\ty1: {y1:>15.0f}')
      Debug(2, f'x2: {x2:>15.0f}\ty2: {y2:>15.0f}')
      Debug(1, f'm1: {m1:>5.10f}\tm2: {m2:>5.10f}')
      Debug(0, f'lat: {lat} 90-lat: {lat-90}')

      tree_line = 20

      if alt < i_h + tree_line:
        h_d = (alt - i_h)/ tree_line
        m_d = (self.mx_m_a - self.mn_m_a)*h_d 
        mask = self.mx_m_a - m_d
      else:
        mask = self.mn_m_a


      # Angle of the horizon
      d_a = math.pi/2 - cm.deg2rad(lat)- cm.deg2rad((np.abs(m2) if under else np.abs(m1))) + mask

      th_a = math.pi/2 - d_a  -\
            math.asin(math.cos(d_a) / cm.NOM_GPS_RAD \
                      * np.linalg.norm(u))

      threshold = math.cos(th_a) #np.dot(n_u, p_t)
      
      Debug(0, f'')
      Debug(1, f'           date: {t}')
      Debug(1, f'           mask: {cm.rad2deg(mask)}')
      Debug(1, f'            alt: {alt}')
      Debug(1, f'Threshold angle: {VIOLET}{cm.rad2deg(th_a):.4f}{CEND}')
      Debug(1, f'Threshold value: {RED}{threshold:.4f}{CEND}')

      # Calculate dot prod to all sats
      for sat in sats_pos[t]:
        p_s = np.array(sats_pos[t][sat])
        p_s = p_s/np.linalg.norm(p_s)
        d = np.dot(n_u,p_s)
        if d >= threshold:
          sats_LOS[t][sat] = sats_pos[t][sat]
          Debug(0,f'dot for {sat}:     {GREEN}{d:.4f}{CEND}')
        else:
          Debug(2,f'dot for {sat}:     {VIOLET}{d:.4f}{CEND}')
      Debug(1, f'sats in view: {GREEN}{len(sats_LOS[t])}{CEND}')


    return sats_LOS