from typing import List, Mapping, Tuple
import numpy as np
from common import *


class FOV_model:
    def __init__(self):
        self.is_setup = False

    def setup(self, **args) -> None:
        """
        Sets the constants and values used for calculating FOV in a model
        """
        raise Exception("SubClass.setup() not defined")

    def required_vars(self) -> List[str]:
        """
        Return the variables required to calculate FOV for a model
        """
        raise Exception("SubClass.required_vars() not defined")

    def get_sats(
        self, pos_data, sats_data
    ) -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
        """
        Return a container with the positions of all
        visible satellites at every given time.\n
        The heirarchy is: {'time': {'prn': (x,y,z) } }
        """
        raise Exception("SubClass.get_sats() not defined")


class FOV_view_match(FOV_model):
    def __init__(self):
        super().__init__()

    def setup(self, **args):
        """
        FOV_view_match model doesn't require any additional setup.\n
        This method is empty.
        """
        super().is_setup = True

    def required_vars(self) -> List[str]:
        """
        Return the variables required to calculate FOV for this model
        """
        return [CHN_LAT, CHN_LON, CHN_ALT, CHN_UTC, CHN_SAT]

    def get_sats(self, pos_pos, sats_pos) -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
        """
        Calculate the satellites in view, given the measured amount of
        visible satellites, at every time and place.
        """
        # Sats pos is ordered like:  times{} -> prn{} = (x,y,z)

        # initialize output map
        sats_LOS = {}
        for t in pos_pos[CHN_UTC]:
            sats_LOS[t] = {}

        # Calculate best visible sats
        for i in range(len(pos_pos[CHN_UTC])):
            t = pos_pos[CHN_UTC][i]  # Timestamps from pos_data
            n_s = int(pos_pos[CHN_SAT][i])  # n. of visible sats at 't'

            lat = pos_pos[CHN_LAT][i]
            lon = pos_pos[CHN_LON][i]
            alt = pos_pos[CHN_ALT][i]

            u = np.array(lla2ecef(lat, lon, alt))
            u = u / np.linalg.norm(u)

            dots = {}
            # Calculate dot prod to all sats
            for sat in sats_pos[t]:
                p_s = np.array(sats_pos[t][sat])
                p_s = p_s / np.linalg.norm(p_s)
                dots[np.dot(u, p_s)] = sat

            # Order in terms of largest abs value
            ordered = sorted(dots.keys(), key=np.abs, reverse=True)

            # Set the n_s most visible satellites as the ones in FOV
            for j in range(n_s):
                dot = ordered[j]
                sat = dots[dot]
                sats_LOS[t][sat] = sats_pos[t][sat]

        # sats_LOS is ordered like:  times{} -> prn{} = (x,y,z)
        return sats_LOS
