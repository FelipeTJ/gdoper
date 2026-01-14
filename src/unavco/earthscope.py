import requests

from random import randint
from json import load
from pathlib import Path
from re import search

# https://gitlab.com/earthscope/public/earthscope-sdk
from earthscope_sdk.auth.device_code_flow import DeviceCodeFlow
from earthscope_sdk.common.context import SdkContext
from earthscope_sdk.config.settings import SdkSettings


UNAVCO_DIR = Path(__file__).resolve().parent
STATIONS = load(Path(UNAVCO_DIR / Path("unavco_stations.json")).open())

if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(UNAVCO_DIR.parent))

from common import RINEX_FOLDER


# choose where you want the token saved - the default file name is sso_tokens.json
# if you want to keep the default name, set the path to a directory. Include a file name to rename.
token_path = UNAVCO_DIR

# loads settings via loading chain
settings = SdkSettings()


def get_earthscope_rinex(station_rinex_file: str, save_dir: str = RINEX_FOLDER) -> bool:
    matches = search(r"(\d\d\d)0\.(\d\d)(n|e|g)\.Z", station_rinex_file)
    assert matches is not None, f"Incorrect Rinex filename format: {station_rinex_file}"

    remote_file_path = "20{1}/{0}/".format(*matches.groups()) + station_rinex_file
    req_path = "https://data.unavco.org/archive/gnss/rinex/nav/" + remote_file_path

    save_dir = Path(save_dir)
    station_rinex_file = Path(req_path).name

    # instantiate the device code flow subclass
    device_flow = DeviceCodeFlow(SdkContext(settings))

    # Do the device code flow directly
    with device_flow.do_flow() as codes:
        print(f"To authenticate, visit {codes.verification_uri_complete}")

    token = device_flow.access_token

    r = requests.get(req_path, headers={"authorization": f"Bearer {token}"})
    if r.status_code == requests.codes.ok:
        # save the file
        with open(Path(save_dir / station_rinex_file), "wb") as f:
            for data in r:
                f.write(data)
        return True
    else:
        # problem occured
        print(f"failure: {r.status_code}, {r.reason}")
        return False


def get_random_station():
    ix = randint(0, len(STATIONS))
    return STATIONS[ix]


if __name__ == "__main__":
    example_file = "ac701850.19n.Z"

    if get_earthscope_rinex(example_file):
        print("Successfully obtained file!")

    else:
        print("File not found:", example_file)
