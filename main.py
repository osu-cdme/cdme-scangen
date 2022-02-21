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
from pyslm.hatching.islandHatcher import IslandHatcher
from src.output.alsamTypes import SegmentStyle,VelocityProfile,Wobble,Traveler
from pyslm.hatching import hatching, LinearSort
from pyslm.geometry import HatchGeometry
# from pyslm.hatching.multiple import hatch_multiple
from src.standardization.shortening import split_long_vectors
from src.standardization.lengthening import lengthen_short_vectors
from src.island.island import BasicIslandHatcherRandomOrder
from src.scanpath_switching.scanpath_switching import excel_to_array, array_to_instances
from src.output.xml_hdf5_io_2 import XMLWriter, xml_to_hdf5
import src.output.HDF5Util as HDF5Util


# Handle first command line argument, which is a JSON-serialized list of the user's option selections
# Go from our standardized source of fields, or our "schema"
from load_parameters import *
if len(sys.argv) > 1:
    print("First Command Line Argument: " + sys.argv[1], flush=True)
    config_obj = json.loads(sys.argv[1])
    config = parse_config(config_obj)
else: 
    print("First Command Line Argument not specified, using default config", flush=True)
    config = default_config()
print("Post-load config: " + str(config))

# Handle second command line argument, which is a list of paths to add to the python path
# ...it's a (hacky) way to ensure a given library (in our case, pyslm) gets properly loaded from the UI

if len(sys.argv) > 2: 
    print("Second Command Line Argument: " + sys.argv[2], flush=True)
    for path in json.loads(sys.argv[2]):
        print("Appending {} to PYTHONPATH.".format(path), flush=True)
        sys.path.append(path)

#%%

# Initialize Part
# config["Part File Name"] = "nist.stl"
Part = pyslm.Part(config["Part File Name"])
Part.setGeometry('geometry/' + config["Part File Name"])
Part.origin = [0.0, 0.0, 0.0]
Part.rotation = np.array([0, 0, 90])
Part.dropToPlatform()

# General Part Parameters 
LAYER_THICKNESS = config["Layer Thickness"]  # [mm]

# Special scan strategies need additional attributes supplied
if config["Scan Strategy"] == "Island":
    print("Island Hatching!")
    hatcher = IslandHatcher()
elif config["Scan Strategy"] == "Striping": 
    print("Striping hatching!") 
    hatcher = hatching.StripeHatcher()
else:
    print("Default hatching!")
    hatcher = hatching.Hatcher()

# Parameters used in the common hatching class used for any hatcher (default, island, striping)
hatcher.hatchAngle = config["Hatch Angle"] # Hatch Angle
hatcher.layerAngleIncrement = config["Hatch Angle Increment"] # [degrees]
hatcher.hatchDistance = config["Hatch Distance"] # Hatch Distance
hatcher.layerAngleIncrement = config["Hatch Angle Increment"] # Hatch Angle Increment
hatcher.numInnerContours = config["# Inner Contours"] # Num Inner Contours
hatcher.numOuterContours = config["# Outer Contours"] # Num Outer Contours
hatcher.spotCompensation = config["Spot Compensation"] # Spot Compensation
hatcher.volumeOffsetHatch = config["Volume Offset Hatch"] # Volume Offset Hatch 
hatcher.scanContourFirst = config["Contour First"] # Whether to scan contours or hatches first
hatcher.hatchSortMethod = LinearSort() # Which direction, essentially, to do vectors

if config["Scan Strategy"] == "Island":
    hatcher.islandWidth = config["Island Width"]
    hatcher.islandOffset = config["Island Offset"]
    hatcher.islandOverlap = config["Island Overlap"]

elif config["Scan Strategy"] == "Striping": 
    hatcher.stripeWidth = config["Stripe Width"]
    hatcher.stripeOffset = config["Stripe Offset"]
    hatcher.stripeOverlap = config["Stripe Overlap"]

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
# NOTE: file=* is b/c tqdm prints to stderr by default, but to handle properly in ui we need to redirect to stdout
for z in tqdm(np.arange(0, Part.boundingBox[5],
                        LAYER_THICKNESS), desc="Generating Vectors", unit="layers", file=sys.stdout, smoothing=0):

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

    # The layer height is set in integer increment of microns to ensure no rounding error during manufacturing
    layer.z = int(z*1000)
    for geometry in layer.geometry:
        geometry.mid = 1
        geometry.bid = 1

    layers.append(layer)

    # Hatch angle increment is handled inside pyslm

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

# NOTE: This folder name is hardcoded into 'cdme-scangen-ui' as well, so if you change it here, change it there
# Also note that xmlWriter creates the given output folder if it doesn't already
outputDir=os.path.abspath('XMLOutput')
xmlWriter = XMLWriter(outputDir)

#outputs xml layer files
xmlWriter.output_xml(layers,segStyleList,vProfileList, config["Contour Default ID"], config["Hatch Default ID"])

#outputs .scn file in same location as xml layer files
# xmlWriter.output_zip()

#%%
#converts xlm output to an hdf5 file for use in external simulator
# The UI disables this automatically (as it has an alternate mechanism for HDF5 export) and the schema has it disabled by default
if config["Output .HDF5"]: 
    hdf5Dir=os.path.abspath('HDF5Output')
    HDF5Util.HDF5Util(os.path.abspath('XMLOutput'),'HDF5FromSCN.hdf5').convertSCNtoHDF5()
