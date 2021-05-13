import pandas as pd
import numpy as np
from lxml import etree
from typing import List, Dict
from . import config_build as settings
from datetime import date
from shapely.geometry import Polygon, MultiLineString
from zipfile import ZipFile
import os
import math
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
        return settings.Header(date.today(), layer_thickness, dosing_factor)

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


class XMLWriter():

    def __init__(self, output_path: str, print_loader: ConfigFile):
        self.out = output_path
        self.pl = print_loader

    def make_header(self, layer_num: int):
        h = etree.Element('Header')
        etree.SubElement(h, 'AmericaMakesSchemaVersion').text = \
            self.pl.header.AmericaMakesSchemaVersion.strftime("%Y-%m-%d")
        etree.SubElement(h, 'LayerNum').text = \
            str(layer_num)
        etree.SubElement(h, 'LayerThickness').text = \
            str(self.pl.header.LayerThickness)
        etree.SubElement(h, 'DosingFactor').text = \
            str(self.pl.header.DosingFactor)
        return h

    def make_velocity_profiles(self):
        vpl = etree.Element('VelocityProfileList')

        ls_vpl = self.pl.vel_profile

        for vl in ls_vpl.values():
            xvl = etree.SubElement(vpl, 'VelocityProfile')

            etree.SubElement(xvl, 'ID').text = str(vl.ID)
            etree.SubElement(xvl, 'Velocity').text = str(vl.Velocity)
            etree.SubElement(xvl, 'Mode').text = str(vl.Mode)
            etree.SubElement(xvl, 'LaserOnDelay').text = str(vl.LaserOnDelay)
            etree.SubElement(xvl, 'LaserOffDelay').text = str(vl.LaserOffDelay)
            etree.SubElement(xvl, 'MarkDelay').text = str(vl.MarkDelay)
            etree.SubElement(xvl, 'PolygonDelay').text = str(vl.PolygonDelay)

        return vpl

    def make_segment_styles(self):
        xsl_root = etree.Element('SegmentStyleList')

        ls_seg = self.pl.seg_style
        for sl in ls_seg.values():
            xsl = etree.SubElement(xsl_root, 'SegmentStyle')

            etree.SubElement(xsl, 'ID').text = str(sl.ID)
            etree.SubElement(xsl, 'VelocityProfileID').text = str(
                sl.VelocityProfileID)
            etree.SubElement(xsl, 'LaserMode').text = str(sl.LaserMode)
            
            if (etree.SubElement(xsl, 'ID').text != "Jump"):
                xtl = etree.SubElement(xsl, 'Traveler')
    
                etree.SubElement(xtl, 'ID').text = str(sl.Traveler.ID)
                etree.SubElement(xtl, 'SyncDelay').text = str(
                    sl.Traveler.SyncDelay)
                etree.SubElement(xtl, 'Power').text = str(sl.Traveler.Power)
                etree.SubElement(xtl, 'SpotSize').text = str(sl.Traveler.SpotSize)

        return xsl_root

    
    def make_traj_list(self, layer_paths: np.ndarray, layer_segstyle: str, scan_mode: ScanMode): # unstack and make one list, broken down by segments instead of coordinates - do that in the test2 file, assume it is already unstacked in trajectory function
          
        xtraj_root = etree.Element('TrajectoryList')

        # Add control flow for >1 trajectory            
        traj = etree.SubElement(xtraj_root, 'Trajectory')
        etree.SubElement(traj, 'TrajectoryID').text = '0'
        etree.SubElement(traj, 'PathProcessingMode').text = "sequential" # add control flow for multipart                               
        
        for path in range(len(layer_paths)):
            
            xpath = etree.SubElement(traj, 'Path')
            
            if scan_mode == ScanMode.ContourFirst:
                etree.SubElement(xpath, 'Type').text = 'contour'
                scan_mode = ScanMode.HatchFirst
            else:
                etree.SubElement(xpath, 'Type').text = 'hatch'
                
            etree.SubElement(xpath, 'Tag').text = 'part1'
            etree.SubElement(xpath, 'NumSegments').text = str(len(layer_paths[0])-1)
            etree.SubElement(xpath, 'SkyWritingMode').text = str(0)
            start = etree.SubElement(xpath, 'Start')
            etree.SubElement(start, 'X').text = str(layer_paths[path][(0,0)])
            etree.SubElement(start, 'Y').text = str(layer_paths[path][(0,1)])
                    
            # Create segments for each contour and hatch coordinates
            for i in range(1, len(layer_paths[path])):
                seg = etree.SubElement(xpath, 'Segment')
                etree.SubElement(seg, 'SegmentID').text = str(i)
                # For hatches, every other segment is going to be a jump vector
                if (path == 1 and i % 2 == 0):
                    etree.SubElement(seg, 'SegStyle').text = 'Jump'                    
                else: 
                    etree.SubElement(seg, 'SegStyle').text = layer_segstyle
                end = etree.SubElement(seg, 'End')
                etree.SubElement(end, 'X').text = str(layer_paths[path][(i,0)])
                etree.SubElement(end, 'Y').text = str(layer_paths[path][(i,1)])
                                                 
                                                  
        return xtraj_root
    
    """
    Writes single XML layer file
    
    Needs flat 1D lists of coordinates for Lcontour and Lhatch e.g. [x1, y2, x2, y2, x3, y3]
    """            
    def write_layer(self, layer_paths: np.ndarray, layer_num: int, layer_segstyle: str, scan_mode: ScanMode):
        with etree.xmlfile(self.out + '/scan_' + str(layer_num) + '.xml') as xf:
            with xf.element('Layer'):
                xf.write(self.make_header(layer_num), pretty_print=True)
                xf.write(self.make_velocity_profiles(), pretty_print=True)
                xf.write(self.make_segment_styles(), pretty_print=True)
                xf.write(self.make_traj_list(layer_paths, layer_segstyle, scan_mode), pretty_print=True)

    """
    Outputs all XML layer files
    
    Needs a List of Lists of flat 1D of coordinates, see above
    """
    def output_xml(self, layers_paths: np.ndarray, layers_segstyles: List[str], scan_mode: ScanMode):
        
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
        with ZipFile(self.out + '/scanpath_files.zip', 'w') as zip_file:
           # Iterate over all the files in directory
           for folder_name, subfolders, file_names in os.walk(self.out):
               for file_name in file_names:
                   #create complete filepath of file in directory
                   file_path = os.path.join(folder_name, file_name)
                   # Add file to zip
                   zip_file.write(file_path, basename(file_path))
        print(self.out + '/scanpath_files.zip was created successfully')
        return

'''
This does not use ConfigFile to get any of its data. The method parameters() 
takes coordinates,  
'''
class HDF5Writer():
    
    def __init__(self, output_path: str, print_loader: ConfigFile):
        self.out = output_path
        self.pl = print_loader
    
    # Get data for HDF5 File
    def parameters(self, layer_paths: np.ndarray, layer_power: float, 
                   layer_speed: float, layer_num: int):
        
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
        for i in range(0, len(edges)):
            
            # Each edge
            edges[i][0] = 2*i
            edges[i][1] = 2*i + 1
            velocities[i] = layer_speed
            powers[i] = layer_power
            lengths[i] = np.linalg.norm(points[2*i+1] - points[2*i])
            
            '''
            Neighbors are defined in this code as being continuous off 
            of another segment. I don't think this is right, but it's also not
            just consecutive segments because some segments that are not the first
            or last have no neighbors. I'll have to ask Mike how to define neighbors, 
            '''
            neighbors[i][1] = lengths[i]
            # Each edge except the first and last
            if i > 0 and i < ( (len(points) // 2) - 1 ):               
                if np.array_equiv(points[2*i-1], points[2*i]):
                    neighbors[i][0] = lengths[i-1]
                else:
                    neighbors[i][0] = 0
                
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
    
    # Writes 1 layer to HDF5
    def write_layer(self, layer_paths: np.ndarray, layer_power: float, 
                    layer_speed: float, layer_num: int):
        params = self.parameters(layer_paths, layer_power, layer_speed, 
                                 layer_num)
        with h5py.File(self.out + "/Nut.hdf5", "a") as f:
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
    def output_hdf5(self, layers_paths: np.ndarray, 
                    powers_layers: List[float], speeds_layers: List[float]):
        
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
                                     powers_layers[layer], 
                                     speeds_layers[layer], layer)
        
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
        
            self.write_layer(layers_paths[layer], powers_layers[layer], 
                             speeds_layers[layer], layer)
        
        
        #Writing to HDF5 file for all the layers
        with h5py.File(self.out + "/Nut.hdf5", "a") as f:
            f.create_dataset("/data_layer_times", data=data_layer_times, dtype='d')
            f.create_dataset("/file_layer_times", data=file_layer_times, dtype='d')
            f.create_dataset("/layer_height", data=layer_height, dtype='d')
            f.create_dataset("/layer_start_times", data=layer_start_times, dtype='d')
            f.create_dataset("/layer_thickness", data=layer_thickness, dtype='d')
        
        print(self.out + "/Nut.hdf5 was created successfully")

'''
Requires in_dir to contain only XML files

Requires out_path to be in an existing directory
'''
def xml_to_hdf5(in_dir: str, out_path: str):
    pass

'''
Requires in_path to be an HDF5 file in an existing directory
'''
def hdf5_to_xml(in_path: str, out_dir: str):
    pass