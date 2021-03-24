# PowderBedFusion_ScanGenerator

This library generates the scan vectors used in Powder Bed Fusion (PBF) Additive Manufacturing (AM) Systems. Built for the Ohio State University Center for Design and Manufacturing Excellence (CDME) to prototype and develop new scanning algorithms.

## To Install

Either run `python -mpip install -r requirements.txt` in the base directory of this repository or install the following packages: - sphinx  
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

## To Run

The `test2.py` file currently has a basic implementation of line scanning and island scanning implemented.

## To Develop

Write new algorithms in the PowderBedFusion/genScan folder.
