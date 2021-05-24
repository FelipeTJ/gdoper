# Gdoper
GDOP calculation for simple GPS positioning post-processing

## Introduction
Gdoper provides an easy to use interface for processing positioning related data in a straightforward manner. Given a file that contains positioning data logged by a GNSS receiver, it can automatically downloads the Ephemeris of the GPS and/or Galileo constellations at the time of the positioning data. The data of the receiver position and the satellite constellation is then available for processing. 

For example, a file containing the flight trajectory of a drone is input. The GPS and Galileo Ephemeris for the day of the flight is downloaded locally and pre-processed. It is now available for further processing.

## Usage
The following libraries must be installed for Gdoper to work:
- georinex
- unlzw3
- pyproj
- ftputil

Note:
The program has only been tested with Python 3.8.5

Positioning data is by default stored in a directory named 'test_data', located in the same directory as the 'gdoper_scripts.py' file.

Satellite data is by default stored in a file names 'rinex_files', which is also located in the same directory as the 'gdoper_scripts.py' file. This folder and its contents are created automatically as the program downloads satellite data (rinex files).

A example run is set up in the 'example_scripts.py' file. By running 'python3 example_scripts.py' in the command terminal, the program will process the data.
