# In short, this file goes from a folder of ALSAM XML files to an HDF5 file.
# sys.argv[1]: Path to directory of input .XML files (relative or absolute)
# sys.argv[2]: Path to output .HDF5 file (relative or absolute)
# Output: HDF5 file located at sys.argv[2]

import os 
import sys
sys.path.insert(0, os.path.abspath("./")) # Needed for it to recognize src 
import src.output.HDF5Util as HDF5Util

# Verify cmd line arguments
if not len(sys.argv) == 3:
    raise Exception("Intended Usage: python outputhdf5.py <Path to Folder of XML files> <Path of Output .HDF5 File>")

# Check first folder exists
if not os.path.isdir(sys.argv[1]):
    raise Exception("Invalid path {} to folder of XML files.".format(sys.argv[1]))
# Check first folder only contains .XML files
if not all(os.path.isfile(os.path.join(sys.argv[1], f)) for f in os.listdir(sys.argv[1]) if f.endswith(".xml")):
    raise Exception("Input folder {} doesn't contain only .XML files.".format(sys.argv[1]))

# Check second is valid path to a file AND that its extension to lowercase is .hdf5
# TODO: Implement check that the path is valid 
if not sys.argv[2].lower().endswith(".hdf5"):
    raise Exception("Invalid output file extension (must be .hdf5 or .HDF5): {}".format(sys.argv[2]))

# Convert relative path to absolute paths
input_folder = os.path.abspath(sys.argv[1])
output_file = os.path.abspath(sys.argv[2])

# Actually do the work 
HDF5Util.HDF5Util(input_folder, output_file).convertSCNtoHDF5()