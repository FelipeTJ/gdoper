###############################################################################
# Gdoper v1.3                                                                 #
#                                                                             #
# File:  reader_rinex.py
# Author: Felipe Tampier Jara
# Date:   5 Apr 2021
# Email:  felipe.tampierjara@tuni.fi
#
# Description:
# Program returns the data for GPS satellites' positions. It first checks if
# data for a given day has already been aquired and if not, it retrieves the
# data from the UNAVCO database and processes it accordingly.
#                                                                             #
###############################################################################

# %%

from xarray.core.dataarray import DataArray
from xarray.core.dataset import Dataset
from typing import Dict, Mapping, List, Tuple
import georinex as gr
import datetime as dt
import wget as wget
import time
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from common import *
from d_print import Print, Debug
from unavco.earthscope import get_earthscope_rinex, get_random_station

# TODO: create directory if it doesn't exist
# Directory where downloaded rinex files are stored
# The sublist of the path removes the /src directory part
R_FOLDER = os.path.dirname(os.path.abspath(__file__))[:-4] + "/rinex_files"

# Required tolerance for the eccentricity anomaly error
ECC_TOL = 0.001

DEFAULT_STATIONS = ["ac70", "ab33", "ac15"]
DL_MAX_TRIES = 5


class Satellite:
    def __init__(self, prn: str, date: dt.date, gps_data: Dataset):
        self.prn = prn
        self.dates = [date]
        self.gps_data = {self.dates[0]: gps_data}
        Print("debug0", f"Created Satellite object (PRN: {prn})")
        Print("debug0", f'data: {self.gps_data[self.dates[0]]["time"]}')

    def get_position(self, times: List[dt.datetime] = []):
        if len(times) == 0:
            raise Exception("list of times cannot be empty.")
        mes_date = dt.date(times[0].year, times[0].month, times[0].day)
        if mes_date not in self.dates:
            raise Exception("Data for this date doesn't exist")

        # Select the nearest recorded NAV message
        close_nav = self.gps_data[mes_date].sel(time=times, method="nearest")

        Print("\\debug0", f"Satellite PRN: {self.prn}")
        Print("\\debug0", f"NAV GPS message from times:")
        for i in close_nav["time"].values:
            Print("debug0", f"- {i}")

        Print("\\debug0", f"Requested compute at times:")
        for i in times:
            Print("debug0", f"- {i}")

        # Get the time of the NAV message
        td = close_nav["time"].values.astype("datetime64[us]").astype(dt.datetime)

        Print(
            "\\debug0",
            f"Difference between NAV message and requested times (- before, + after NAV):",
        )
        for i, j in zip(times, td):
            dif = i - j
            if dif < dt.timedelta(days=0):
                Print("debug0", f" -{-dif}")
            else:
                Print("debug0", f" +{dif}")

        Print("\\0debug", f"After: {close_nav}")

        ecef = gr.keplerian.keplerian2ecef(close_nav)

        da = DataArray(list(ecef), dims=["space", "time"], coords=[["x", "y", "z"], times])

        return da

    def add_date(self, datetime: dt.datetime, gps_data: Dataset):
        if not self.has_date(datetime):
            self.gps_data[datetime.date] = gps_data
        else:
            Print("debug", f"Data for {datetime.date} already exists.")

    def has_date(self, date: dt.date) -> bool:
        return date in self.gps_data.keys()


class OrbitalData:
    def __init__(self, utc: str = "1900-01-01 00:00:00"):
        # Date parameters
        d_utc = dt.datetime.fromisoformat(utc)
        y_utc = d_utc.year
        self.utc = dt.date(y_utc, d_utc.month, d_utc.day)
        self.gps_year = y_utc - 2000  # TODO: convert properly
        self.gps_day = (self.utc - dt.date(y_utc, 1, 1)).days + 1  # Adjust for date

        # File name parameters
        self.is_file_available = False
        self.station = DEFAULT_STATIONS[0]
        self.rinex_file = f"{self.station}{self.gps_day}0.{self.gps_year}n.Z"
        self.filedir_remote = ""
        self.filedir_local = ""

        # Dict containing all satellite objects
        self.sats: Dict[str, Satellite] = {}

        self.done_setup = False
        self.debuging = "none"

    def print_data(self):
        self.setup_check()

        print()
        Print("info", f"Variables for: {self}")
        for i in list(self.__dict__.keys()):
            Print(
                "info",
                f' - {i:15} : {(self.__dict__[i] if type(self.__dict__[i]) != dict else "<dict>")}',
            )
        print()

    # TODO: Create setup function
    def setup(self, utc: str = ""):
        try:
            d_utc = dt.datetime.fromisoformat(utc)

            if d_utc.year >= 2000:
                self.change_date(d_utc)
            else:
                raise Exception("Input date's year cannot be older than 2000")
        except:
            if self.utc.year == 1900:
                raise Exception("Setup needs an initial date to look for satellite data.")

        self.done_setup = True

        self.filedir_local = self.get_file()
        self.read_rinex()

        # Debug('Done setup\n')

    def setup_check(self):
        if not self.done_setup:
            raise Exception("Orbital_data has not been set up.")

    def change_station(self, new_station: str):
        self.station = new_station
        self.rinex_file = f"{self.station}{self.gps_day}0.{self.gps_year}n.Z"
        self.filedir_local = f"{RINEX_FOLDER}/{self.rinex_file}"
        self.is_file_available = False

    def change_date(self, new_datetime: dt.datetime):
        self.utc = (
            dt.datetime.fromisoformat(new_datetime) if (type(new_datetime) == str) else new_datetime
        )
        self.gps_year = self.utc.year - 2000
        self.gps_day = (self.utc - dt.datetime(self.utc.year, 1, 1)).days + 1  # Adjust for date
        self.utc = dt.date(self.utc.year, self.utc.month, self.utc.day)
        self.change_station(self.station)  # Update all filenames and directories

    def local_file_exists(self) -> bool:
        self.setup_check()

        Print("debug0", f"local_file_exists()")
        for file in os.listdir(RINEX_FOLDER):
            # Check if file with same day exists
            if file.endswith(self.rinex_file[4:]):
                self.change_station(file[:4])
                Print("debug0", f"File exists locally: {self.filedir_local}")
                return True
        return False

    def get_file(self) -> str:
        self.setup_check()

        Print("debug0", f"get_file()")
        if not self.local_file_exists():
            downloaded = False
            tries = 0
            while not downloaded:
                Print("info", f"Downloading...")

                # If current station is unavailable at self.utc: try other stations
                if 1 <= tries and tries < len(DEFAULT_STATIONS):
                    self.change_station(DEFAULT_STATIONS[tries])
                elif 1 <= tries:
                    self.change_station(get_random_station())

                if tries >= DL_MAX_TRIES:
                    raise Exception(f"Maximum download request attempts ({DL_MAX_TRIES}) reached.")

                tries = tries + 1
                downloaded = get_earthscope_rinex(self.rinex_file)

        self.is_file_available = True
        return f"{RINEX_FOLDER}/{self.rinex_file}"

    def read_rinex(self):
        self.setup_check()

        Print("debug0", f"read_rinex()")
        if not self.is_file_available:
            self.filedir_local = self.get_file()

        # Read all the data from Rinex file
        Print("info0", f'Reading Rinex file "{self.rinex_file}"...')
        nav = gr.load(self.filedir_local)

        now = time.perf_counter()
        # TODO: reset to normal operation (this is testing mode)
        for n in range(1, nav["sv"].size + 1):
            sat = "G" + f"{n:02}"
            # p.Print('\\debug',f'Satellite: {sat}')

            # Create or add data to Satellite object at date of self.utc
            if sat not in self.sats.keys():
                self.sats[sat] = Satellite(
                    sat, self.utc, nav.sel(sv=sat).dropna(dim="time", how="all")
                )
            elif not self.sats[sat].has_date(self.utc):
                self.sats[sat].add_date(self.utc, nav.sel(sv=sat).dropna(dim="time", how="all"))
            else:
                pass

        Print("info\\0", f"Done. ({time.perf_counter()-now:.3f}s for {len(self.sats)} satellites)")

    def get_sats_pos(
        self, time_list: List[dt.datetime]
    ) -> Mapping[str, Mapping[str, Tuple[float, float, float]]]:
        """
        Input a list of times for when to compute the positions of the satellites.
        Inputs can be either ISO formatted strings or datetime objects.
        """
        self.setup_check()

        Print("debug0", f"get_sats_pos()")
        if not self.is_file_available:
            self.read_rinex()

        if len(self.sats) == 0:
            Print(
                "\\error\\",
                f"[get_sats_pos] No Satellite objects in this instance (no file has been read yet)",
            )
            return

        times = time_list.copy()

        if len(times) != 0:
            for i in range(len(times)):
                if type(times[i]) == str:
                    times[i] = dt.datetime.fromisoformat(times[i])

        now = time.perf_counter()
        Print(
            "info0",
            f'Calculating satellite positions for "{self.utc.year}-{self.utc.month}-{self.utc.day}"...',
        )

        results = {}
        for t in time_list:
            results[t] = {}

        # TODO: fix output format to: time{} -> prn{} = (x,y,z)
        for prn in list(self.sats.keys()):
            dr = self.sats[prn].get_position(times)

            for t in times:
                results[t.isoformat(sep=" ")][prn] = dr.sel(time=t).values

        Print(
            "debug\\",
            f"Done. ({time.perf_counter()-now:.3f}s for {len(self.sats)*len(times)} positions)",
        )

        # Output order is:  times{} -> prn{} = (x,y,z)

        return results


if __name__ == "__main__":
    o = OrbitalData("2019-07-10 07:25:31")
    o.setup()
    o.print_data()
    # print("Results:\n",o.get_sats_pos(['2019-07-10 08:25:31', '2019-07-10 14:25:31']))
    o.get_sats_pos(["2019-07-10 08:25:31", "2019-07-10 14:25:31"])


# %%
