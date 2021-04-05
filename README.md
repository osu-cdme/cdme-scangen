# PowderBedFusion_ScanGenerator

This library generates the scan vectors used in Powder Bed Fusion (PBF) Additive Manufacturing (AM) Systems. Built for the Ohio State University Center for Design and Manufacturing Excellence (CDME) to prototype and develop new scanning algorithms.

## To Install

The following are required:

- **Microsoft Visual C++ 14.0**: Required for one of the Python libraries; downloading the installer [here](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and installing the defaults under "C++ Build Tools" (and possibly MSVC v140 if that doesn't work) should be enough.
- **Python**: Overall codebase runs on it. **Overall codebase is only tested on Python 3.9.1**. We can't speak for other versions, but we know 3.6.8 breaks. 
- **Python Prerequisites**: A bunch of libraries. Run `python -mpip install -r requirements.txt` in the base directory of this repository to install them all.

## To Run

The `main.py` file currently has a basic implementation of line scanning and island scanning implemented.

## To Develop

1. Set up `autopep8` for formatting. This depends on your editor, but in Visual Studio Code setting the editor setting "Format on Save" is recommended.

You're good to start writing new algorithms in the pyslm/genScan folder! There's some documentation on Box inside the "Scan Path Generation" folder; more will be written in the coming weeks. 

## Attributions

This infrastucture heavily uses [pyslm](https://github.com/drlukeparry/pyslm/), which is built by [@drlukeparry](https://github.com/drlukeparry).
