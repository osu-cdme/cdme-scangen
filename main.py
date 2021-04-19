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
import sklearn.preprocessing

# Local Imports
# sys.path.insert(0, os.path.abspath("pyslm"))  # nopep8
import pyslm
import pyslm.visualise
import pyslm.analysis
from pyslm.hatching import hatching
from pyslm.geometry import HatchGeometry
from src.standardization.shortening import split_long_vectors
from src.standardization.lengthening import lengthen_short_vectors
from src.island.island import BasicIslandHatcherRandomOrder


Part = pyslm.Part('nist')
Part.setGeometry('TestGeometry/nut.stl')
Part.origin = [0.0, 0.0, 0.0]
Part.rotation = np.array([0, 0, 90])
Part.dropToPlatform()

# Create a BasicIslandHatcher object for performing any hatching operations (
myHatcher = hatching.Hatcher()
myHatcher.islandWidth = 3.0
myHatcher.islandOffset = 0
myHatcher.islandOverlap = 0

# Set the base hatching parameters which are generated within Hatcher
myHatcher.hatchAngle = 45  # [°] The angle used for the islands
# [mm] Offset between internal and external boundary
myHatcher.volumeOffsetHatch = 0.08
# [mm] Additional offset to account for laser spot size
myHatcher.spotCompensation = .06
myHatcher.numInnerContours = 2
myHatcher.numOuterContours = 2
myHatcher.hatchSortMethod = hatching.AlternateSort()

# Set model and build style parameters
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


# Lists are for in-process monitoring of time spent on each layer and scaling other parameters accordingly
layers = []
layer_times = []
layer_lens = []
layer_powers = []
layer_speeds = []
layer_widths = []

# Options for parameter scaling between layers based on vector length or scan time of the previous layer
PARAMETER_SCALING = True
POWER = True
ISLAND_WIDTH = True
SPEED = True
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
     
    # Analyze total layer path parameters
    layer_lens.append(pyslm.analysis.getLayerPathLength(layer))
    layer_times.append(pyslm.analysis.getLayerTime(layer, [model]))
    layer_powers.append(model.buildStyles[0].laserPower)
    layer_speeds.append(model.buildStyles[0].laserSpeed)
    layer_widths.append(myHatcher.islandWidth)
    
    # Scale parameters by time/layer differential 
        # There will likely be problems with this inter-layer scaling method
        # Ultimately we want sensor data for this kind of inter-layer adjustment
    if PARAMETER_SCALING and len(layers) > N_MOVING_AVG-1:
        # Time of current layer
        t1 = pyslm.analysis.getLayerTime(layer, [model])
        # Moving average of previous layers
        prev_ts = []
        for i in range(len(layers) - N_MOVING_AVG, len(layers)):
            prev_ts.append(pyslm.analysis.getLayerTime(layers[i], [model]))
        moving_avg = stats.mean(prev_ts)  
        if POWER:
            # As time goes down, so should power
            model.buildStyles[0].laserPower *= 1 - (t1 - moving_avg)/moving_avg
        if ISLAND_WIDTH:
            # As time goes down, increase island width
            myHatcher.islandWidth *= 1 + (t1 - moving_avg)/moving_avg
        if SPEED:
            # As time goes down, so should speed
            model.buildStyles[0].laserSpeed *= 1 - (t1 - moving_avg)/moving_avg

    
    layers.append(layer)
    

    # Change hatch angle every layer
    myHatcher.hatchAngle += 66.7
    myHatcher.hatchAngle %= 360

# Diagnostic plots for parameter scaling    
plt.figure()
plt.title("Normalized Process Parameters by Layer")
plt.xlabel("Layer number")
plt.ylabel("Normalized process parameters")
plt.plot(sklearn.preprocessing.scale(layer_times))
plt.plot(sklearn.preprocessing.scale(layer_powers))
plt.plot(sklearn.preprocessing.scale(layer_speeds))
plt.plot(sklearn.preprocessing.scale(layer_widths))
plt.legend(['Time','Power','Speed','Island Width'], loc='upper right')
plt.show()

# print("layer times")
# print(layer_times)
# print("layer powers")
# print(layer_powers)
# print("layer speeds")
# print(layer_speeds)
# print("layer widths")
# print(layer_widths)

# Output Options 
GENERATE_OUTPUT = True
OUTPUT_PNG = True 
OUTPUT_SVG = False 

if GENERATE_OUTPUT:

    # Create/wipe folder
    if not os.path.exists("LayerFiles"):
        os.makedirs("LayerFiles")
    else:
        for f in glob.glob("LayerFiles/*"):
            os.remove(f)

    # Generate new output
    for i in tqdm(range(len(layers)), desc="Generating Plots"):
        fig, ax = plt.subplots()
        pyslm.visualise.plot(
            layers[i], plot3D=False, plotOrderLine=True, plotHatches=True, plotContours=True, handle=(fig, ax))

        if OUTPUT_PNG:
            fig.savefig("LayerFiles/Layer{}.png".format(i), bbox_inches='tight')
        if OUTPUT_SVG:
            fig.savefig("LayerFiles/Layer{}.svg".format(i), bbox_inches='tight')

        plt.cla()
        plt.close(fig)

'''
If we want to change to a subplot-based system, here's most of the code for it:
NUM_ROWS, NUM_COLS = 200, 2
fig, axarr = plt.subplots(NUM_ROWS, NUM_COLS)
pyslm.visualise.plot(layers[i], plot3D=False, plotOrderLine=True,
                                 plotHatches=True, plotContours=True, handle=(fig, axarr[i // NUM_COLS, i % NUM_COLS]))
'''
