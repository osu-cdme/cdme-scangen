# -*- coding: utf-8 -*-
"""
Created on Wed Feb  3 14:37:32 2021

@author: harsh
"""
"""
example showing how to use pyPowderBedFusion for generating scan vector
"""

import PowderBedFusion
from PowderBedFusion import hatching as hatching
import numpy as np
import matplotlib.pyplot as plt

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
myHatcher.hatchAngle = 45 # [°] The angle used for the islands
myHatcher.volumeOffsetHatch = 0.08 # [mm] Offset between internal and external boundary
myHatcher.spotCompensation = 0.06 # [mm] Additional offset to account for laser spot size
myHatcher.numInnerContours = 2
myHatcher.numOuterContours = 1
myHatcher.hatchSortMethod = hatching.AlternateSort()

# Set the layer thickness
layerThickness = 1 # [mm]

#Perform the hatching operations
print('Hatching Started')

layers = []


for z in np.arange(0, Part.boundingBox[5], layerThickness):
    # Slice the boundary
    geomSlice = Part.getVectorSlice(z)

    # Hatch the boundary using myHatcher
    layer = myHatcher.hatch(geomSlice)

    # The layer height is set in integer increment of microns to ensure no rounding error during manufacturing
    print('Layer # ' + str(z) + ' Started')
    layer.z = int(z*1000)
    print('Layer # ' + str(z) + ' Complete\n')
    layers.append(layer)
    
# we have to assign a model and build style id to the layer geometry
for layer in layers:
  for layerGeom in layer.geometry:
    layerGeom.mid = 1
    layerGeom.bid = 1
    
bstyle = PowderBedFusion.genLayer.BuildStyle()
bstyle.bid = 1
bstyle.laserSpeed = 200.0 # [mm/s]
bstyle.laserPower = 200 # [W]#
bstyle.pointDistance = 60 # (60 microns)
bstyle.pointExposureTime = 30 #(30 micro seconds)
    

model = PowderBedFusion.genLayer.Model()
model.mid = 1
model.buildStyles.append(bstyle)
resolution = 0.2

# Plot the layer geometries using matplotlib
PowderBedFusion.outputtools.plotLayers(layers[0:len(layers)])

# Plot the corresponding layers
i=0
for layer in layers:
    name = 'Layer Files for Parameter quality nut 2/Layer' + str(i) + '.pdf'
    fig, ax = plt.subplots(figsize=(20, 10))
    PowderBedFusion.outputtools.plot(layers[i], plot3D=False, plotOrderLine=True, plotArrows=True, handle=(fig,ax))
    fig.savefig(name, bbox_inches='tight')
    print(name)
    plt.cla()
    plt.close(fig) 
    i = i+1