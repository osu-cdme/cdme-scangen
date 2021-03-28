# PowderBedFusion_ScanGenerator

This library generates the scan vectors used in Powder Bed Fusion (PBF) Additive Manufacturing (AM) Systems. Built for the Ohio State University Center for Design and Manufacturing Excellence (CDME) to prototype and develop new scanning algorithms.

## To Install

Either run `python -mpip install -r requirements.txt` in the base directory of this repository or install the following packages:

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

The `test2.py` file currently has a basic implementation of line scanning and island scanning implemented.

## To Develop

1. Install autopep8
2. Write new algorithms in the pyslm/genScan folder!

## Attributions

This library is built on top of [pyslm](https://github.com/drlukeparry/pyslm/), built by [@drlukeparry](https://github.com/drlukeparry).
