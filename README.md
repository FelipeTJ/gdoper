# Gdoper
GDOP calculation for simple GPS positioning post-processing

## Introduction
Gdoper provides an easy to use interface for processing positioning related data
in a straightforward manner. Given a file that contains positioning data of a
GPS receiver, it automatically downloads the Ephemeris of the GPS constellation
at the time of the positioning data. The data of the receiver position and the
satellite constellation is then available for processing. 

For example, a file containing the flight trajectory of a drone is input. The
GPS Ephemeris for the day of the flight is downloaded locally and pre-processed.
It is now available for further processing. An [Earthscope
account](https://www.unavco.org/data/gps-gnss/file-server/user-profile.html) is
required to access the publicly available UNAVCO GNSS database

## Usage
It is recommended to use a virtual environment for this package:
```
python -m venv venv_gdoper
```

Activate the venv (Windows):
```
& .\venv_gdoper\bin\Activate.ps1
```

Activate the venv (Linux):
```
. ./venv_gdoper/activate
```

install the requirements:
```
pip install -r requirements.txt
```


Note: The program has only been tested with Python 3.8.5

Positioning data is by default stored in a directory named 'test_data', located
in the same directory as the 'gdoper.py' file.

Satellite data is by default stored in a file names 'rinex_files', which is also
located in the same directory as the 'gdoper.py' file. This folder and its
contents are created automatically as the program downloads satellite data
(rinex files).

A example run is set up in the 'gdoper.py' file. By running 'python3 gdoper.py'
in the command terminal, the program should process the data.
