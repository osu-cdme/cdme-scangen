# PowderBedFusion_ScanGenerator

This library generates the scan vectors used in Powder Bed Fusion (PBF) Additive Manufacturing (AM) Systems. Built for the Ohio State University Center for Design and Manufacturing Excellence (CDME) to prototype and develop new scanning algorithms.

## To Install

The following are required:

- **Microsoft Visual C++ 14.0**: Required for one of the Python libraries; downloading the installer [here](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and installing the defaults under "C++ Build Tools" (and possibly MSVC v140 if that doesn't work) should be enough.
- **Python**: Overall codebase runs on it. **Overall codebase is only tested on Python 3.9.1**. We can't speak for other versions, but we know 3.6.8 breaks. 
- **Python Prerequisites**: A bunch of libraries. Run `python -mpip install -r requirements.txt` in the base directory of this repository to install them all.

## To Run

The `main.py` file currently has basic overall usage implemented, and is pretty well outlined. Simply run it with `python main.py`. 

Experiment with changing the line `myHatcher = hatching.Hatcher()` to `myHatcher = hatching.StripeHatcher()` or `myHatcher = hatching.BasicIslandHatcher()` to try out scan paths other than the basic alternating one.

## To Develop

1. Get an editor. 
    - Visual Studio Code is recommended; the .vscode folder in this repository includes some useful debugger configurations. 
2. Set up `autopep8` for formatting. 
    - Visual Studio Code, the editor setting "Format on Save" is recommended.

You're good to start writing new algorithms in the PowderBedFusion/genScan folder! There's some documentation on Box inside the "Scan Path Generation" folder; more will be written in the coming weeks. 

## Attributions

This infrastucture heavily uses [pyslm](https://github.com/drlukeparry/pyslm/), which is built by [@drlukeparry](https://github.com/drlukeparry). Note that we've done some renaming to make this closer to other bits of our architecture, particularly the OASIS framework.
