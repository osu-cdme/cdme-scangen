import os
import sys
sys.path.append("C:/CDME/Code/cdme-scangen")

from src.output.xml_hdf5_io import XMLWriter,ConfigFile
##test status, currently runs but does not produce any noticable output


outputDir="C:/CDME/Code/cdme-scangen/xmlnew"
print_loader=ConfigFile("C:/CDME/Code/cdme-scangen/build_config.xls")

xmlWriter = XMLWriter(outputDir,print_loader)
xmlWriter.output_xml
xmlWriter.output_zip

