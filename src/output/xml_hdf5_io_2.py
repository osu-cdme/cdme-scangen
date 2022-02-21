
import pandas as pd
import numpy as np
from lxml.etree import Element, SubElement, xmlfile, tostring
import xml.etree.ElementTree as et
from typing import List, Dict
from . import config_build as settings
from datetime import datetime
from shapely.geometry import Polygon, MultiLineString
from zipfile import ZipFile
import os
from os.path import basename
from xml.sax.saxutils import unescape
from pyslm.geometry.geometry import ScanMode, BuildStyle, Layer,Model ## Directed import to version of pyslm included in scan-gen package
import h5py
import glob
from src.output.alsamTypes import SegmentStyle,Wobble,VelocityProfile,Traveler
from tqdm import tqdm # Progress bar 


'''
V 2.0 removes the configFile class. will be loading lists generated by pySLM into xmlWriter instead, NOTE: all functions in this io assume CDME's implementation pySLM output.

Current Task:
TODO: Defined new classes to contain segment style, traveler,velocity profile, and wobble information. Need to rewrite XMLWriter to take from new classes

In Progress:
hdf5_to_xml() <-- needs updated for deletion of configFile dependency/input type

'''
'''
Data available from pySLM output

    layer_times->list of ints describing time to execute each layer: generated from analysis of layer object by pyslm package
    layer_powers->list of int or string arrays describing laser power: property of layer_segstyle object
    layer_speeds->list of ints describing laser speed: property of layer_segstyle object
    layer_segstyles->list of layer_segstyle objects
    
    layers->list of instances Layer class objects defined in pyslm
'''
"""
Writes ALSAM controller XML files for L-PBF
output_dir needs to be existing directory
"""


class XMLWriter():
    #Initializes writer with output directory
    def __init__(self, output_dir: str):
        self.out = output_dir

    '''
    generates a .xml file for a single layer of a print in the format required to convert to a .scn for use by the open controller
    '''
    #TODO: write fails when directory does not exist. Need to add function that creates a new directory when new write starts.
    def write_layer(self,layer:Layer, layer_num: int,SegmentStyleList:list[SegmentStyle],velocityProfileList:list[VelocityProfile], defaultContourSegmentStyleID, defaultHatchSegmentStyleID):
        #create new file at end of directory provided for the layer
        with open(os.path.join(self.out , 'scan_' + str(layer_num) + '.xml'),'wb') as layerFile:
            #write to file the layer
            with xmlfile(layerFile) as xf:
              with xf.element('Layer'):
                xf.write(self.make_header(layer_num), pretty_print=True)
                xf.write(self.make_velocity_profiles(velocityProfileList), pretty_print=True)
                xf.write(self.make_segment_styles(SegmentStyleList), pretty_print=True)
                xf.write(self.make_traj_list(layer, defaultContourSegmentStyleID, defaultHatchSegmentStyleID), pretty_print=True) #<--TODO:ScanMode selector function removed for redesign, add back in
    
    '''
    Returns string that opens the <Layer> and <Header> fills in the header of the OASIS xml format and closes </header>. Required at the beginning of every layer file.
    Requires:
    schema version <--hard coded
    layer number <--passed in but generated by calling function
    layer thickness <--set by user and passed in from json file, TODO: design hook for edit. currently hard coded to .05
    dosing factor <--set by user and passed in from json file, TODO: design hook for edit. currently hard coded to 1.75
    '''
    def make_header(self,layerNum: int):
       
        header=Element('Header')
        SubElement(header, 'AmericaMakesSchemaVersion').text = "2020-03-23"
        SubElement(header, 'LayerNum').text = str(layerNum)
        SubElement(header, 'LayerThickness').text = ".05"
        SubElement(header, 'DosingFactor').text = "1.75"
        
        return header 

    ## TODO: Changed format of buildstyle object, will need to change references to it in velocity profile and segment style generation
    '''
    Returns string that opens and closes the <VelocityProfileList> of <VelocityProfile>(s). 2nd entry of layer file. 
    
    Must return the entire list of profiles.
    Requires:
    length of all lists passed in must be equal
    id <-- int that identifies a profile's position in the list, generated by this function
    velocity 
    mode 
    laser on delay 
    mark delay 
    polygon delay 
    '''
    def make_velocity_profiles(self,vProfiles:list[VelocityProfile()]):
        vpList=Element('VelocityProfileList')
        
        for profile in vProfiles:
            vProfile=SubElement(vpList,'VelocityProfile')
            SubElement(vProfile,'ID').text=profile.id
            SubElement(vProfile,'Velocity').text=str(profile.velocity)
            SubElement(vProfile,'Mode').text=str(profile.mode)
            SubElement(vProfile,'LaserOnDelay').text=str(profile.laserOnDelay) 
            SubElement(vProfile,'LaserOffDelay').text=str(profile.laserOffDelay)
            SubElement(vProfile,'JumpDelay').text=str(profile.jumpDelay)
            SubElement(vProfile,'MarkDelay').text=str(profile.markDelay)
            SubElement(vProfile,'PolygonDelay').text=str(profile.polygonDelay)


        return vpList

    '''
    Returns string that opens and closes the <SegmentStyleList> of <SegmentStyle>(s). 3rd entry of layer file. 
    Gets list of buildstyles from Model class generated by pyslm
    Must return the entire list of profiles.
    Requires:
    id
    velocity profile id
    laser mode
    traveler
    id(under traveler)
    sync delay
    power
    spotsize
    '''
    def make_segment_styles(self,segStyleList: list[SegmentStyle]):
        ssList=Element('SegmentStyleList')

        
        for style in segStyleList:
            sStyle = SubElement(ssList,'SegmentStyle')
            SubElement(sStyle, 'ID').text =style.id
            SubElement(sStyle, 'VelocityProfileID').text =style.vProfileID
            SubElement(sStyle, 'LaserMode').text =str(style.laserMode)

            travelerList=style.travelers
            travelers=SubElement(sStyle, 'Travelers')
            for entry in travelerList:
                traveler=SubElement(travelers, 'Traveler')
                SubElement(traveler, 'ID').text = str(entry.id)
                SubElement(traveler, 'SyncDelay').text =str(entry.syncDelay)
                SubElement(traveler, 'Power').text =str(entry.power)
                SubElement(traveler, 'SpotSize').text =str(entry.spotSize)

        return ssList

    '''
    Returns string that opens and closes the <TrajectoryList> of <Trajectory>(s) which are a list of <segment>(s).
    Requires:
    segment id<--unique int used to identify individual paths, generated in this function
    segment style<--references a segment style ID from the <SegmentStyleList>
    X and Y coordinates<--passed in.
    '''
    def make_traj_list(self,layer: Layer, defaultContourSegmentStyleID: str, defaultHatchSegmentStyleID: str):
        
        tList=Element('TrajectoryList')

        # create node for >1 trajectory group           
        traj = SubElement(tList, 'Trajectory')
        SubElement(traj, 'TrajectoryID').text = '0'
        SubElement(traj, 'PathProcessingMode').text = "sequential" # add control flow for multipart.

        # TODO: There's an option in the UI whether to do contours or hatches first; need to pass that value in here and respect their choice

        ##write contours
        
        for group in layer.getContourGeometry():
            contours_path =SubElement(traj,'Path')
            
            SubElement(contours_path,'Type').text="contour"
            SubElement(contours_path,"Tag").text="part1"
            SubElement(contours_path,"NumSegments").text=str(group.numContours())
            SubElement(contours_path,"SkyWritingMode").text="0"

            ## Get array of coordinates in numpy ndarray and its number of rows which represents the number of segments
            coordinates=group.coords
            numRows=coordinates.shape[0]

            ## Generate start point
            startPair=coordinates[0] # Weird stuff, don't worry about it, seems to work
            Start=SubElement(contours_path,"Start")
            SubElement(Start,"X").text=str(round(startPair[0], 4))
            SubElement(Start,"Y").text=str(round(startPair[1], 4))

            ## Generate every segment
            for i in range(1,numRows):
                segment=SubElement(contours_path,"Segment")
                SubElement(segment,"SegmentID").text=str(i)
                SubElement(segment,"SegStyle").text=str(defaultContourSegmentStyleID)
                end=SubElement(segment,"End")
                # round to thousandths place 
                SubElement(end,"X").text=str(round(coordinates[i,0], 4))  ##assuming coordinates is a 2 by n array of x,y coordinates
                SubElement(end,"Y").text=str(round(coordinates[i,1], 4))

        ##write hatches
        for group in layer.getHatchGeometry():
            hatches_path = SubElement(traj,'Path')
            
            SubElement(hatches_path,'Type').text="hatch"
            SubElement(hatches_path,"Tag").text="part1"
            SubElement(hatches_path,"NumSegments").text=str(group.numHatches())
            SubElement(hatches_path,"SkyWritingMode").text="0"

            ## Get array of coordinates in numpy ndarray and its number of rows which represents the number of segments
            coordinates=group.coords
            numRows=coordinates.shape[0]

            ## Generate start point
            firstHatch=coordinates[0]
            Start=SubElement(hatches_path,"Start")
            SubElement(Start,"X").text=str(round(firstHatch[0][0], 4))
            SubElement(Start,"Y").text=str(round(firstHatch[0][1], 4))

            for i in range(len(coordinates)):
                hatch = coordinates[i]

                # Burn the hatch 
                hatchVec=SubElement(hatches_path,"Segment")
                SubElement(hatchVec,"SegmentID").text=str(i)
                SubElement(hatchVec,"SegStyle").text=str(defaultHatchSegmentStyleID)
                hatchVecEnd=SubElement(hatchVec,"End")
                SubElement(hatchVecEnd,"X").text=str(round(hatch[1][0], 4))
                SubElement(hatchVecEnd,"Y").text=str(round(hatch[1][1], 4))

                # If next hatch exists, add jump vector to next hatch
                if (i < len(coordinates) - 1):
                    nextHatch=coordinates[i+1]
                    jumpVec = SubElement(hatches_path,"Segment")
                    SubElement(jumpVec, "SegmentID").text=str(i)
                    SubElement(jumpVec, "SegStyle").text=str('jumps')
                    jumpVecEnd=SubElement(jumpVec, "End")
                    SubElement(jumpVecEnd,"X").text=str(round(nextHatch[0][0], 4))
                    SubElement(jumpVecEnd,"Y").text=str(round(nextHatch[0][1], 4))

        return tList


    """
    Need to review inputs to this one, can have better references for readability
    """
    
    def output_xml(self, layers: List[Layer], segmentStyleList:list[SegmentStyle],vProfileList:list[VelocityProfile], defaultContourSegmentStyleID: str, defaultHatchSegmentStyleID: str):
        
        # Create/wipe folder
        if not os.path.exists(self.out):
            os.makedirs(self.out)
        else:
            for f in glob.glob(self.out+'\*'):
                os.remove(f)  
        
        # TODO: Rewrite UI to parse tqdm output instead of the previous print statements here 
        import sys
        for i in tqdm(range(0, len(layers)), desc='Output -> XML', unit="layers", file=sys.stdout, smoothing=0):
            xml_path = os.path.join(self.out , 'scan_' + str(i+1) + '.xml')
            self.write_layer(layers[i],i+1,segmentStyleList,vProfileList, defaultContourSegmentStyleID, defaultHatchSegmentStyleID)
            
        return

    """
    Outputs zipped scn file of XML layer files
    
    Requires that there are XML files in the directory self.out
    """
    def output_zip(self):
        # create a ZipFile object
        with ZipFile(os.path.join(self.out , 'scanpath_files.scn'), 'w') as zip_file:
           # Iterate over all the files in directory
           for folder_name, subfolders, file_names in os.walk(self.out):
               for file_name in file_names:
                   #create complete filepath of file in directory
                   file_path = os.path.join(folder_name, file_name)
                   # Add file to zip
                   zip_file.write(file_path, basename(file_path))
        print(self.out + '/scanpath_files.scn was created successfully')
        return

'''
This does not use ConfigFile to get any of its data. 
output_path needs to be full path with .hdf5 extension
'''
class HDF5Writer():
    
    def __init__(self, output_dir: str):
        self.out = output_dir
    
    # Get data for HDF5 File
    def parameters(self, layer_paths: np.ndarray, layer_power: float, 
                   layer_speed: float, layer_num: int, scan_mode: ScanMode):
        
        # preallocate points data
        segments_len = 0
        for path in layer_paths:
            segments_len += len(path)
        points = np.concatenate((layer_paths[0], layer_paths[1]), axis=0)
        
        times = np.empty(len(points), dtype='d')
        
        # preallocate edge data
        edges = np.empty(len(points),dtype='i').reshape(-1,2)              
        velocities = np.empty(len(points) // 2, dtype='d')
        powers = np.empty(len(points) // 2, dtype='d')
        lengths = np.empty(len(points) // 2, dtype='d')
        
        #Iterate through each consecutive pair of points
        
        for i in range(len(points)):
            
                    
            # Each edge
            edges[i // 2][0] = i // 2
            edges[i // 2][1] = i // 2 + 1
            
                
            if ( (scan_mode == ScanMode.HatchFirst and i < len(layer_paths[0]) - 1 and i % 4 > 1) or 
                  (scan_mode == ScanMode.ContourFirst and i > len(layer_paths[0]) - 1) and i % 4 > 1): # jump vectors odd edges hatch only                       
                  powers[i // 2] = 0
                  velocities[i // 2] = 5000
            else:
                powers[i // 2] = layer_power
                velocities[i // 2] = layer_speed
                if (i < len(points) - 1): 
                    lengths[i // 2] = np.linalg.norm(points[i+1] - points[i])
                    

            
                                    
        turn_time = 5*(10**-4)
        current_time = 0
        count = 0
        for vel in velocities:
            times[2*count] = current_time
            times[2*count + 1] = current_time + (lengths[count] / vel)
            current_time = times[2*count + 1] + turn_time
            count = count + 1  
        
        # Base level data
        dlt = np.amax(times)
        flt = np.amax(times) + 10.0
        lt = 0.03
        lh = 0.03*layer_num
        lst = 0.0
        
        return (powers,velocities,edges,points,times,dlt,flt,lh,lt,lst,lengths)
    
    # Writes 1 layer to HDF5 File
    def write_layer(self, layer_paths: np.ndarray, layer_power: float, 
                    layer_speed: float, layer_num: int, file_name: str, 
                    scan_mode: ScanMode):
        params = self.parameters(layer_paths, layer_power, layer_speed, 
                                 layer_num, scan_mode)
        with h5py.File(self.out + "/" + file_name, "a") as f:
            grp = f.create_group(str(layer_num))
            grp.create_dataset('points', data=params[3])
            grp.create_dataset('edges', data=params[2])
            
            subgrp1 = grp.create_group('edgeData')
            subgrp1.create_dataset('power', data=params[0])
            subgrp1.create_dataset('velocity', data=params[1])

            subgrp2 = grp.create_group('pointData')
            subgrp2.create_dataset('time',data=params[4])
            subgrp1.create_dataset('length', data=params[10])
    
    # Writes data to HDF5 file
    # File name needs .hdf5 
    def output_hdf5(self, layers_paths: np.ndarray, 
                    powers_layers: List[float], speeds_layers: List[float],
                    file_name: str, scan_mode: ScanMode):
        
        # Create/wipe folder
        if not os.path.exists("hdf5"):
            os.makedirs("hdf5")
        else:
            for f in glob.glob("hdf5/*"):
                os.remove(f)
        
        data_layer_times = np.zeros(len(layers_paths), dtype='d')
        file_layer_times = np.zeros(len(layers_paths), dtype='d')
        layer_height = np.zeros(len(layers_paths), dtype='d')
        layer_thickness = np.zeros(len(layers_paths), dtype='d')
        layer_start_times = np.zeros((len(layers_paths),1), dtype='d')
        
        for layer in range(len(layers_paths)):
        
            params = self.parameters(layers_paths[layer], 
                                     powers_layers[layer][0], 
                                     speeds_layers[layer][0], 
                                     layer,
                                     scan_mode)
        
            data_layer_times[layer] = params[5]
            file_layer_times[layer] = params[6]
            layer_height[layer] = params[7]
            layer_thickness[layer] = params[8]
        
            if(layer == 0):
                st1 = [params[9]]
                layer_start_times[layer] = st1        
            else:
                st2 = layer_start_times[layer-1] + data_layer_times[layer-1]
                layer_start_times[layer] = st2
        
            self.write_layer(layers_paths[layer], 
                             powers_layers[layer][0], 
                             speeds_layers[layer][0], 
                             layer, 
                             file_name, 
                             scan_mode)
        
        
        #Writing to HDF5 file for all the layers
        with h5py.File(self.out + "/" + file_name, "a") as f:
            f.create_dataset("/data_layer_times", data=data_layer_times, dtype='d')
            f.create_dataset("/file_layer_times", data=file_layer_times, dtype='d')
            f.create_dataset("/layer_height", data=layer_height, dtype='d')
            f.create_dataset("/layer_start_times", data=layer_start_times, dtype='d')
            f.create_dataset("/layer_thickness", data=layer_thickness, dtype='d')
        
        print(self.out + "/" + file_name + " was created successfully")

'''
Requires in_dir to be a valid directory and to contain only the following:
    XML files for each layer [1, n] e.g. layer_1.xml
    The zipped file (.scn or .zip) (or any arbitrary 1 additional file) 

Requires out_file to be a .hdf5 file
'''
def xml_to_hdf5(in_dir: str, out_file: str):
    
    hdf = HDF5Writer('hdf5')
    num_layers = len(os.listdir(in_dir + '/')) - 1 # subtract .scn file
    
    layers_paths = []
    layers_powers = []
    layers_speeds = []
    
    # XPath Element Tree Evaluators for efficiency
    
    for layer_num in range(num_layers):
            
        layer = et.parse(in_dir + '/scan_' + str(layer_num + 1) + '.xml').getroot()
        velprofiles = layer.find('VelocityProfileList')          
        segstyles = layer.find('SegmentStyleList')
        
        paths = layer.findall('./TrajectoryList/Trajectory/Path') # expression for paths
        layers_paths.append([])
        if (paths[0].find('Type').text == 'contour'):
            scan_mode = ScanMode.ContourFirst
        else:
            scan_mode = ScanMode.HatchFirst
            
        for path_num in range(len(paths)):  
            segments = paths[path_num].findall('Segment')
            layers_paths[layer_num].append([])
            layers_paths[layer_num][path_num].append([float(paths[path_num].find('./Start/X').text), float(paths[path_num].find('./Start/Y').text)])
            for seg_num in range(len(segments)):
                layers_paths[layer_num][path_num].append([float(segments[seg_num].find('./End/X').text), float(segments[seg_num].find('./End/Y').text)])
                    
        all_segs = layer.findall('./TrajectoryList/Trajectory/Path/Segment')
        layers_powers.append([])
        layers_speeds.append([])
            
        for seg_num in range(len(all_segs)):
                
            seg_style_id = all_segs[seg_num].find('SegStyle').text              
            # Search for seg style id
            seg_style = segstyles.find('./SegmentStyle/*[.=\'' + seg_style_id + '\']/..')
                
            # Assign power for this segment
            power = float(seg_style.find('./Traveler/Power').text)      
            layers_powers[layer_num].append(power)
                
            vel_profile_id = seg_style.find('./VelocityProfileID').text
            # Search for velocity profile id
            vel_profile = velprofiles.find('./VelocityProfile/*[.=\'' + vel_profile_id + '\']/..')
                
            # Assign velocity for this segment
            velocity = float(vel_profile.find('./Velocity').text)
            layers_speeds[layer_num].append(velocity)
                
    hdf.output_hdf5(layers_paths, layers_powers, layers_speeds, out_file, scan_mode)
                

'''
Requires in_path to be an HDF5 file in an existing directory
'''
def hdf5_to_xml(in_path: str, out_dir: str):
    
    MIN_JUMP_SPEED = 1000
    xml_out = XMLWriter(out_dir, config)
    layers_paths = []
    layers_segstyles = []
    seg_style = ''
    
    with h5py.File(in_path, "r") as f:

        # List all groups
        for layer in range(0, len(f.keys())-5):
            
            # Best practice to do contour first
            paths = [ [], [] ]
            scan_mode = ScanMode.ContourFirst
            on_first = True
            if (f[str(layer)]['edgeData']['power'][0] != 0 and
                f[str(layer)]['edgeData']['power'][1] == 0 and
                abs(f[str(layer)]['edgeData']['velocity'][0]) < MIN_JUMP_SPEED and
                abs(f[str(layer)]['edgeData']['velocity'][1]) >= MIN_JUMP_SPEED):
                
                scan_mode = ScanMode.HatchFirst
            seg_styles = []
            for point in range(f[str(layer)]['points'].shape[0]):
                
                x = f[str(layer)]['points'][point][0]
                y = f[str(layer)]['points'][point][1]
                                                            
                seg_power = f[str(layer)]['edgeData']['power'][point // 2]
                seg_vel = f[str(layer)]['edgeData']['velocity'][point // 2]                
                
                if (point < f[str(layer)]['points'].shape[0] - 2):
                    on_hatch = (f[str(layer)]['edgeData']['power'][point // 2] != 0 and
                            f[str(layer)]['edgeData']['power'][point // 2 + 1] == 0 and
                            abs(f[str(layer)]['edgeData']['velocity'][point // 2]) < MIN_JUMP_SPEED and
                            abs(f[str(layer)]['edgeData']['velocity'][point // 2 + 1]) >= MIN_JUMP_SPEED)
                
                if ( (scan_mode == ScanMode.ContourFirst and on_hatch) or 
                     (scan_mode == ScanMode.HatchFirst and (not on_hatch) ) ):
                    on_first = False
                
                # Assign points to appropriate path (hatch or contour)
                if on_first:
                    paths[0].append([x, y])
                else:
                    paths[1].append([x, y])
                
                # Assign seg style based on power and velocity               
                if (seg_power == 0):
                    seg_style = 'Jump'
                else: 
                    # search for velocity profile
                    vel_id = None
                    for velprofile in config.vel_profile.keys():                   
                        if (config.vel_profile[velprofile].Velocity == seg_vel):
                            vel_id = config.vel_profile[velprofile].ID
                    
                    # search for segment style
                    for segstyle in config.seg_style.keys():
                        if (config.seg_style[segstyle].Traveler.Power == seg_power and
                            config.seg_style[segstyle].VelocityProfileID == vel_id):
                            seg_style = config.seg_style[segstyle].ID
                if (point % 2 != 0):
                    seg_styles.append(seg_style)
            layers_segstyles.append(seg_styles[0])
            layers_paths.append(paths)
            
    xml_out.output_xml(layers_paths, layers_segstyles, scan_mode)
    # xml_out.output_zip()