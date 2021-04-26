#%%

from typing import Tuple, List
import numpy as np
from numpy.core.fromnumeric import trace
import src.common as cm

class Calc:
  def __init__(self):
    self.is_setup = False
    pass

  def get_chn(self) -> List[str]:
    pass

  def required_vars(self) -> List[str]:
    pass

  def do_calc(self, sampled_pos, sats_FOV) -> Tuple[str, list]:
    # Expected sats_FOV heirarchy is:  time{} -> prn{} -> (x,y,z)
    # Expected sampled_pos order is :  chn{} -> data[]
    pass


class Calc_gdop(Calc):
  def __init__(self):
    super().__init__()
    pass

  def get_chn(self) -> List[str]:
    return ['HDOP', 'VDOP', 'GDOP']

  def required_vars(self) -> List[str]:
    return [cm.CHN_UTC, cm.CHN_LAT, cm.CHN_LON, cm.CHN_ALT]

  def do_calc(self, pos_pos, sats_FOV) -> Tuple[str, list]:
    # sats_FOV is ordered like:  times{} -> prn{} = (x,y,z)
    fov_name = 'sats_FOV' # TODO: proper implemenmtation comes with linkning of Calc to FOVmodel 

    results = {'HDOP': [], 'VDOP': [], 'GDOP': [], fov_name:[]}  # TODO: Add unique calculation signature to names

    for i in range(len(pos_pos[cm.CHN_UTC])):
      t = pos_pos[cm.CHN_UTC][i]

      lat = pos_pos[cm.CHN_LAT][i]
      lon = pos_pos[cm.CHN_LON][i]
      alt = pos_pos[cm.CHN_ALT][i]

      u = np.array(cm.lla2ecef(lat, lon, alt))

      mat: np.array = []

      # Add visible satellites to LOS matrix
      for j in sats_FOV[t]:
        sat_pos = sats_FOV[t][j]                # tuple, ECEF coord of a sat
        d = lambda ax: sat_pos[ax] - u[ax]      # float, axis value difference (x=0, y=1, z=2)
        psd = np.sqrt(d(0)**2 + d(1)**2 + d(2)**2)    # pseudo range from receiver to sat
        m_row = [-d(0)/psd, -d(1)/psd, -d(2)/psd, 1]  # Row in GDOP matrix
        mat.append(m_row)

      m = np.matmul(np.transpose(mat), mat)
      Q = np.linalg.inv(m)
      T = [Q[0][0], Q[1][1], Q[2][2], Q[3][3]]
      hdop = np.sqrt(T[0]**2 + T[1]**2)
      
      results[fov_name].append(len(mat))
      results['HDOP'].append(hdop)
      results['VDOP'].append(T[2])
      results['GDOP'].append(np.sqrt(np.trace(Q)))
    
    return results
