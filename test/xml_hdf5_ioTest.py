import os
import sys

from pyslm.geometry.geometry import ScanMode
sys.path.append("C:/CDME/Code/cdme-scangen")

from src.output.xml_hdf5_io import XMLWriter,ConfigFile
##test status, currently runs but does not produce any noticable output


outputDir="C:/CDME/Code/xml"


xmlWriter = XMLWriter(outputDir)
xmlWriter.output_xml(layers,model)
xmlWriter.output_zip()

