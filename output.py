#%%
"""
HEADER:
    output.py is an example for how to use PySLM and this project to output 
    XML files for the ALSAM controller and HDF5 files for research data
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
import src.output.config_build as config_build
from src.output.xml_hdf5_io import ConfigFile, XMLWriter, HDF5Writer, xml_to_hdf5, hdf5_to_xml
from pyslm.geometry import ScanMode


#%%
'''
STEP 1: Initialize part, build, and program parameters
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

if(eval_bool(values[30])):
    SCAN_MODE = ScanMode.ContourFirst
else:
    SCAN_MODE = ScanMode.HatchFirst

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

#%%
'''
STEP 2: Slice part and generate scan paths. Format data for XML and HDF5
'''
# Keep track of parameters
layers = []
layers_times = []
layers_powers = []
layers_speeds = []
layers_segstyles = []
layers_paths = np.empty(len(np.arange(0, Part.boundingBox[5],
                        LAYER_THICKNESS)), dtype=object)

segstyle_index = 30
layer_power = model.buildStyles[segstyle_index].laserPower
layer_speed = model.buildStyles[segstyle_index].laserSpeed
i = 0
for z in tqdm(np.arange(0, Part.boundingBox[5],
                        LAYER_THICKNESS), desc="Processing Layers"):

    geom_slice = Part.getVectorSlice(z)  # Slice layer
    layer = myHatcher.hatch(geom_slice)  # Scan strategy / slicer
    
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
    
    hatch_geoms = layer.getHatchGeometry()
    if len(hatch_geoms) > 0:
        hatches = np.vstack([hatch_geom.coords.reshape(-1, 2) for hatch_geom in hatch_geoms])
        
    contour_geoms = layer.getContourGeometry()
    if len(contour_geoms) > 0:
        contours = np.vstack([contour_geom.coords.reshape(-1, 2) for contour_geom in contour_geoms])
    
    # Best practice to do contour first
    paths = [None, None]
    if SCAN_MODE == ScanMode.ContourFirst:
        paths[0] = contours
        paths[1] = hatches
    else:
        paths[0] = hatches
        paths[1] = contours
    
    layers_paths[i] = paths

    # The layer height is set in integer increment of microns to ensure no rounding error during manufacturing
    layer.z = int(z*1000)
    
    for geometry in layer.geometry:
        geometry.mid = 1
        geometry.bid = 1
    
    '''
    Scale parameters by how much time it's taking to scan layers.
    Attempts to address "pyramid problem" where as you move up building a part 
    shaped like a pyramid, layers take less time, and there's less time for 
    things to cool off, which leads to problems with the part.
    '''
    ACTIVATION_DIFF = .5
    if CHANGE_PARAMS and len(layers_times) > 1:
        dt = np.diff(layers_times)
        if CHANGE_POWER:
        # As time goes down, so should power
            if dt[len(dt)-1] > ACTIVATION_DIFF and segstyle_index < MAX_POWER_LVL:
                segstyle_index += 1
            elif dt[len(dt)-1] < -ACTIVATION_DIFF and segstyle_index > MIN_POWER_LVL:
                segstyle_index -= 1
            layer_power = model.buildStyles[segstyle_index].laserPower
        if CHANGE_SPEED:
        # As time goes down, so should speed
            layer_speed = model.buildStyles[segstyle_index].laserSpeed

    
    layers.append(layer)
    
    # Get parameters for each layer and collect
    layers_times.append(pyslm.analysis.getLayerTime(layer, [model]))
    layer_powers = []
    layer_speeds = []
    for k in range(len(contours)+len(hatches)-1):
        layer_powers.append(layer_power)
        layer_speeds.append(layer_speed)
    layers_powers.append(layer_powers)
    layers_speeds.append(layer_speeds)
    
    layers_segstyles.append(model.buildStyles[segstyle_index].name)

    # Change hatch angle every layer
    myHatcher.hatchAngle += 66.7
    myHatcher.hatchAngle %= 360
    
    i+=1
    
        

    
#%%
'''
STEP 3 part 1: Write the XML files and zip       
'''

output_dir = 'xml'
config = ConfigFile('build_config.xls')
xml_out = XMLWriter(output_dir, config)   
xml_out.output_xml(layers_paths, layers_segstyles, SCAN_MODE)
xml_out.output_zip()

#%%
'''
STEP 3 part 2: Write to the HDF5 File       
'''

output_dir = 'hdf5'
file_name = PART_NAME[0:len(PART_NAME)-4] + ".hdf5"
hdf5_out = HDF5Writer(output_dir)
hdf5_out.output_hdf5(layers_paths, layers_powers, layers_speeds, file_name, SCAN_MODE)

#%%
'''
OPTIONAL: XML --> HDF5 Conversion
'''
in_dir = 'xml'
out_file = PART_NAME[0:len(PART_NAME)-4] + ".hdf5"
xml_to_hdf5(in_dir, out_file)

#%%
'''
OPTIONAL: HDF5 --> XML Conversion
'''
in_path = 'hdf5/nut.hdf5'
out_dir = 'xml'
config = ConfigFile('build_config.xls')
hdf5_to_xml(in_path, out_dir, config)








