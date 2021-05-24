#%%

from typing import Dict, List
import numpy as np
from numpy.core.fromnumeric import trace
from src.common import lla2ecef, CSTL, CHN_UTC, CHN_LAT, CHN_LON, CHN_ALT
from src.d_print import Enable_Debug, Debug

class Calc:
  def __init__(self):
    self.sign: str = '_nosign'
    self.is_setup = False
    self.last_calc = None

  def __repr__(self) -> str:
    return f"{self.__str__()} with CHNS: {self.get_chn()}, required variables: {self.required_vars()}"

  def __str__(self) -> str:
    pass

  def get_chn(self) -> List[str]:
    pass

  def required_vars(self) -> List[str]:
    pass

  def do_calc(self, sampled_pos, sats_FOV) -> Dict[str, list]:
    # Expected sats_FOV heirarchy is:  time{} -> prn{} = (x,y,z)
    # Expected sampled_pos order is :  chn{} = data[]
    pass

# TODO: passthrough calc to rename data example: satellites from PosData to sats_in_view

class Calc_gdop(Calc):
	def __init__(self, cstl: CSTL = None):
		super().__init__()
		if cstl == None:
			raise Exception("A constellation must be specified "
											"for this calculation (CSTL.GPS or CSTL.GAL).")

		self.cstl: CSTL = cstl
		self.sign = f'_{self.cstl.name}'

	def __str__(self) -> str:
		return f'Calc_GDOP_{self.cstl.name}'	

	def get_chn(self) -> List[str]:
		# full format: chns[i] + FOVmodel signature + CSTL.name
		# example: GDOP_match1_GPS

		chns = ['HDOP', 'VDOP', 'TDOP','GDOP','sats_FOV']
		return [i+self.sign for i in chns]

	def required_vars(self) -> set:
		return {CHN_UTC, CHN_LAT, CHN_LON, CHN_ALT}

	def do_calc(self, pos_pos, sats_FOV) -> Dict[str, list]:
		# sats_FOV is ordered like:  times{} -> prn{} = (x,y,z)
		Enable_Debug()
		Debug(1, f'Starting calculation for: {self.__str__()}')

		chns = self.get_chn()

		results = {i:[] for i in chns}

		for i in range(len(pos_pos[CHN_UTC])):
			t = pos_pos[CHN_UTC][i]

			lat = pos_pos[CHN_LAT][i]
			lon = pos_pos[CHN_LON][i]
			alt = pos_pos[CHN_ALT][i]

			u = np.array(lla2ecef(lat, lon, alt))

			mat: np.array = []

			# Add visible satellites to LOS matrix
			for j in sats_FOV[t]:

				if j[0] != self.cstl.value[0]: continue

				sat_pos = sats_FOV[t][j]                # tuple, ECEF coord of a sat
				d = lambda ax: sat_pos[ax] - u[ax]      # float, axis value difference (x=0, y=1, z=2)
				psd = np.sqrt(d(0)**2 + d(1)**2 + d(2)**2)    # pseudo range from receiver to sat
				m_row = [-d(0)/psd, -d(1)/psd, -d(2)/psd, 1]  # Row in GDOP matrix
				mat.append(m_row)

			m = np.matmul(np.transpose(mat), mat)
			Q = np.linalg.inv(m)
			T = [Q[0][0], Q[1][1], Q[2][2], Q[3][3]]
			hdop = np.sqrt(T[0]**2 + T[1]**2)

			results[chns[0]].append(hdop)
			results[chns[1]].append(T[2])
			results[chns[2]].append(T[3])
			results[chns[3]].append(np.sqrt(np.trace(Q)))
			results[chns[4]].append(len(mat))
    
		self.last_calc = results
		return results

class Calc_wgdop(Calc):
	def __init__(self):
		super().__init__()
		self.sign = ''

	def __str__(self) -> str:
		return 'Calc_wGDOP'

	def get_chn(self) -> List[str]:
		chns = ['wHDOP', 'wVDOP', 'wTDOP','wGDOP', 'sats_FOV']
		return [i+self.sign for i in chns]

	def required_vars(self) -> set:
		return {CHN_UTC, CHN_LAT, CHN_LON, CHN_ALT}

	def do_calc(self, pos_pos, sats_FOV) -> Dict[str, list]:
		# sats_FOV is ordered like:  times{} -> prn{} = (x,y,z)
		Enable_Debug()
		Debug(1, f'Starting calculation for: {self.__str__()}')

		chns = self.get_chn()
		results = {i:[] for i in chns}

		for i in range(len(pos_pos[CHN_UTC])):
			t = pos_pos[CHN_UTC][i]

			lat = pos_pos[CHN_LAT][i]
			lon = pos_pos[CHN_LON][i]
			alt = pos_pos[CHN_ALT][i]

			u = np.array(lla2ecef(lat, lon, alt))

			nsats = len(sats_FOV[t])

			mat = []
			w   = [ [ 0.0 for y in range(nsats)] for x in range(nsats)] # Create zeros weight matrix

			# Add visible satellites to LOS matrix
			for count, j in enumerate(sats_FOV[t]):
				sat_pos = sats_FOV[t][j]                # tuple, ECEF coord of a sat

				d = lambda ax: sat_pos[ax] - u[ax]      # float, axis value difference (x=0, y=1, z=2)
				psd = np.sqrt(d(0)**2 + d(1)**2 + d(2)**2)    # pseudo range from receiver to sat

				sinE = np.dot(u/np.linalg.norm(u), sat_pos/np.linalg.norm(sat_pos))

				m_row = []
				if j[0] == 'G' or j[0] == 'C':
					m_row = [-d(0)/psd, -d(1)/psd, -d(2)/psd, 1, 0]   # Row in GDOP matrix for gps
					w[count][count] = 1/(0.3 * sinE * sinE)           # Weight for GPS or BeiDou
				elif j[0] == 'E' or j[0] == 'R':
					m_row = [-d(0)/psd, -d(1)/psd, -d(2)/psd, 0, 1]   # Row in GDOP matrix for galileo
					w[count][count] = 1/(0.6 * sinE * sinE)           # Weight for GALILEO or GLONASS
				else:
					raise Exception(f'Constelation not supported: {j[0]}')

				mat.append(np.array(m_row, np.float))

			mat = np.array(mat, np.float)
			w = np.array(w, np.float)

			Q = np.matmul(np.transpose(mat), w)
			Q = np.matmul(Q,mat)
			Q = np.linalg.inv(Q)
			T = [Q[0][0], Q[1][1], Q[2][2], Q[3][3]]
			hdop = np.sqrt(T[0]**2 + T[1]**2)

			results[chns[0]].append(hdop)
			results[chns[1]].append(T[2])
			results[chns[2]].append(T[3])
			results[chns[3]].append(np.sqrt(np.trace(Q)))
			results[chns[4]].append(nsats)
    
		self.last_calc = results
		return results

