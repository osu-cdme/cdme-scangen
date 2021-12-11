# CDME Scan Generation

This library generates the scan vectors used in Powder Bed Fusion (PBF) Additive Manufacturing (AM) Systems. Built for the Ohio State University Center for Design and Manufacturing Excellence (CDME) to prototype and develop new scanning algorithms.

## To Install

### 1. Clone the repo 
Clone the repository **with submodules** with the command `git clone https://github.com/osu-cdme/cdme-scangen --recurse-submodules`. You can optionally specify a folder name by including it as another command line parameter after the URL. 
- We need to clone with submodules because we keep a library we hook into, `pyslm`, as a submodule, which makes it easy to contribute back into the library should we make changes beneficial to the overall community.
- If you cloned normally by mistake, either delete and reclone or execute `git submodule update --init --recursive`.

See [here](http://openmetric.org/til/programming/git-pull-with-submodule/) and [here](https://stackoverflow.com/questions/1030169/easy-way-to-pull-latest-of-all-git-submodules) for more details.

### 2. Install Dependencies
Install the following dependencies:

- **Microsoft Visual C++ 14.0**: Required for one of the Python libraries; downloading the installer [here](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and installing the defaults under "C++ Build Tools" (and possibly MSVC v140 if that doesn't work) should be enough.
- **Python**: Install Python 3.9.9. The codebase theoretically works with others as well, just for compatibility reasons other versions (of ones we've tested 3.6, 3.10) break.
- **Python Prerequisites**: A bunch of libraries. Run `python -mpip install -r requirements.txt` in the base directory of this repository to install them all.

### 3. Compile PySLM
**Note that you will get import issues until you do this. Do not forget this.**

As we interface with the module by cloning it down rather than through PyPi or an automated online repository, we need to build it from source, which is easy enough. First, `cd` into the `pyslm` folder in the top level of this repo. This one will have `build`, `dist`, `docs`, `examples`, and other folders in it.

If you do not plan to make modifications to `pyslm`:
-  Execute `python setup.py install` from here, which will compile the module. 
    - NOTE: If you are on Windows (which we recommend) you will need to launch this from an elevated command prompt.

If you plan to make modifications to `pyslm`: 
- Execute `python setup.py develop` from here, which will compile the module *in a way that sets up symlinks, meaning you will not need to keep recompiling when you make changes*. 

See [here](https://stackoverflow.com/questions/19048732/python-setup-py-develop-vs-install) for an explanation of the difference. 

## To Run

### UI
I'm hoping to bundle the UI for this at some point, but the steps for getting the UI working aren't currently all too difficult. Do the following:
- Clone [this repo](https://github.com/osu-cdme/cdme-scangen-ui) when your terminal is one level up from this one, meaning your `cdme-scangen` and `cdme-scangen-ui` folders will be in the same folder. This is necessary for a few relative paths.
- Execute `npm install` from your `cdme-scangen-ui` folder to install all the Electron requisite packages. If you don't have `npm`, install Node.js (any recent stable version should be fine) and it will come bundled.
- Execute `npm start` from your `cdme-scangen-ui` folder and the application should show up, and it should be self-explanatory from there. 

If you're curious, it also works off of the `schema.json` file to display input fields for the user, then takes all the values from the form and starts this script with them, passing the user-input values in as serialized JSON. The goal was to get all the input parameters in one point so that we don't need to change it all over the place, and this does that. 

### Code
The `main.py` file is your starting point for everything. Simply run it with `python main.py` from the top level of this repository. Experiment with changing the line `myHatcher = hatching.Hatcher()` to `myHatcher = hatching.StripeHatcher()` or `myHatcher = hatching.BasicIslandHatcher()` to try out scan paths other than the basic alternating one. Output will be generated in the `LayerFiles/` directory as a `.png` image for each layer.

If you run this script directly (rather than from the UI), it will take all its input variables (i.e. whether to do plots and stuff like that) from whatever `schema.json` states is its default value.

## To Develop
All you really need is an editor. Visual Studio Code is recommended, as the .vscode folder in this repository includes some debugger configuration you may find useful. 

### Writing New Algorithms
Writing new algorithms is currently a bit difficult; to do so, you will need to become familiar with [pyslm](https://github.com/drlukeparry/pyslm), the library we wrap around and use for most of the real functionality. For CDME employees, there's some documentation in OneDrive inside the "Scan Path Generation" folder; more will be written in the coming weeks. 

We recommend writing new algorithms in the `src` folder rather than doing so inside the `pyslm` library itself, when possible. 

## Documentation

### View Documentation
Documentation is not currently hosted online; however, the tool outlined below, `sphinx`, generates `.html` files you can view with any popular web browser.

### Generate Documentation
I've set up `sphinx`, which automatically does some documentation based solely on docstrings. It isn't necessary, but it's a more graphical way to look at function definitions and so on and didn't take much time to set up. 

**To Install:** To get Sphinx installed, run `python -mpip install -U sphinx`. You will likely need to add `<path to Python install>/Scripts` (which will now have `sphinx-build.exe` in it) to your PATH environment variable. If you do it correctly, `sphinx-build --version` in a terminal won't give you an error.

**To Run:** To actually document once you have Sphinx installed, you need two commands: 
- If you rearrange package structure or add/remove files, you will need to regenerate the .rst files - the files that dictate high-level layout and, more importantly, how pages relate to each other. Delete all `.rst` files (except `index.rst`) in `docs/source`, then run `sphinx-apidoc -o source ../src` from the `docs` directory. Then, run the below command.
- If you just changed/added docstrings and want to re-build the documentation, run `sphinx-build -b html source build` from the `docs` directory. There should then be an `index.html` file in the `docs/source` directory that is the root page of the documentation. 

## Attributions

This infrastucture makes heavy use of the [pyslm](https://github.com/drlukeparry/pyslm/) library, written by [@drlukeparry](https://github.com/drlukeparry), for all the actual difficult slicing, hatching, and so on. Many thanks to him. 
