# System Imports
import io
import sys 

# Third Party Imports 
import numpy as np 
import pandas as pd 

# Local Imports
from pyslm.hatching import Hatcher 
from ..island.island import BasicIslandHatcherRandomOrder

# Takes in an Excel sheet 
# TODO: Tracking IDs is redundant; remove from excel file and just use array indexes as equivalent 
def excel_to_array(excel_file: pd.io.excel._base.ExcelFile, debug_file: io.TextIOWrapper) -> list:
    """Reads in an Excel file, outputting an array-based representation of areas and associated scanpaths/parameters.
    The first set of values corresponds to the *default hatcher*. This is to be initialized and everything, but will 
    *not* have an area tied to it. 

    :param excel_file: The excel file to pull the information from. 
    :type excel_file: pd.io.excel._base.ExcelFile
    :param debug_file: A debug file to output debug output to.
    :type debug_file: io.TextIOWrapper
    :return: An array of arrays, each inner array with the following structure:
        [0]: ID of the given Area (Equation: "<Row of Excel Sheet> - 2")
        [1]: 6-Long Array of min-x, min-y, min-z, max-x, max-y, max-z 
        [2]: scanpath identifier (`default`, `island`, etc.)
        [3]: General Parameters (True/False)
    :rtype: list
    """

    debug_file.write("excel_to_array()\n--------------------\n")

    # Convert an Excel specification of area to an array to use as input for next step
    bounds_sheet = excel_file.parse(1)

    # Get ids corresponding to each scan path specified 
    ids = bounds_sheet["id"]
    ids = np.array(ids[~np.isnan(ids)]).astype(np.uint)
    debug_file.write("ids: \n{}\n".format(ids))

    # Get boundaries of each scanpath 
    bounds = np.array([bounds_sheet["min_x"], bounds_sheet["min_y"], bounds_sheet["min_z"], 
        bounds_sheet["max_x"], bounds_sheet["max_y"], bounds_sheet["max_z"]])
    bounds = bounds[:, ~np.isnan(bounds).any(axis=0)] # Long story short, filters out NaN columns
    areas = np.hstack([arr.reshape(-1, 1) for arr in bounds]).astype(np.uint) # Essentially a transpose 
    debug_file.write("areas: \n{}\n".format(areas))

    # Get the scanpath versions (i.e. default, island, ...)
    scanpaths = list(bounds_sheet["scanpath"])
    scanpaths = np.array(scanpaths[:scanpaths.index(np.nan)]) # Can't use above solution because isnan() undefined for strings...
    debug_file.write("scanpaths: \n{}\n".format(scanpaths))

    # Get the general parameters to go along with the provided ids 
    general_params_sheet = excel_file.parse(2)
    general_params = []
    for row in general_params_sheet.values:
        if pd.isna(row[0]): # End of valid rows 
            break 
        row = row[:9] # Indices 0-8 are the ones we care about; rest is just visual info on the sheet 
        row[5] = int(row[5]) # pyslm requires # Inner Contours as int 
        row[6] = int(row[6]) # pyslm requires # Outer Contours as int 
        general_params.append(row)
    debug_file.write("general_params: \n{}\n".format(general_params))

    # Get the custom parameters to go along with the provided ids 
    custom_params_sheet = excel_file.parse(3)
    custom_params = []
    for row in custom_params_sheet.values:
        if pd.isna(row[0]):
            break
        row = row[:6] # Indices 0-5 are the oens we care about; rest is just visual info on the sheet 
        custom_params.append(row)
    debug_file.write("custom_params: \n{}\n".format(custom_params))

    # Can't do fancy numpy stuff because they aren't all the same data type (scan paths are strings)
    output = []
    for i in range(len(ids)):
        output.append([ids[i], areas[i], scanpaths[i], general_params[i], custom_params[i]])
    return output 

def array_to_instances(arr: list, debug_file: io.TextIOWrapper) -> tuple:
    """Converts the array that `excel_to_array()` returns into a list of hatchers, each initialized with
    the correct parameters - both generic (common across all algorithms) and custom (specific to an algorithm).

    :param arr: The array, formatted in the way `excel_to_array()` returns.
    :type arr: list
    :param debug_file: A pointer to the open `debug.txt` file to use for any debug output.
    :type debug_file: io.TextIOWrapper
    :return: A list of [hatcher, area] lists, where the hatcher has been initialized and all parameters have been set. 
    :rtype: list
    """
    
    # Refresher: Each scanpath has the following structure:
    # [0]: ID of the given Area (Equation: "<Row of Excel Sheet> - 2")
    # [1]: 6-Long Array of min-x, min-y, min-z, max-x, max-y, max-z 
    # [2]: scanpath identifier (`default`, `island`, etc.)
    # [3]: General Parameters (True/False)
    output = []
    for scanpath in arr:

        # 1. Initialize the correct type
        if scanpath[2] == "default":
            hatcher = Hatcher()
        elif scanpath[2] == "island":
            hatcher = BasicIslandHatcherRandomOrder()
        else:
            sys.exit("ERROR: Unrecognized scanpath type " + str(scanpath[2]))

        # 2. Set general parameters for the scan path
        # TODO: ID is scanpath[3][0]; work support for that in or something 
        hatcher.hatchDistance = scanpath[3][1]
        hatcher.hatchAngle = scanpath[3][2]
        hatcher.layerAngleIncrement = scanpath[3][3]
        # hatcher.hatchSortMethod = scanpath[3][4] # TODO: Broken with error `The Hatch Sort Method should be derived from the BaseSort class`. Fix!
        hatcher.numInnerContours = scanpath[3][5]
        hatcher.numOuterContours = scanpath[3][6]
        hatcher.spotCompensation = scanpath[3][7]
        hatcher.volumeOffsetHatch = scanpath[3][8]

        # 3. Set custom parameters for the given scan path 
        if scanpath[2] == "island":
            # TODO: ID is scanpath[4][0]; work support for that in or something 
            hatcher.islandWidth = scanpath[4][1]
            hatcher.islandOverlap = scanpath[4][2]
            hatcher.islandOffset = scanpath[4][3]

        # 4. Append to output array 
        output.append((hatcher, scanpath[1]))

    return output