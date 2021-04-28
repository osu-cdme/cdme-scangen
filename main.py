"""
Created on Wed Feb  3 14:37:32 2021

@author: harsh

Example showing how to use pypyslm for generating scan vector
"""

# Standard Library Imports
import sys
import os
import glob
import time
import statistics as stats

# Third-Party Imports
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import sklearn.preprocessing as skp
import pandas as pd 

# Local Imports
#sys.path.insert(0, os.path.abspath("pyslm/pyslm"))  # nopep8
import pyslm
import pyslm.visualise
import pyslm.analysis
import pyslm.geometry
from pyslm.hatching import hatching
from pyslm.geometry import HatchGeometry
from src.standardization.shortening import split_long_vectors
from src.standardization.lengthening import lengthen_short_vectors
from src.island.island import BasicIslandHatcherRandomOrder

# Import Excel Parameters
def eval_bool(str):
    return True if str == "Yes" else False

values = pd.ExcelFile(r'config.xlsx').parse(0)["Value"]
PART_NAME = values[2]
GENERATE_OUTPUT = eval_bool(values[8]) 
OUTPUT_PNG = eval_bool(values[9])
OUTPUT_SVG = eval_bool(values[10])
PLOT_CONTOURS = eval_bool(values[11])
PLOT_HATCHES = eval_bool(values[12])
PLOT_CENTROIDS = eval_bool(values[13])
PLOT_JUMPS = eval_bool(values[14])

CHANGE_PARAMS = eval_bool(values[3]) 
CHANGE_POWER = eval_bool(values[4]) 
CHANGE_SPEED = eval_bool(values[5]) 

PLOT_TIME = eval_bool(values[15]) 
PLOT_CHANGE_PARAMS = eval_bool(values[16]) 
PLOT_POWER = eval_bool(values[17]) 
PLOT_SPEED = eval_bool(values[18]) 

# Initialize Part
Part = pyslm.Part('nist')
Part.setGeometry('Geometry/' + PART_NAME)
Part.origin = [0.0, 0.0, 0.0]
Part.rotation = np.array([0, 0, 90])
Part.dropToPlatform()

# Create a BasicIslandHatcher object for performing any hatching operations (
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
else:
    myHatcher.hatchSortMethod = hatching.AlternateSort()
    
# Set the initial values for model and build style parameters
bstyle = pyslm.geometry.BuildStyle()
bstyle.bid = 1
bstyle.laserSpeed = 200.0  # [mm/s]
bstyle.laserPower = 200  # [W]#
bstyle.pointDistance = 60  # (60 microns)
bstyle.pointExposureTime = 30  # (30 micro seconds)

model = pyslm.geometry.Model()
model.mid = 1
model.buildStyles.append(bstyle)
resolution = 0.2

# Set the layer thickness
LAYER_THICKNESS = 1  # [mm]


# Keep track of parameters
layers = []
layer_times = []
layer_powers = []
layer_speeds = []

N_MOVING_AVG = 1 # This should be dependent on the number of layers in the part. For only 22 layers, 1 works best 

# Perform the hatching operations
for z in tqdm(np.arange(0, Part.boundingBox[5],
                        LAYER_THICKNESS), desc="Processing Layers"):

    geom_slice = Part.getVectorSlice(z)  # Slice layer
    layer = myHatcher.hatch(geom_slice)  # Hatch layer

    # Vector Splitting; to use, switch to Hatcher()
    '''
    CUTOFF = 2  # mm
    for geometry in layer.geometry:
        if isinstance(geometry, HatchGeometry):
            coords = split_long_vectors(geometry.coords, CUTOFF)
            geometry.coords = coords
    '''

    # Vector Lengthening; to use, switch to Hatcher()
    '''
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
    layer_powers.append(model.buildStyles[0].laserPower)
    layer_speeds.append(model.buildStyles[0].laserSpeed)
    
    '''
    Scale parameters by time/layer differential 
    There will likely be problems with this inter-layer scaling method
    Ultimately we want sensor data for this kind of inter-layer adjustment
    '''
    if CHANGE_PARAMS and len(layers) > N_MOVING_AVG-1:
        # Moving average of previous layers
        prev_l0 = []
        for i in range(len(layers) - N_MOVING_AVG, len(layer_times)):
            prev_l0.append(layer_times[i])
        moving_avg = stats.mean(prev_l0)
        if moving_avg != 0:
            if CHANGE_POWER:
                # As time goes down, so should power
                model.buildStyles[0].laserPower *= 1 + (layer_times[len(layer_times)-1] - moving_avg)/moving_avg
            if CHANGE_SPEED:
                # As time goes down, so should speed
                model.buildStyles[0].laserSpeed *= 1 + (layer_times[len(layer_times)-1] - moving_avg)/moving_avg
  
    layers.append(layer)

    # Change hatch angle every layer
    myHatcher.hatchAngle += 66.7
    myHatcher.hatchAngle %= 360
       

if GENERATE_OUTPUT:

    # Create/wipe folder
    if not os.path.exists("LayerFiles"):
        os.makedirs("LayerFiles")
    else:
        for f in glob.glob("LayerFiles/*"):
            os.remove(f)

    # Generate new output
    for i in tqdm(range(len(layers)), desc="Generating Layer Path Plots"):
        fig, ax = plt.subplots()
        pyslm.visualise.plot(
            layers[i], plot3D=False, plotOrderLine=PLOT_CENTROIDS, plotHatches=PLOT_HATCHES, plotContours=PLOT_CONTOURS, plotJumps=PLOT_JUMPS, handle=(fig, ax))

        if OUTPUT_PNG:
            fig.savefig("LayerFiles/Layer{}.png".format(i), bbox_inches='tight')
        if OUTPUT_SVG:
            fig.savefig("LayerFiles/Layer{}.svg".format(i), bbox_inches='tight')

        plt.cla()
        plt.close(fig)
    
    if PLOT_TIME:
        plt.figure()
        plt.title("Time by Layer")
        plt.xlabel("Layer number")
        plt.ylabel("Time (s)")
        plt.plot(layer_times)
        plt.show()
    
    if PLOT_CHANGE_PARAMS:
        # Diagnostic plots for parameter scaling    
        plt.figure()
        plt.title("Normalized Process Parameters by Layer")
        plt.xlabel("Layer number")
        plt.ylabel("Normalized process parameters")
        plt.plot(skp.scale(layer_times))
        plt.plot(skp.scale(layer_powers))
        plt.plot(skp.scale(layer_speeds))
        plt.legend(['Time','Power','Speed','Island Width'], loc='upper right')
        plt.show()
    
        if PLOT_POWER:
            plt.figure()
            plt.title("Power by Layer")
            plt.xlabel("Layer number")
            plt.ylabel("Power (W)")
            plt.plot(layer_powers)
            plt.show()        
        
        if PLOT_SPEED:
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
