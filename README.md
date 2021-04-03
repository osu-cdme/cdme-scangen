# PowderBedFusion_ScanGenerator

This library generates the scan vectors used in Powder Bed Fusion (PBF) Additive Manufacturing (AM) Systems. Built for the Ohio State University Center for Design and Manufacturing Excellence (CDME) to prototype and develop new scanning algorithms.

## To Install

Many versions should work, but **the library is tested on Python 3.9.1**. You can check your running python version by running `python --version` in a terminal. The python version used depends on the python install specified in your `PATH` environment variable. We can't speak for other versions, but can confirm **3.6.8 breaks**. 

To install all the Python prerequisites, either run `python -mpip install -r requirements.txt` in the base directory of this repository or install the following packages:

- sphinx
- numpy
- scipy
- shapely
- networkx
- Rtree
- trimesh
- triangle
- scikit-image
- cython
- pyclipper
- autopep8 (for formatting)

## To Run

The `main.py` file currently has a basic implementation of line scanning and island scanning implemented.

## To Develop

1. Set up `autopep8` for formatting. This depends on your editor, but in Visual Studio Code setting the editor setting "Format on Save" is recommended.

You're good to start writing new algorithms in the pyslm/genScan folder! There's some documentation on Box inside the "Scan Path Generation" folder; more will be written in the coming weeks. 

## Attributions

This infrastucture heavily uses [pyslm](https://github.com/drlukeparry/pyslm/), which is built by [@drlukeparry](https://github.com/drlukeparry).
