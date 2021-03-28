"""
Created on Wed Feb  3 14:37:32 2021

@author: harsh

Example showing how to use pyPowderBedFusion for generating scan vector
"""

# Standard Library Imports
import os
import glob

# Third-Party Imports
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm

# Local Imports
import PowderBedFusion
from PowderBedFusion import hatching

Part = PowderBedFusion.Part('Parameter_quality_nut_2')
Part.setGeometry('Parameter_quality_nut_2.stl')
Part.origin = [0.0, 0.0, 0.0]
Part.rotation = np.array([0, 0, 90])
Part.dropToPlatform()

# Create a BasicIslandHatcher object for performing any hatching operations (
myHatcher = hatching.BasicIslandHatcher()
myHatcher.islandWidth = 3.0
myHatcher.stripeWidth = 5.0

# Set the base hatching parameters which are generated within Hatcher
myHatcher.hatchAngle = 45  # [°] The angle used for the islands
# [mm] Offset between internal and external boundary
myHatcher.volumeOffsetHatch = 0.08
# [mm] Additional offset to account for laser spot size
myHatcher.spotCompensation = 0.06
myHatcher.numInnerContours = 2
myHatcher.numOuterContours = 1
myHatcher.hatchSortMethod = hatching.AlternateSort()

# Set the layer thickness
LAYER_THICKNESS = 1  # [mm]

# Perform the hatching operations
layers = []

t = tqdm(np.arange(0, Part.boundingBox[5], LAYER_THICKNESS))
t.set_description("Processing Layers")
for z in t:

    geom_slice = Part.getVectorSlice(z)  # Slice layer
    layer = myHatcher.hatch(geom_slice)  # Hatch layer

    # The layer height is set in integer increment of microns to ensure no rounding error during manufacturing
    layer.z = int(z*1000)
    for geometry in layer.geometry:
        geometry.mid = 1
        geometry.bid = 1
    layers.append(layer)

    # Explicitly refresh progress bar
    t.refresh()

bstyle = PowderBedFusion.genLayer.BuildStyle()
bstyle.bid = 1
bstyle.laserSpeed = 200.0  # [mm/s]
bstyle.laserPower = 200  # [W]#
bstyle.pointDistance = 60  # (60 microns)
bstyle.pointExposureTime = 30  # (30 micro seconds)

model = PowderBedFusion.genLayer.Model()
model.mid = 1
model.buildStyles.append(bstyle)
resolution = 0.2

# Plot the results
# PowderBedFusion.outputtools.plotLayers(layers[0:len(layers)])
# plt.show()

GENERATE_OUTPUT = True
if GENERATE_OUTPUT:

    # Create/wipe folder
    if not os.path.exists("LayerFiles"):
        os.makedirs("LayerFiles")
    else:
        for f in glob.glob("LayerFiles/*"):
            os.remove(f)

    # Generate new output
    t = tqdm(range(len(layers)))
    t.set_description("Generating Plots")
    for i in t:
        fig, ax = plt.subplots()
        PowderBedFusion.outputtools.plot(
            layers[i], plot3D=False, plotOrderLine=False, plotHatches=True, plotContours=True, handle=(fig, ax))
        fig.savefig("LayerFiles/Layer{}.png".format(i), bbox_inches='tight')
        plt.cla()
        plt.close(fig)

'''
If we want to change to a subplot-based system, here's most of the code for it:
NUM_ROWS, NUM_COLS = 200, 2
fig, axarr = plt.subplots(NUM_ROWS, NUM_COLS)
PowderBedFusion.outputtools.plot(layers[i], plot3D=False, plotOrderLine=True,
                                 plotHatches=True, plotContours=True, handle=(fig, axarr[i // NUM_COLS, i % NUM_COLS]))
'''
