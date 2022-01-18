# CDME Scan Generation

This library generates the scan vectors used in Powder Bed Fusion (PBF) Additive Manufacturing (AM) Systems. Built for the Ohio State University Center for Design and Manufacturing Excellence (CDME) to prototype and develop new scanning algorithms.

## To Install

You'll need to install the following prior to this: 
- [Git](https://git-scm.com/downloads), the version control system we use. All the default options are fine.
- [GitKraken](https://www.gitkraken.com/download), a GUI that makes Git easier to work with. Optional if you're familiar with command-line Git. 
- A text editor. Most of us recommend [VSCode](https://code.visualstudio.com/download). 
- [Visual Studio](https://visualstudio.microsoft.com/). Specifically, the "C++ Desktop Development" bucket. MSVC v140 (which isn't selected by default but you should select) is required by one of our Python libraries.
- [Python](https://www.python.org/downloads/release/python-3910/). Python 3.9.9 is recommended. We haven't extensively tested on different versions, but we know dependencies break on Python 3.6 and Python 3.10. 
- [Python Prerequisites]: A bunch of libraries. Run `python -mpip install -r requirements.txt` in the base directory of this repository (note: NOT inside the `pyslm` directory) to install them all.

Then, do the following: 
1. **Set Up Folders.** Create a folder called `cdme` somewhere on your machine - your choice where. The goal is to get all our repositories in one folder next to each other. 
2. **Clone This Repo.** Use GitKraken to clone this repository into that folder. When you're done, the `cdme-scangen` folder should be inside the `cdme` folder. 
3. **Install Python Dependencies.** You can do this by running `python -mpip install -r requirements.txt` from a terminal that's inside this directory (NOT) the `pyslm` directory. 
4. **Compile PySLM.**
    - Open a Command Prompt with Administrator Access.
    - `cd` into the `pyslm` directory at the top level of this repository. 
    - If you plan to make `PySLM` changes, run `python setup.py develop` in a way that sets up symlinks, which will make new changes to the library immediately reflect. Otherwise, run `python setup.py develop`, which compiles in a static kind of way. 

If you set everything up successfully, you should be able to run `python main.py` from the terminal and it should work correctly with no issues.

If you plan to use this with the UI, now follow the instructions in the [cdme-scangen-ui](https://github.com/osu-cdme/cdme-scangen-ui) repository. 

## To Run

### Code
The `main.py` file is your starting point for everything. Simply run it with `python main.py` from the top level of this repository. Default parameters are loaded from the `schema.json` file. 

### Writing New Algorithms
Writing new algorithms is currently a bit difficult; to do so, you will need to become familiar with [pyslm](https://github.com/drlukeparry/pyslm), the library we wrap around and use for most of the real functionality. For CDME employees, there's some documentation in OneDrive inside the "Scan Path Generation" folder; more will be written in the coming weeks. 

We recommend writing new algorithms in the `src` folder rather than doing so inside the `pyslm` library itself, when possible. 

## Documentation
Fair warning - this section may be out of date. It was written early 2021 and it hasn't been touched since. 

### View Documentation
Documentation is not currently hosted online; however, the tool outlined below, `sphinx`, generates `.html` files you can view with any popular web browser.

### Generate Documentation
I've set up `sphinx`, which automatically does some documentation based solely on docstrings. It isn't necessary, but it's a more graphical way to look at function definitions and so on and didn't take much time to set up. 

**To Install:** To get Sphinx installed, run `python -mpip install -U sphinx`. You will likely need to add `<path to Python install>/Scripts` (which will now have `sphinx-build.exe` in it) to your PATH environment variable. If you do it correctly, `sphinx-build --version` in a terminal won't give you an error.

**To Run:** To actually document once you have Sphinx installed, you need two commands: 
- If you rearrange package structure or add/remove files, you will need to regenerate the .rst files - the files that dictate high-level layout and, more importantly, how pages relate to each other. Delete all `.rst` files (except `index.rst`) in `docs/source`, then run `sphinx-apidoc -o source ../src` from the `docs` directory. Then, run the below command.
- If you just changed/added docstrings and want to re-build the documentation, run `sphinx-build -b html source build` from the `docs` directory. There should then be an `index.html` file in the `docs/source` directory that is the root page of the documentation. 

## Attributions

This infrastucture makes heavy use of the [pyslm](https://github.com/drlukeparry/pyslm/) library written by [@drlukeparry](https://github.com/drlukeparry) for all the difficult slicing and hatching. Many thanks to him. 
