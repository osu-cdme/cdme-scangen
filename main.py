# Standard Library Imports
import sys
import os
import glob
import time
import statistics as stats
import json 

# Third-Party Imports
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import sklearn.preprocessing as skp
import pandas as pd 
from pprint import pprint 

# Local Imports
sys.path.insert(0, os.path.abspath("./")) # Hacky way to ensure Python can find local modules
sys.path.insert(0, os.path.abspath("pyslm")) 
print(sys.path)
import pyslm
import pyslm.visualise
import pyslm.analysis
import pyslm.geometry
from src.output.alsamTypes import SegmentStyle,VelocityProfile,Wobble,Traveler
from pyslm.hatching import hatching
from pyslm.geometry import HatchGeometry
# from pyslm.hatching.multiple import hatch_multiple
from src.standardization.shortening import split_long_vectors
from src.standardization.lengthening import lengthen_short_vectors
from src.island.island import BasicIslandHatcherRandomOrder
from src.scanpath_switching.scanpath_switching import excel_to_array, array_to_instances
from src.output.xml_hdf5_io_2 import XMLWriter


# Handle first command line argument, which is a JSON-serialized list of the user's option selections
# Go from our standardized source of fields, or our "schema"
from load_parameters import *
if len(sys.argv) > 1:
    print("First Command Line Argument: " + sys.argv[1])
    config_obj = json.loads(sys.argv[1])
    config = parse_config(config_obj)
else: 
    print("First Command Line Argument not specified, using default config")
    config = default_config()
print("Post-load config: " + str(config))

# Handle second command line argument, which is a list of paths to add to the python path
# ...it's a (hacky) way to ensure a given library (in our case, pyslm) gets properly loaded from the UI

if len(sys.argv) > 2: 
    print("Second Command Line Argument: " + sys.argv[2])
    for path in json.loads(sys.argv[2]):
        print("Appending {} to PYTHONPATH.".format(path))
        sys.path.append(path)

#%%

if "Write Debug Info" in config and config["Write Debug Info"]:
    print("Logging debug information to `debug.txt`.")
    debug_file = open("debug.txt", "w")
    debug_file.write("Input Parameters\n")
    debug_file.write("--------------------\n")
    for key, value in config.items():
        debug_file.write("{}: {}\n".format(key, value))
    debug_file.write("\n")

"""
USE_SCANPATH_SWITCHING = False
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
"""

# Initialize Part
# config["Part File Name"] = "Cone_1.stl"
Part = pyslm.Part(config["Part File Name"])
Part.setGeometry('geometry/' + config["Part File Name"])
Part.origin = [0.0, 0.0, 0.0]
Part.rotation = np.array([0, 0, 90])
Part.dropToPlatform()

# General Part Parameters 
LAYER_THICKNESS = config["Layer Thickness"]  # [mm]

# Special scan strategies need additional attributes supplied
if config["Scan Strategy"] == "island":
    print("Island Hatching!")
    hatcher = hatching.IslandHatcher()
elif config["Scan Strategy"] == "Striping": 
    print("Striping hatching!") 
    hatcher = hatching.StripeHatcher()
else:
    print("Default hatching!")
    hatcher = hatching.Hatcher()

# Parameters used in the common hatching class used for any hatcher (default, island, striping)
hatcher.hatchAngle = config["Hatch Angle"] # Hatch Angle 
hatcher.hatchDistance = config["Hatch Distance"] # Hatch Distance
hatcher.layerAngleIncrement = config["Hatch Angle Increment"] # Hatch Angle Increment
hatcher.numInnerContours = config["# Inner Contours"] # Num Inner Contours
hatcher.numOuterContours = config["# Outer Contours"] # Num Outer Contours
hatcher.spotCompensation = config["Spot Compensation"] # Spot Compensation
hatcher.volumeOffsetHatch = config["Volume Offset Hatch"] # Volume Offset Hatch 

# Hatch Sort Method
if config["Hatch Sorting Method"]=='Alternate':
    hatcher.hatchSortMethod = hatching.AlternateSort()
elif config["Hatch Sorting Method"]=='Linear':
    hatcher.hatchSortMethod = hatching.LinearSort()
elif config["Hatch Sorting Method"]=='Greedy':
    hatcher.hatchSortMethod = hatching.GreedySort()
else:
    print("Invalid hatch sorting method " + config["Hatch Sorting Method"] + " passed in.")
    sys.exit(-1)

if config["Scan Strategy"] == "Island":
    hatcher.islandWidth = config["Island Width"]
    hatcher.islandOffset = config["Island Offset"]
    hatcher.islandOverlap = config["Island Overlap"]

elif config["Scan Strategy"] == "Striping": 
    print("Stripe Width: " + str(config["Stripe Width"]))
    hatcher.stripeWidth = config["Stripe Width"]
    print("Stripe Offset: " + str(config["Stripe Offset"]))
    hatcher.stripeOffset = config["Stripe Offset"]
    print("Stripe Overlap: " + str(config["Stripe Overlap"]))
    hatcher.stripeOverlap = config["Stripe Overlap"]

# TODO: Figure out what these were used for and reimplement the system
# MIN_POWER_LVL = min(config_powers.keys())
# MAX_POWER_LVL = max(config_powers.keys())

# Instantiate model and set model parameters
model = pyslm.geometry.Model()
model.mid = 1

segStyleList=[]
# pull segment style info from schema
for style in config["Segment Styles"]:
    ## Create new SegmentStyle object that contains segment style info
    segStyle = SegmentStyle()   
    
    # Segment Style Info 
    segStyle.id=style["id"] # TYPE: string
    segStyle.vProfileID=style["velocityProfileID"] # TYPE: string
    segStyle.laserMode=style["laserMode"] # TYPE: string from set {"Independent", "FollowMe"}
    
    # Create traveler list and add traveler objects to it
    travelers=[]
    for item in style["travelers"]:
        traveler=Traveler()
        traveler.id=item["id"] # TYPE: int
        traveler.syncDelay=item["syncDelay"]
        traveler.power=item["power"]  # TYPE: float (Watts)
        traveler.spotSize=item["spotSize"]  # TYPE: float (microns)

        # If wobble tag exists
        if item["wobble"] is not None:
            #pull wobble info
            wobble=Wobble()
            wobble.on=item["wobble"]["on"]
            wobble.freq=item["wobble"]["freq"]
            wobble.shape=item["wobble"]["shape"]
            wobble.transAmp=item["wobble"]["transAmp"]
            wobble.longAmp=item["wobble"]["longAmp"]
            traveler.wobble=wobble

        travelers.append(traveler)
    # Attach travelers to SegmentStyle object
    segStyle.travelers=travelers
    segStyleList.append(segStyle)
    
vProfileList=[]
for style in config["Velocity Profiles"]:
    ## Create new VelocityProfile object that contains velocity profile info
    vProfile = VelocityProfile()   
    # Velocity Profile Info
    vProfile.id=style["id"] # TYPE: string
    vProfile.velocity=style["velocity"] # TYPE: float (mm/s)
    vProfile.mode=style["mode"] # TYPE: string from set {"Delay", "Auto"}
    vProfile.laserOnDelay=style["laserOnDelay"] # TYPE: float (microseconds)
    vProfile.laserOffDelay=style["laserOffDelay"] # TYPE: float (microseconds)
    vProfile.jumpDelay=style["jumpDelay"] # TYPE: float (microseconds)
    vProfile.markDelay=style["markDelay"] # TYPE: float (microseconds)
    vProfile.polygonDelay=style["polygonDelay"] # TYPE: float (microseconds)

    vProfileList.append(vProfile)

resolution = 0.2

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
# layer_segstyle = 11
# layer_power = model.buildStyles[layer_segstyle].laserPower
# layer_speed = model.buildStyles[layer_segstyle].laserSpeed
for z in tqdm(np.arange(0, Part.boundingBox[5],
                        LAYER_THICKNESS), desc="Processing Layers"):

    geom_slice = Part.getVectorSlice(z)  # Slice layer

    # pyslm doesn't error out if Trimesh returns an empty slice, so we have to check
    # This generally only occurs at the very beginning or end of the part 
    if geom_slice == []:
        continue

    if "Use Scanpath Switching" in config and config["Use Scanpath Switching"]:
        hatchers, areas = [], []
        for pair in scanpath_area_pairs:
            hatchers.append(pair[0])
            areas.append(pair[1])
        layer = hatch_multiple(hatchers[1:], areas[1:], hatchers[0], geom_slice, z)
    else:
        layer = hatcher.hatch(geom_slice)  # Hatch layer

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
    # layer_times.append(pyslm.analysis.getLayerTime(layer, [model]))
    # layer_powers.append(layer_power)
    # layer_speeds.append(layer_speed)
    # layer_segstyles.append(model.buildStyles[layer_segstyle].name)
    
    '''
    Scale parameters by how much time it's taking to scan layers.
    Attempts to address "pyramid problem" where as you move up building a part 
    shaped like a pyramid, layers take less time, and there's less time for 
    things to cool off, which leads to problems with the part.
    '''
    ACTIVATION_DIFF = .5
    """
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
    """
  
    layers.append(layer)

    # Change hatch angle every layer
    # hatch.hatchAngle += 66.7
    # myHatcher.hatchAngle %= 360

'''
If pulling .scn output from process, the data is available here for conversion

Data available is in Lists after slicing and hatching completes

    layer_times->list of ints describing time to execute each layer: generated from analysis of layer object by pyslm package
    layer_powers->list of int or string arrays describing laser power
    layer_speeds->list of ints describing laser speed
    layer_segstyles->list of layer_segstyle objects
    layers->list of instances Layer class objects defined in pyslm
'''

#%%

'''
This chunk should be able to go where needed. It requires an output directory to an empty or new folder so the zip output can produce a correct .scn file
will need to ensure input sanitation when UI hooks into this component. 
'''
# if config["Output .scn"]:

# Create 'output' directory if it doesn't exist\

# NOTE: This folder name is hardcoded into 'cdme-scangen-ui' as well, so if you change it here, change it there
# Also note that xmlWriter creates the given output folder if it doesn't already
outputDir=os.path.abspath('XMLOutput')
xmlWriter = XMLWriter(outputDir)

#outputs xml layer files
xmlWriter.output_xml(layers,segStyleList,vProfileList, config["Contour Default ID"], config["Hatch Default ID"])

#outputs .scn file in same location as xml layer files
xmlWriter.output_zip()

#%%
'''
STEP 3: Visualization Outputs       
'''

if "Output Plots" in config and config["Output Plots"]:

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
            layers[i], plot3D=False, plotOrderLine=config["Plot Centroids"], plotHatches=config["Plot Hatches"],\
                 plotContours=config["Plot Contours"], plotJumps=config["Plot Jump Vectors"], handle=(fig, ax))

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
