"""
Created on Wed Feb  3 14:37:32 2021

@author: harsh

Example for PySLM slicing, data manipulation, and visualizations
"""

# Standard Library Imports
import sys
import os
import glob
import time
import statistics as stats
import json 

# tl;dr custom PYTHONPATH and input argument stuff
# Command line stuff is a little complicated, and that's a fair critique
# If we get one command line argument in, we assume it's a JSON-serialized object representing the user's input parameters
# If we get two command line arguments in, we assume the first is the user's input params and the second is a JSON-serialized list of anything to manually add to the python path
    # Note that the second argument can be specified without specifying the first argument by simply passing in an empty JSON-serialized dictionary as the first

# First command line argument is a list of the user's command 
if len(sys.argv) > 1:
    config = json.loads(sys.argv[1])
if len(sys.argv) > 2: # Hacky way to ensurea given library (in our case, generally pyslm) gets loaded from the UI
    for path in json.loads(sys.argv[2]):
        print("Appending {} to PYTHONPATH.".format(path))
        sys.path.append(path)
print(sys.path)

# Third-Party Imports
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import sklearn.preprocessing as skp
import pandas as pd 
from pprint import pprint 

# Local Imports
#sys.path.insert(0, os.path.abspath("pyslm/pyslm"))  # nopep8
import pyslm
import pyslm.visualise
import pyslm.analysis
import pyslm.geometry
from pyslm.hatching import hatching
from pyslm.geometry import HatchGeometry
from pyslm.hatching.multiple import hatch_multiple
from src.standardization.shortening import split_long_vectors
from src.standardization.lengthening import lengthen_short_vectors
from src.island.island import BasicIslandHatcherRandomOrder
from src.scanpath_switching.scanpath_switching import excel_to_array, array_to_instances

#%%
'''
STEP 1: Initialize part, build, and program parameters
'''

# TODO: Split all this input/output into a separate Python file 

# Import Excel Parameters
def eval_bool(str):
    return True if str == "Yes" else False

# "Parameters" for the file 
values = pd.ExcelFile(r'config.xlsx').parse(0)["Value"]
config_vprofiles = pd.ExcelFile(r'build_config.xls').parse(3,header=7)['Velocity Profile for build segments\nVP for jumps is selected in Region profile'][3:]
#config_speeds = pd.ExcelFile(r'build_config.xls').parse(2, header=5)['Velocity\n(mm/s)']
config_segstyles = pd.ExcelFile(r'build_config.xls').parse(3, header=7)['SegmentStyle ID\nMay be integer or text'][3:]
config_powers = pd.ExcelFile(r'build_config.xls').parse(3, header=7)['Lead laser power (Watts)'][3:]
segstyles = pd.DataFrame({'SegStyles':np.array(config_segstyles),
                          'Powers':np.array(config_powers),
                          'VelocityProfiles':np.array(config_vprofiles)})

# Go from our standardized source of fields, or our "schema"
with open("schema.json", "r") as f:
    schema = json.load(f)



# Otherwise, assemble and run with the default values
if len(sys.argv) <= 1 or not len(config):
    config = {}
    for category in schema:
        for attribute in schema[category]: 
            config[attribute["name"]] = attribute["default"]

# Cast int/float/bool to their Python representations, rather than just leaving everything as a string
for category in schema:
    for attribute in schema[category]:
        config[attribute["name"]] = int(config[attribute["name"]]) if attribute["type"] == "int" else config[attribute["name"]]
        config[attribute["name"]] = float(config[attribute["name"]]) if attribute["type"] == "float" else config[attribute["name"]]
        if attribute["type"] == "bool":
            config[attribute["name"]] = True if attribute["default"] == "Yes" else False

"""
Example Config Object:
{'# Inner Contours': 2,
 '# Outer Contours': 2,
 'Change Parameters': False,
 'Change Power': False,
 'Change Speed': False,
 'Contour First': True,
 'Hatch Angle': 66.7,
 'Hatch Sorting Method': 'None',
 'Output .png': True,
 'Output .svg': False,
 'Output Plots': True,
 'Part File Name': 'nut.stl',
 'Plot Centroids': False,
 'Plot Contours': True,
 'Plot Hatches': True,
 'Plot Jump Vectors': False,
 'Plot Parameter Changes': False,
 'Plot Power': False,
 'Plot Speed': False,
 'Plot Time': False,
 'Scan Strategy': 'default',
 'Spot Compensation': 1.0,
 'Volume of Offset Hatch': 0.08,
 'Write Debug Info': True}
 
(NOTE: This will change if schema.json changes, as this and the UI work directly from that.)
"""

USE_SCANPATH_SWITCHING = False

if config["Write Debug Info"]:
    print("Logging debug information to `debug.txt`.")
    debug_file = open("debug.txt", "w")
    debug_file.write("Input Parameters\n")
    debug_file.write("--------------------\n")
    for key, value in config.items():
        debug_file.write("{}: {}\n".format(key, value))
    debug_file.write("\n")

if USE_SCANPATH_SWITCHING:

    # Function takes in a pd.ExcelFile() instance (and debug file) and returns an array of arrays, each inside array with the following structure:
    # [0]: ID of the given Area (Equation: "<Row of Excel Sheet> - 2")
    # [1]: 6-Long Array of min-x, min-y, min-z, max-x, max-y, max-z 
    # [2]: scanpath identifier (`default`, `island`, etc.)
    # [3]: General Parameters (True/False)
    scanpath_info = excel_to_array(pd.ExcelFile(r'config.xlsx'), debug_file)
    debug_file.write("scanpath_info: \n{}".format(scanpath_info))

    # Function takes in the array from the previous call and returns an array of [hatcher instance, area]
    #   corresponding to the parameters and scan path type given in the array.
    scanpath_area_pairs = array_to_instances(scanpath_info, debug_file)
    debug_file.write("scanpath_area_pairs: \n{}".format(scanpath_area_pairs))

# Initialize Part
Part = pyslm.Part(config["Part File Name"])
Part.setGeometry('geometry/' + config["Part File Name"])
Part.origin = [0.0, 0.0, 0.0]
Part.rotation = np.array([0, 0, 90])
Part.dropToPlatform()

# Create a BasicIslandHatcher object for performing any hatching operations
myHatcher = hatching.Hatcher()
myHatcher.islandWidth = 3.0
myHatcher.islandOffset = 0
myHatcher.islandOverlap = 0

# Set the base hatching parameters which are generated within Hatcher
myHatcher.hatchAngle = values[22]  # [°] The angle used for the islands
# [mm] Offset between internal and external boundary
myHatcher.volumeOffsetHatch = values[23]
# [mm] Additional offset to account for laser spot size
myHatcher.spotCompensation = values[24]
myHatcher.numInnerContours = values[25]
myHatcher.numOuterContours = values[26]

if values[27]=='Alternate':
    myHatcher.hatchSortMethod = hatching.AlternateSort()
elif values[27]=='Linear':
    myHatcher.hatchSortMethod = hatching.LinearSort()
elif values[27]=='Greedy':
    myHatcher.hatchSortMethod = hatching.GreedySort()

MIN_POWER_LVL = min(config_powers.keys())
MAX_POWER_LVL = max(config_powers.keys())

# Instantiate model and set model parameters
model = pyslm.geometry.Model()
model.mid = 1

# Set the initial values for possible build style parameters
for style_id, seg_style in segstyles.iterrows():    
    bstyle = pyslm.geometry.BuildStyle()
    bstyle.bid = style_id
    bstyle.name = seg_style['SegStyles']
    bstyle.laserSpeed = 200     
    bstyle.laserPower = seg_style['Powers']  # [W]#
    bstyle.pointDistance = 60  # (60 microns)
    bstyle.pointExposureTime = 30  # (30 micro seconds)
        
    model.buildStyles.append(bstyle)

resolution = 0.2

# Set the layer thickness
LAYER_THICKNESS = 1  # [mm]

#%%
'''
STEP 2: Slice part, generate scan paths, control parameters while slicing the part 
'''

# Keep track of parameters
layers = []
layer_times = []
layer_powers = []
layer_speeds = []
layer_segstyles = []

# Perform the hatching operations
layer_segstyle = 11
layer_power = model.buildStyles[layer_segstyle].laserPower
layer_speed = model.buildStyles[layer_segstyle].laserSpeed
for z in tqdm(np.arange(0, Part.boundingBox[5],
                        LAYER_THICKNESS), desc="Processing Layers"):

    geom_slice = Part.getVectorSlice(z)  # Slice layer

    if USE_SCANPATH_SWITCHING:
        hatchers, areas = [], []
        for pair in scanpath_area_pairs:
            hatchers.append(pair[0])
            areas.append(pair[1])
        layer = hatch_multiple(hatchers[1:], areas[1:], hatchers[0], geom_slice, z)
    else:
        layer = myHatcher.hatch(geom_slice)  # Hatch layer

    # Vector Splitting; to use, switch to Hatcher()
    '''
    CUTOFF = 2  # mm
    for geometry in layer.geometry:
        if isinstance(geometry, HatchGeometry):
            coords = split_long_vectors(geometry.coords, CUTOFF)
            geometry.coords = coord
    '''

    '''
    # Vector Lengthening; to use, switch to Hatcher()
    CUTOFF = 2 # mm
    for geometry in layer.geometry:
        if isinstance(geometry, HatchGeometry):
            coords = lengthen_short_vectors(geometry.coords, CUTOFF)
            geometry.coords = coords
    '''

    # The layer height is set in integer increment of microns to ensure no rounding error during manufacturing
    layer.z = int(z*1000)
    for geometry in layer.geometry:
        geometry.mid = 1
        geometry.bid = 1

    # Get parameters for each layer and collect
    layer_times.append(pyslm.analysis.getLayerTime(layer, [model]))
    layer_powers.append(layer_power)
    layer_speeds.append(layer_speed)
    layer_segstyles.append(model.buildStyles[layer_segstyle].name)
    
    '''
    Scale parameters by how much time it's taking to scan layers.
    Attempts to address "pyramid problem" where as you move up building a part 
    shaped like a pyramid, layers take less time, and there's less time for 
    things to cool off, which leads to problems with the part.
    '''
    ACTIVATION_DIFF = .5
    if config["Change Parameters"] and len(layer_times) > 1:
        dt = np.diff(layer_times)
        if config["Change Power"]:
        # As time goes down, so should power
            if dt[len(dt)-1] > ACTIVATION_DIFF and layer_segstyle < MAX_POWER_LVL:
                layer_segstyle += 1
            elif dt[len(dt)-1] < -ACTIVATION_DIFF and layer_segstyle > MIN_POWER_LVL:
                layer_segstyle -= 1
            layer_power = model.buildStyles[layer_segstyle].laserPower
        if config["Change Speed"]:
            # As time goes down, so should speed
            layer_speed = model.buildStyles[layer_segstyle].laserSpeed

  
    layers.append(layer)

    # Change hatch angle every layer
    myHatcher.hatchAngle += 66.7
    myHatcher.hatchAngle %= 360

#%%
'''
STEP 3: Visualization Outputs       
'''

if config["Output Plots"]:

    # Create/wipe folder
    if not os.path.exists("LayerFiles"):
        os.makedirs("LayerFiles")
    else:
        for f in glob.glob("LayerFiles/*"):
            os.remove(f)

    # Generate new output
    for i in tqdm(range(len(layers)), desc="Generating Layer Plots"):
        fig, ax = plt.subplots()
        pyslm.visualise.plot(
            layers[i], plot3D=False, plotOrderLine=config["Plot Centroids"], plotHatches=config["Plot Hatches"], plotContours=config["Plot Contours"], plotJumps=config["Plot Jump Vectors"], handle=(fig, ax))

        if config["Output .png"]:
            fig.savefig("LayerFiles/Layer{}.png".format(i), bbox_inches='tight')
        if config["Output .svg"]:
            fig.savefig("LayerFiles/Layer{}.svg".format(i), bbox_inches='tight')

        plt.cla()
        plt.close(fig)
    
    if config["Plot Time"]:
        plt.figure()
        plt.title("Time by Layer")
        plt.xlabel("Layer number")
        plt.ylabel("Time (s)")
        plt.plot(layer_times)
        plt.show()
    
    if config["Plot Parameter Changes"]:
        # Diagnostic plots for parameter scaling    
        plt.figure()
        plt.title("Normalized Process Parameters by Layer")
        plt.xlabel("Layer number")
        plt.ylabel("Normalized process parameters")
        plt.plot(skp.scale(layer_times))
        plt.plot(skp.scale(layer_powers))
        plt.plot(skp.scale(layer_speeds))
        plt.legend(['Time','Power','Speed'], loc='upper right')
        plt.show()
    
        if config["Plot Power"]:
            plt.figure()
            plt.title("Power by Layer")
            plt.xlabel("Layer number")
            plt.ylabel("Power (W)")
            plt.plot(layer_powers)
            plt.show()        
        
        if config["Plot Speed"]:
            plt.figure()
            plt.title("Speed by Layer")
            plt.xlabel("Layer number")
            plt.ylabel("Speed (mm/s)")
            plt.plot(layer_speeds)
            plt.show()

'''
If we want to change to a subplot-based system, here's most of the code for it:
NUM_ROWS, NUM_COLS = 200, 2
fig, axarr = plt.subplots(NUM_ROWS, NUM_COLS)
pyslm.visualise.plot(layers[i], plot3D=False, plotOrderLine=True,
                                 plotHatches=True, plotContours=True, handle=(fig, axarr[i // NUM_COLS, i % NUM_COLS]))
'''
