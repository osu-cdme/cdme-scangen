
"""
Example showing how to use this project to output XML files for the
ALSAM controller
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from tqdm import tqdm

# Local Imports
import pyslm
import pyslm.visualise
import pyslm.analysis
import pyslm.geometry
from pyslm.hatching import hatching
from pyslm.geometry import HatchGeometry
from src.standardization.shortening import split_long_vectors
from src.standardization.lengthening import lengthen_short_vectors
from src.island.island import BasicIslandHatcherRandomOrder
import src.output.xml_config as xml_config
from src.output.xml_io import ConfigFile, XMLWriter


'''
STEP 1: Initialize part, slice the part, and generate scan path (per main.py)
'''

# Import Excel Parameters
def eval_bool(str):
    return True if str == "Yes" else False

values = pd.ExcelFile(r'config.xlsx').parse(0)["Value"]
PART_NAME = values[2] 

PLOT_TIME = eval_bool(values[15]) 
PLOT_CHANGE_PARAMS = eval_bool(values[16]) 
PLOT_POWER = eval_bool(values[17]) 
PLOT_SPEED = eval_bool(values[18]) 

# Initialize Part
Part = pyslm.Part('nut')
Part.setGeometry('geometry/' + PART_NAME)
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
      
    layers.append(layer)

    # Change hatch angle every layer
    myHatcher.hatchAngle += 66.7
    myHatcher.hatchAngle %= 360


'''
STEP 2: Get list of coordinates, one list for each trajectory, e.g. hatches and contours.        
'''

#Coordinates For Hatches - flat 1D array, segments 0:1, 2:3, 4:5, etc.
hatch_layers = []
for layer in layers:
    hatches = np.array([hatchGeom.coords for hatchGeom in layer.getHatchGeometry()], dtype='object').reshape(-1)
    hatch_layers.append(hatches)
    
#Coordinates For Contours - flat 1D array, segments 0:1, 2:3, 4:5, etc.
contour_layers = []
for layer in layers:
    contours = np.array([contourGeom.coords for contourGeom in layer.getContourGeometry()], dtype='object').reshape(-1)
    contour_layers.append(contours)
    

'''
STEP 3: Write the XML files and zip in a .scn        
'''

output_path = 'xml'
config = ConfigFile('OASIS Ex_ Parameter_quality_nut_2.xls')
xml_out = XMLWriter(output_path, config)   
xml_out.output_xml(contour_layers, hatch_layers)
xml_out.output_zip()
















