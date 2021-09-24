import os
import sys

from pyslm.geometry.geometry import ScanMode
sys.path.append("C:/CDME/Code/cdme-scangen")

from src.output.xml_hdf5_io import XMLWriter,ConfigFile
##test status, currently runs but does not produce any noticable output


outputDir="C:/CDME/Code/xml"
print_loader=ConfigFile("C:/CDME/Code/cdme-scangen/build_config.xls")

xmlWriter = XMLWriter(outputDir,print_loader)
xmlWriter.output_xml(print_loader.parts,print_loader.seg_style,ScanMode.ContourFirst)
xmlWriter.output_zip()

#def output_xml(self, layers_paths: List[List[np.ndarray]], layers_segstyles: List[str], scan_mode: ScanMode):
#class ConfigFile():
#    def __init__(self, file_path):
#        self.config_path = file_path
#        self.header = self.load_header()
#        self.vel_profile = self.load_velocity_profile()
#        self.seg_style = self.load_segment_style()
#        self.regions, self.parts = self.load_parts()

#killing off the ConfigFile class in move to IO 2.0