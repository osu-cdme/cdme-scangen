import pandas as pd
import numpy as np
from lxml import etree
from typing import List, Dict
from . import xml_config as settings
from datetime import date
from shapely.geometry import Polygon, MultiLineString
from zipfile import ZipFile
import os
from os.path import basename
from pyslm.geometry import ScanMode

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

    def make_velocity_profile(self):
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

    def make_segment_style(self):
        xsl_root = etree.Element('SegmentStyleList')

        ls_seg = self.pl.seg_style
        for sl in ls_seg.values():
            xsl = etree.SubElement(xsl_root, 'SegmentStyle')

            etree.SubElement(xsl, 'ID').text = str(sl.ID)
            etree.SubElement(xsl, 'VelocityProfileID').text = str(
                sl.VelocityProfileID)
            etree.SubElement(xsl, 'LaserMode').text = str(sl.LaserMode)

            xtl = etree.SubElement(xsl_root, 'Traveler')

            etree.SubElement(xtl, 'ID').text = str(sl.Traveler.ID)
            etree.SubElement(xtl, 'SyncDelay').text = str(
                sl.Traveler.SyncDelay)
            etree.SubElement(xtl, 'Power').text = str(sl.Traveler.Power)
            etree.SubElement(xtl, 'SpotSize').text = str(sl.Traveler.SpotSize)

        return xsl_root

    def make_trajectory(self, contour: List[float], hatches: List[float], scan_mode: ScanMode): # unstack and make one list, broken down by segments instead of coordinates - do that in the test2 file, assume it is already unstacked in trajectory function
          
        xtraj_root = etree.Element('TrajectoryList')

        # Contour trajectory
        ctraj = etree.SubElement(xtraj_root, 'Trajectory')
        etree.SubElement(ctraj, 'TrajectoryID').text = '0'
        etree.SubElement(ctraj, 'PathProcessingMode').text = "sequential" # add control flow for multipart       

        # Hatches trajectory
        htraj = etree.SubElement(xtraj_root, 'Trajectory')
        etree.SubElement(htraj, 'TrajectoryID').text = '1'
        etree.SubElement(htraj, 'PathProcessingMode').text = "sequential" # add control flow for multipart
              
        for traj in [ctraj, htraj]:
            
            path = etree.SubElement(traj, 'Path') # Make path subtree - add control flow for multipart   
                            
            if (scan_mode == ScanMode.ContourFirst):
                etree.SubElement(path, 'Type').text = 'contour'
                etree.SubElement(path, 'Tag').text = 'part1'
                etree.SubElement(path, 'NumSegments').text = str(len(contour)/2)
                etree.SubElement(path, 'SkyWritingMode').text = str(0) # Why is it a dict with one key 'Main'?
                start = etree.SubElement(path, 'Start')
                etree.SubElement(start, 'X').text = str(contour[0])
                etree.SubElement(start, 'Y').text = str(contour[1])
                
                # Create segments for each contour and hatch coordinates
                for i in range(2, len(contour), 2):
                    seg = etree.SubElement(path, 'Segment')
                    # index of segment in list
                    etree.SubElement(seg, 'SegmentID').text = str(int(i/2))
                    etree.SubElement(seg, 'SegStyle').text = 'Contour1'
                    end = etree.SubElement(seg, 'End')
                    etree.SubElement(end, 'X').text = str(contour[i])
                    etree.SubElement(end, 'Y').text = str(contour[i+1])
            # Currently assumes hatches are first by default            
            else:
                etree.SubElement(path, 'Type').text = 'hatch'
                etree.SubElement(path, 'Tag').text = 'part1'
                etree.SubElement(path, 'NumSegments').text = str(len(hatches)/2)
                etree.SubElement(path, 'SkyWritingMode').text = str(0) # Why is it a dict with one key 'Main'?
                start = etree.SubElement(path, 'Start')
                etree.SubElement(start, 'X').text = str(hatches[0])
                etree.SubElement(start, 'Y').text = str(hatches[1])

                for i in range(2, len(hatches), 2):
                    seg = etree.SubElement(path, 'Segment')
                    # index of segment in list
                    etree.SubElement(seg, 'SegmentID').text = str(int(i/2))
                    etree.SubElement(seg, 'SegStyle').text = 'Hatch1'
                    end = etree.SubElement(seg, 'End')
                    etree.SubElement(end, 'X').text = str(hatches[i])
                    etree.SubElement(end, 'Y').text = str(hatches[i+1])
                                                  
        return xtraj_root
    
    """
    Writes single XML layer file
    """            
    def write_xml(self, Lcontour, Lhatch, layer_num: int, scan_mode: ScanMode):
        with etree.xmlfile(self.out + '/scan_' + str(layer_num) + '.xml') as xf:
            with xf.element('Layer'):
                xf.write(self.make_header(layer_num), pretty_print=True)
                xf.write(self.make_velocity_profile(), pretty_print=True)
                xf.write(self.make_segment_style(), pretty_print=True)
                xf.write(self.make_trajectory(Lcontour, Lhatch, scan_mode), pretty_print=True)

    """
    Outputs all XML layer files
    
    Needs a flat 1D list of coordinates e.g. [x1, y2, x2, y2, x3, y3]
    """
    def output_xml(self, contour_layers, hatch_layers, scan_mode: ScanMode):
        
        num_layers = len(contour_layers)    
        
        for i in range(0, num_layers):
            print('XML Layer # ' + str(i+1) + ' Started')
            xml_path = '../../' + self.out + '/scan_' + str(i+1) + '.xml'
            print(xml_path)
            self.write_xml(contour_layers[i], hatch_layers[i], i+1, scan_mode)
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
        print(self.out + 'scanpath_files.zip was created successfully')
        return