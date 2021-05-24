from typing import List, Mapping, Tuple
from numpy import linalg
from pyproj import Transformer
import math
import numpy as np
import datetime as dt

import src.common as cm
from src.common import CSTL
from src.calcs import Calc, Calc_gdop
from src.d_print import Debug, Enable_Debug, GREEN, RED, VIOLET, CEND


class FOV_model:
  def __init__(self):
    self.calcs: List[Calc]  = []
    self.cstls: List[CSTL]  = []
    self.cstls_initials: List[str] = []

    self.is_setup:  bool    = False
    self.in_view: Mapping[str, Mapping[str, Tuple[float, float, float]]] = {}

  def __repr__(self) -> str:
      return f"{self.__str__()} with signature: {self.__sign},"\
             f" constellations: {self.cstls}, calcs: {self.calcs}"

  def is_in_cstls(self, sat) -> bool:
    return sat[0] in self.cstls_initials

  def add_cstls(self, cstls: List[cm.CSTL]) -> None:
    if len(cstls) == 0:
      raise Exception('Input constellation list cannot be empty.')
    
    if cm.CSTL.NONE in cstls:
      raise Exception('CSTL.NONE cannot be used.')

    self.cstls = cstls
    self.cstls_initials = [i.value[0] for i in cstls]

  def add_calc(self, calc) -> None:
    if calc == Calc():
      raise Exception("Calc cannot be used as a calculation.\
                        Select an inherited class.")

    if calc not in self.calcs:
      self.calcs.append(calc)

  def do_calcs(self, sampled_pos):
    """
      Perform the calculations based on the FOV model
    """
    raise Exception('SubClass.do_calcs() is not defined.')

  def __str__(self) -> str:
    """
      Return the name of the class
    """
    raise Exception('SubClass.__str__() is not defined.')

  def __sign(self) -> str:
    """
      Return the signature of the class
    """
    raise Exception('SubClass.__sign() is not defined.')

  def setup(self, **args) -> None:
    """
      Sets the constants and values used for calculating FOV in a model
    """
    raise Exception('SubClass.setup() not defined')

  def required_vars(self) -> set:
    """
      Return the variables required to calculate FOV for a model
    """
    raise Exception('SubClass.required_vars() not defined')

  def get_sats(self, pos_data, sats_data) \
              -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
    """
      Return a container with the positions of all
      visible satellites at every given time.\n
      The heirarchy is: {'time': {'prn': (x,y,z) } }
    """
    raise Exception('SubClass.get_sats() not defined')

class FOV_empty(FOV_model):

  _fovID = 0

  def __init__(self):
    super().__init__()

    # Count class instances
    self.id = FOV_empty._fovID
    FOV_empty._fovID += 1      
  
  def __str__(self) -> str:
      return 'FOV_empty'

  def __sign(self) -> str:
      return f'_empty{str(self.id) if self.id != 0 else ""}'

  def setup(self) -> None:
    self.is_setup = True

  def required_vars(self) -> set:
      return {cm.CHN_LAT, cm.CHN_LON, cm.CHN_ALT, cm.CHN_UTC}

  def get_sats(self, pos_data, sats_data) \
              -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
      return super().get_sats(pos_data, sats_data)

class FOV_view_match(FOV_model):

  _fovID = 0

  def __init__(self, cstls: List[CSTL] = []):
    super().__init__()
    self.cstls = []

    if len(cstls) != 0:
      self.add_cstls(cstls)
      self.is_setup = True

    # Count class instances
    self.id = FOV_view_match._fovID
    FOV_view_match._fovID += 1    

  def __str__(self) -> str:
      return 'FOV_view_match'

  def __sign(self) -> str:
      return f'_match{str(self.id) if self.id != 0 else ""}'

  def do_calcs(self, sampled_pos):
    out = {}
    for i in self.calcs:
      i.sign = self.__sign()
      out.update(i.do_calc(sampled_pos, self.in_view))
    return out

  def setup(self, cstls: List[CSTL] = [CSTL.GPS]) -> None:
    """
      Constelation that is reportedly seen should be defined here
    """
    self.add_cstls(cstls)
    self.is_setup = True

  def required_vars(self) -> set:
    """
      Return the variables required to calculate FOV for this model
    """
    return {cm.CHN_LAT, cm.CHN_LON, cm.CHN_ALT, cm.CHN_UTC, cm.CHN_SAT} # TODO: Add variables required from calcs

  def get_sats(self, pos_pos, sats_pos) \
              -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
    """
      Calculate the satellites in view, given the measured amount of
      visible satellites, at every time and place.
    """
    if not self.is_setup:
      raise Exception(f'{self.__str__} has not been setup')

    Enable_Debug()
    Debug(1, f'Calculating FOV using: {self.__str__()}')

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
      Debug(2 ,f' lat: {lat}   lon: {lon}   alt: {alt}')

      u = np.array(cm.lla2ecef(lat, lon, alt))
      u = u/np.linalg.norm(u)

      dots = {}
      # Calculate dot prod to all sats of given constellation
      for sat in sats_pos[t]:
        if not self.is_in_cstls(sat): continue
        s = np.array(sats_pos[t][sat])
        s = s/np.linalg.norm(s)
        Debug(3,f'dot: {np.dot(u,s)}  u: {u}  s: {s}  sat: {sat}')
        dots[np.dot(u,s)] = sat

      # Order in terms of largest value
      ordered = sorted(dots.keys(), reverse=True)

      # Set the n_s most visible satellites as the ones in FOV
      for j in range(n_s):
        dot = ordered[j]
        sat = dots[dot]
        Debug(2, f'In view: {GREEN}{sat}{CEND} dot: {dot}')
        sats_LOS[t][sat] = sats_pos[t][sat]
    
    # sats_LOS is ordered like:  times{} -> prn{} = (x,y,z)
    self.in_view = sats_LOS
    return sats_LOS

class FOV_constant_mask(FOV_model):

  _fovID = 0

  def __init__(self, mask_angle = cm.NO_ANGLE, cstls: List[CSTL] = []):
    super().__init__()
    self.cstls = []

    if len(cstls) != 0:
      self.add_cstls(cstls)

    # Count class instances
    self.id = FOV_constant_mask._fovID
    FOV_constant_mask._fovID += 1    

    self.m_a = cm.deg2rad(int(mask_angle)) # Mask angle
    self.th_calc = lambda u, *args: self.__get_threshold(u, *args)
    self.sv2th_calc = lambda s, *args: self.__get_value(s, *args)

    if mask_angle != cm.NO_ANGLE and len(cstls) != 0:
      self.is_setup = True
  
  def __str__(self) -> str:
      return 'FOV_constant_mask'

  def __sign(self) -> str:
      return f'_constm{str(self.id) if self.id != 0 else ""}'

  def do_calcs(self, sampled_pos):
    out = {}
    for i in self.calcs:
      i.sign = self.__sign()
      out.update(i.do_calc(sampled_pos, self.in_view))
    return out

  def setup(self, mask, cstls: List[CSTL] = [CSTL.GPS]) -> None:
    """
      FOV_constant_mask is setup with a specified mask angle (degrees)
    """
    mask_a = 0

    try:
      mask_a = int(mask)
    except:
      raise Exception('Input mask angle must be convertible to int type')

    if self.m_a != cm.deg2rad(cm.NO_ANGLE):
      Debug(1,f'Changing mask angle: ({cm.rad2deg(self.m_a)}º) -> ({mask_a}º)')

    self.m_a = cm.deg2rad(mask_a)
    self.cstls = cstls
    self.is_setup = True

  def required_vars(self) -> set:
    """
      Return the variables required to calculate FOV for this model
    """
    return {cm.CHN_LAT, cm.CHN_LON, cm.CHN_ALT, cm.CHN_UTC}

  def __get_threshold(self, u, *args):
    th_a = math.pi/2 - self.m_a  -\
            math.asin(math.cos(self.m_a) / cm.NOM_GPS_RAD \
                      * np.linalg.norm(u))
    return math.cos(th_a)

  def __get_value(self, sat_pos, normalized_u, *args):
    return np.dot(normalized_u, sat_pos/np.linalg.norm(sat_pos))

  def get_sats(self, pos_pos, sats_pos) \
              -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
    """
      Calculate the satellites in view, given the measured amount of
      visible satellites, at every time and place.
    """ 
    if not self.is_setup:
      raise Exception(f'{self.__str__} has not been setup')
    
    Enable_Debug()
    Debug(1, f'Calculating FOV using: {self.__str__()}')

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

      threshold = self.th_calc(u, lat)
      Debug(2,f'Threshold value: {RED}{threshold}{CEND}')

      # Calculate dot prod to all sats
      for sat in sats_pos[t]:
        if not self.is_in_cstls(sat): continue
        s = np.array(sats_pos[t][sat])
        d = self.sv2th_calc(s, n_u, u)
        if d >= threshold:
          sats_LOS[t][sat] = sats_pos[t][sat]
          Debug(3,f'dot for {sat}: {GREEN}{d}{CEND}')
        else:
          Debug(3,f'dot for {sat}: {VIOLET}{d}{CEND}')

    self.in_view = sats_LOS
    return sats_LOS

class FOV_constant_mask_old(FOV_constant_mask):
  def __init__(self, mask_angle=cm.NO_ANGLE):
    super().__init__(mask_angle=mask_angle)
    
  def __str__(self) -> str:
      return 'FOV_constant_mask_old'

  def __get_threshold(self, u, lat, *args):
    #Angle between user and threshold point
    th_a = math.pi/2 - self.m_a  -\
          math.asin(math.cos(self.m_a) / cm.NOM_GPS_RAD \
                    * np.linalg.norm(u))

    # Mask vector length
    m_l = math.sin(th_a)*cm.NOM_GPS_RAD/math.sin(self.m_a + math.pi/2)

    # Create user pos projection on ecuatorial plane
    z_ax = np.array([0, 0, 1])
    u_p = u - np.dot(u, z_ax)*z_ax
    u_p = cm.normalize(u_p)

    # Angle of the horizon
    h = (lat - 90)/180 * math.pi

    # Create mask vector (from user to threshold point)
    m_v = u_p*math.cos(h + self.m_a) + z_ax*math.sin(h + self.m_a)
    m_v = m_v * m_l


    # Threshold point vector (from ECEF origin to the point)
    th_v = u + m_v
    th_v = cm.normalize(th_v)
    return np.dot(cm.normalize(u), th_v)

class FOV_constant_mask2(FOV_constant_mask):
  def __init__(self):
    super().__init__()
  
  def __str__(self) -> str:
    return 'FOV_constant_mask2'

  def __get_threshold(self, u, *args):
    return self.m_a

  def __get_value(self, sat_pos, n_u, u, *args):
    n = sat_pos - u
    n = n/np.linalg.norm(n)

    return math.acos(np.dot(n_u, n))

class FOV_treeline(FOV_model):

  _fovID = 0

  def __init__(self,
              max_mask:int = cm.NO_ANGLE,
              tree_height:float = 20, 
              min_mask:int = 5, 
              cstls: List[CSTL] = []):
    super().__init__()
    self.cstls = []

    if len(cstls) != 0:
      self.add_cstls(cstls)

    # Count class instances
    self.id = FOV_treeline._fovID
    FOV_treeline._fovID += 1    

    self.mx_m_a = cm.deg2rad(max_mask)
    self.tl_h = tree_height
    self.mn_m_a = cm.deg2rad(min_mask)

    if max_mask != cm.NO_ANGLE and len(cstls) != 0:
      self.is_setup = True
  
  def __str__(self) -> str:
      return 'FOV_treeline'

  def __sign(self) -> str:
      return f'_tree{str(self.id) if self.id != 0 else ""}'

  def do_calcs(self, sampled_pos):
    out = {}
    for i in self.calcs:
      i.sign = self.__sign()
      out.update(i.do_calc(sampled_pos, self.in_view))
    return out

  def setup(self, 
            max_mask=15,
            tree_line=20,
            min_mask:int = 10, 
            cstls: List[CSTL] = [CSTL.GPS]) -> None:
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

    if self.mx_m_a != cm.deg2rad(cm.NO_ANGLE) \
      and self.mx_m_a != cm.deg2rad(mask_a):
      Debug(1,f'Changing max mask angle: ({cm.rad2deg(self.mx_m_a)}º) -> ({mask_a}º)')

    self.mx_m_a = cm.deg2rad(mask_a)

    if self.mn_m_a != cm.deg2rad(5) and self.mn_m_a != cm.deg2rad(mask_m):
      Debug(1,f'Changing min mask angle: ({cm.rad2deg(self.mn_m_a)}º) -> ({mask_m}º)')

    self.mn_m_a = cm.deg2rad(mask_m)

    try:
      tree_h = float(tree_line)
    except:
      raise Exception('Input tree line height must be convertible to float type')

    if self.mx_m_a != cm.NO_ANGLE and self.tl_h != tree_h:
      Debug(1,f'Changing tree line height: ({self.tl_h}m) -> ({tree_h}m)')
      self.tl_h = tree_h

    self.cstls = cstls
    self.is_setup = True

  def required_vars(self) -> set:
    """
      Return the variables required to calculate FOV for this model
    """
    return {cm.CHN_LAT, cm.CHN_LON, cm.CHN_ALT, cm.CHN_UTC}

  def get_sats(self, pos_pos, sats_pos) \
              -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
    """
      Calculate the satellites in view, given the measured amount of
      visible satellites, at every time and place.
    """
    if not self.is_setup:
      raise Exception(f'{self.__str__} has not been setup')

    Enable_Debug()
    Debug(1, f'Calculating FOV using: {self.__str__()}')

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
      Debug(3,f'u_pz: {u_pz}')
      u_pz_mag = np.linalg.norm(u_pz)

      u_px = u - u_pz
      u_px_mag = np.linalg.norm(u_px)

      u_pz = u_pz/u_pz_mag  # normalized
      u_px = u_px/u_px_mag  # normalized

      c = u_px_mag
      d = u_pz_mag  

      Debug(3, f'proj u = {u_px}  {u_pz}') # Coords in our plane
      Debug(3, f'mags u = {u_px_mag}  {u_pz_mag}') # Coords in our plane
      Debug(3, f'calc u = {c*u_px + d*u_pz}') # Coords in our plane
      Debug(3, f'real u = {u}') 

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

      Debug(3, f'')
      Debug(3, f'a : {a:>15.0f}\tb : {b:>15.0f}')
      Debug(3, f'c : {c:>15.0f}\td : {d:>15.0f}')
      Debug(3, f'x1: {x1:>15.0f}\ty1: {y1:>15.0f}')
      Debug(3, f'x2: {x2:>15.0f}\ty2: {y2:>15.0f}')
      Debug(3, f'm1: {m1:>5.10f}\tm2: {m2:>5.10f}')
      Debug(3, f'lat: {lat} 90-lat: {lat-90}')

      tree_line = 20

      if alt < i_h + tree_line:
        h_d = (alt - i_h)/ tree_line
        m_d = (self.mx_m_a - self.mn_m_a)*h_d 
        mask = self.mx_m_a - m_d
      else:
        mask = self.mn_m_a


      # Angle of the horizon
      d_a = math.pi/2 - cm.deg2rad(lat) \
            - cm.deg2rad((np.abs(m2) if under else np.abs(m1))) + mask

      th_a = math.pi/2 - d_a  -\
            math.asin(math.cos(d_a) / cm.NOM_GPS_RAD \
                      * np.linalg.norm(u))

      threshold = math.cos(th_a) #np.dot(n_u, p_t)
      
      Debug(3, f'')
      Debug(3, f'           date: {t}')
      Debug(3, f'           mask: {cm.rad2deg(mask)}')
      Debug(3, f'            alt: {alt}')
      Debug(3, f'Threshold angle: {VIOLET}{cm.rad2deg(th_a):.4f}{CEND}')
      Debug(3, f'Threshold value: {RED}{threshold:.4f}{CEND}')

      # Calculate dot prod to all sats
      for sat in sats_pos[t]:
        if not self.is_in_cstls(sat): continue
        p_s = np.array(sats_pos[t][sat])
        p_s = p_s/np.linalg.norm(p_s)
        d = np.dot(n_u,p_s)
        if d >= threshold:
          sats_LOS[t][sat] = sats_pos[t][sat]
          Debug(3,f'dot for {sat}:     {GREEN}{d:.4f}{CEND}')
        else:
          Debug(3,f'dot for {sat}:     {VIOLET}{d:.4f}{CEND}')
      Debug(2, f'sats in view: {GREEN}{len(sats_LOS[t])}{CEND}')

    self.in_view = sats_LOS
    return sats_LOS