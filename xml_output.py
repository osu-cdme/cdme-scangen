
"""
This file also serves as an example showing how to use this project to output XML files for the
ALSAM controller
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import statistics as stats
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
from pyslm.geometry import ScanMode


'''
STEP 1: Initialize part, slice the part, and generate scan path (per main.py)
'''

# Import Excel Parameters
def eval_bool(str):
    return True if str == "Yes" else False

values = pd.ExcelFile(r'config.xlsx').parse(0)["Value"]
config_vprofiles = pd.ExcelFile(r'build_config.xls').parse(3,header=7)['Velocity Profile for build segments\nVP for jumps is selected in Region profile'][3:]
#config_speeds = pd.ExcelFile(r'build_config.xls').parse(2, header=5)['Velocity\n(mm/s)']
config_segstyles = pd.ExcelFile(r'build_config.xls').parse(3, header=7)['SegmentStyle ID\nMay be integer or text'][3:]
config_powers = pd.ExcelFile(r'build_config.xls').parse(3, header=7)['Lead laser power (Watts)'][3:]
segstyles = pd.DataFrame({'SegStyles':np.array(config_segstyles),
                          'Powers':np.array(config_powers),
                          'VelocityProfiles':np.array(config_vprofiles)})

PART_NAME = values[2] 

PLOT_TIME = eval_bool(values[15]) 
CHANGE_PARAMS = eval_bool(values[3]) 
CHANGE_POWER = eval_bool(values[4]) 
CHANGE_SPEED = eval_bool(values[5])

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
    if CHANGE_PARAMS and len(layer_times) > 1:
        dt = np.diff(layer_times)
        if CHANGE_POWER:
        # As time goes down, so should power
            if dt[len(dt)-1] > ACTIVATION_DIFF and layer_segstyle < MAX_POWER_LVL:
                layer_segstyle += 1
            elif dt[len(dt)-1] < -ACTIVATION_DIFF and layer_segstyle > MIN_POWER_LVL:
                layer_segstyle -= 1
            layer_power = model.buildStyles[layer_segstyle].laserPower
        if CHANGE_SPEED:
        # As time goes down, so should speed
            layer_speed = model.buildStyles[layer_segstyle].laserSpeed

    
    layers.append(layer)

    # Change hatch angle every layer
    myHatcher.hatchAngle += 66.7
    myHatcher.hatchAngle %= 360


'''
STEP 2: Get list of coordinates, one list for each trajectory, e.g. hatches and contours.
        Note that SegStyle parameters for each layer, e.g. power and speed,
        are stored in layer_segstyles       
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
STEP 3: Write the XML files and zip       
'''

output_path = 'xml'
scan_mode = ScanMode.ContourFirst # Currently, scan mode is the same for all layers. We should change this at some point.
config = ConfigFile('build_config.xls')
xml_out = XMLWriter(output_path, config)   
xml_out.output_xml(contour_layers, hatch_layers, layer_segstyles, scan_mode)
xml_out.output_zip()
print(layer_segstyles)
















