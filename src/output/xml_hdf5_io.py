import pandas as pd
import numpy as np
from lxml.etree import Element, SubElement, xmlfile
import xml.etree.ElementTree as et
from typing import List, Dict
from . import config_build as settings
from datetime import datetime
from shapely.geometry import Polygon, MultiLineString
from zipfile import ZipFile
import os
from os.path import basename
from pyslm.geometry import ScanMode, BuildStyle
import h5py
import glob

class ConfigFile():
    def __init__(self, file_path):
        self.config_path = file_path
        self.header = self.load_header()
        self.vel_profile = self.load_velocity_profile()
        self.seg_style = self.load_segment_style()
        self.regions, self.parts = self.load_parts()

    def load_header(self) -> settings.Header:
        df = pd.read_excel(self.config_path, sheet_name=1, engine="xlrd")
        layer_thickness = df.iloc[4, 2]
        dosing_factor =  df.iloc[5, 2]
        return settings.Header(datetime.strptime('2020-03-23', "%Y-%m-%d"), layer_thickness, dosing_factor)

    def load_velocity_profile(self) -> Dict[str, settings.VelocityProfile]:
        df = pd.read_excel(self.config_path,
                           sheet_name=2, index_col=0, header=5, usecols="A:H")
        vel_ = {}
        for index, row in df.iterrows():
            vel_[index] = settings.VelocityProfile(index, row.iloc[0],
                                                         row.iloc[2], row.iloc[3], row.iloc[4], row.iloc[5], row.iloc[6], row.iloc[1])
        return vel_

    def load_segment_style(self) -> Dict[str, settings.SegmentStyle]:
        df = pd.read_excel(self.config_path, sheet_name=3,
                           index_col=0, header=7, usecols="A:J")
        seg_style = {}
        for index, row in df.iterrows():
            traveler = settings.Traveler(
                row.iloc[1], row.iloc[2], row.iloc[3])
            seg_style[index] = settings.SegmentStyle(
                index, row.iloc[0], traveler)

        return seg_style
        
    def load_parts(self):
        regions = pd.read_excel(
            self.config_path, sheet_name=4, header=5, usecols="A:O", index_col=0)
        parts = pd.read_excel(self.config_path, sheet_name=5,
                              header=5, usecols="A:G")

        regions_d = {}
        for index, row in regions.iterrows():
            p_r = settings.PrintRegions(index, *row.iloc[0:13].values.tolist())
            regions_d[index] = p_r

        part_d = []
        for index, row in parts.iterrows():
            part = settings.PartsSetting(*row.iloc[0:7].values.tolist())
            part_d.append(part)

        return regions_d, part_d

'''
Writes ALSAM controller XML files for L-PBF
output_dir needs to be existing directory
'''
class XMLWriter():

    def __init__(self, output_dir: str, print_loader: ConfigFile):
        self.out = output_dir
        self.pl = print_loader

    def make_header(self, layer_num: int):
        h = Element('Header')
        SubElement(h, 'AmericaMakesSchemaVersion').text = \
            self.pl.header.AmericaMakesSchemaVersion.strftime("%Y-%m-%d")
        SubElement(h, 'LayerNum').text = \
            str(layer_num)
        SubElement(h, 'LayerThickness').text = \
            str(self.pl.header.LayerThickness)
        SubElement(h, 'DosingFactor').text = \
            str(self.pl.header.DosingFactor)
        return h

    def make_velocity_profiles(self):
        vpl = Element('VelocityProfileList')

        ls_vpl = self.pl.vel_profile

        for vl in ls_vpl.values():
            xvl = SubElement(vpl, 'VelocityProfile')

            SubElement(xvl, 'ID').text = str(vl.ID)
            SubElement(xvl, 'Velocity').text = str(vl.Velocity)
            SubElement(xvl, 'Mode').text = str(vl.Mode)
            SubElement(xvl, 'LaserOnDelay').text = str(vl.LaserOnDelay)
            SubElement(xvl, 'LaserOffDelay').text = str(vl.LaserOffDelay)
            SubElement(xvl, 'MarkDelay').text = str(vl.MarkDelay)
            SubElement(xvl, 'PolygonDelay').text = str(vl.PolygonDelay)

        return vpl

    def make_segment_styles(self):
        xsl_root = Element('SegmentStyleList')

        ls_seg = self.pl.seg_style
        for sl in ls_seg.values():
            xsl = SubElement(xsl_root, 'SegmentStyle')

            SubElement(xsl, 'ID').text = str(sl.ID)
            SubElement(xsl, 'VelocityProfileID').text = str(
                sl.VelocityProfileID)
            SubElement(xsl, 'LaserMode').text = str(sl.LaserMode)
            
            if (SubElement(xsl, 'ID').text != "Jump"):
                xtl = SubElement(xsl, 'Traveler')
    
                SubElement(xtl, 'ID').text = str(sl.Traveler.ID)
                SubElement(xtl, 'SyncDelay').text = str(
                    sl.Traveler.SyncDelay)
                SubElement(xtl, 'Power').text = str(sl.Traveler.Power)
                SubElement(xtl, 'SpotSize').text = str(sl.Traveler.SpotSize)

        return xsl_root

    
    def make_traj_list(self, layer_paths: np.ndarray, layer_segstyle: str, scan_mode: ScanMode): # unstack and make one list, broken down by segments instead of coordinates - do that in the test2 file, assume it is already unstacked in trajectory function
          
        xtraj_root = Element('TrajectoryList')

        # Add control flow for >1 trajectory            
        traj = SubElement(xtraj_root, 'Trajectory')
        SubElement(traj, 'TrajectoryID').text = '0'
        SubElement(traj, 'PathProcessingMode').text = "sequential" # add control flow for multipart                               
        
        for path in range(len(layer_paths)):
            
            xpath = SubElement(traj, 'Path')
            
            if scan_mode == ScanMode.ContourFirst:
                SubElement(xpath, 'Type').text = 'contour'
                scan_mode = ScanMode.HatchFirst
            else:
                SubElement(xpath, 'Type').text = 'hatch'
                
            SubElement(xpath, 'Tag').text = 'part1'
            SubElement(xpath, 'NumSegments').text = str(len(layer_paths[0])-1)
            SubElement(xpath, 'SkyWritingMode').text = str(0)
            start = SubElement(xpath, 'Start')
            SubElement(start, 'X').text = str(layer_paths[path][0][0])
            SubElement(start, 'Y').text = str(layer_paths[path][0][1])
                    
            # Create segments for each contour and hatch coordinates
            for i in range(1, len(layer_paths[path])):
                seg = SubElement(xpath, 'Segment')
                SubElement(seg, 'SegmentID').text = str(i)
                # For hatches, every other segment is going to be a jump vector
                if (path == 1 and i % 2 == 0):
                    SubElement(seg, 'SegStyle').text = 'Jump'                    
                else: 
                    SubElement(seg, 'SegStyle').text = layer_segstyle
                end = SubElement(seg, 'End')
                SubElement(end, 'X').text = str(layer_paths[path][i][0])
                SubElement(end, 'Y').text = str(layer_paths[path][i][1])
                                                 
                                                  
        return xtraj_root
    
    """
    Writes single XML layer file
    
    Needs flat 1D lists of coordinates for Lcontour and Lhatch e.g. [x1, y2, x2, y2, x3, y3]
    """            
    def write_layer(self, layer_paths: np.ndarray, layer_num: int, layer_segstyle: str, scan_mode: ScanMode):
        with xmlfile(self.out + '/scan_' + str(layer_num) + '.xml') as xf:
            with xf.element('Layer'):
                xf.write(self.make_header(layer_num), pretty_print=True)
                xf.write(self.make_velocity_profiles(), pretty_print=True)
                xf.write(self.make_segment_styles(), pretty_print=True)
                xf.write(self.make_traj_list(layer_paths, layer_segstyle, scan_mode), pretty_print=True)

    """
    Outputs all XML layer files
    
    Needs a nested list for layers_paths:
    [    
        layer1:
        [ path1 numpy array: [x1,y1], [x2,y2], ... , [xn,yn]
         ...
         pathn numpy array: [x1,y1], [x2,y2], ... , [xn,yn]
        ]
         
        ...
        
        layern:
        [ path1 numpy array: [x1,y1], [x2,y2], ... , [xn,yn]
         ...
         pathn numpy array: [x1,y1], [x2,y2], ... , [xn,yn]
        ]
         
    ]
    """
    def output_xml(self, layers_paths: List[List[np.ndarray]], layers_segstyles: List[str], scan_mode: ScanMode):
        
        # Create/wipe folder
        if not os.path.exists("xml"):
            os.makedirs("xml")
        else:
            for f in glob.glob("xml/*"):
                os.remove(f)  
        
        for i in range(0, len(layers_paths)):
            print('XML Layer # ' + str(i+1) + ' Started')
            xml_path = '../../' + self.out + '/scan_' + str(i+1) + '.xml'
            print(xml_path)
            self.write_layer(layers_paths[i], i+1, layers_segstyles[i], scan_mode)
            print('XML Layer # ' + str(i+1) + ' Complete\n')
            
        return

    """
    Outputs zipped scn file of XML layer files
    
    Requires that there are XML files in the directory self.out
    """
    def output_zip(self):
        # create a ZipFile object
        with ZipFile(self.out + '/scanpath_files.scn', 'w') as zip_file:
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
        neighbors = np.empty( ( len(points) // 2 ) * 3, dtype='d').reshape(-1,3)
        
        #Iterate through each consecutive pair of points
        neighbors[0][0] = 0 # first edge
        
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
                    
            '''
            Neighbors are defined in this code as being continuous off 
            of another segment. I don't think this is right, but it's also not
            just consecutive segments because some segments that are not the first
            or last have no neighbors. I'll have to ask Mike how to define neighbors, 
            '''
            # neighbors[i//2][1] = lengths[i//2]
            # # Each edge except the first and last
            # if j > 0 and j < ( (len(points) // 2) - 1 ):               
            #     if np.array_equiv(points[2*( (i + 1) * j//2)-1], points[2*( (i + 1) * j//2)]):
            #         neighbors[ (i + 1) * j//2][0] = lengths[( (i + 1) * j//2)-1]
            #     else:
            #         neighbors[ (i + 1) * j//2][0] = 0
                
        neighbors[(len(points) // 2) - 1][2] = 0 # last edge
            
                                    
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
        
        return (powers,velocities,edges,points,times,dlt,flt,lh,lt,lst,lengths,neighbors)
    
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
            subgrp1.create_dataset('neighbors', data=params[11])
    
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
def hdf5_to_xml(in_path: str, out_dir: str, config: ConfigFile):
    
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
    xml_out.output_zip()