# System Imports
import io

# Third Party Imports 
import numpy as np 
import pandas as pd 

# Takes in an Excel sheet 
# TODO: Tracking IDs is redundant; remove from excel file and just use array indexes as equivalent 
def excel_to_array(excel_file: pd.io.excel._base.ExcelFile, debug_file: io.TextIOWrapper) -> list:
    # TODO: Docstring 
    """[summary]

    :param excel_file: [description]
    :type excel_file: pd.io.excel._base.ExcelFile
    :param debug_file: [description]
    :type debug_file: io.TextIOWrapper
    :return: [description]
    :rtype: list
    """

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
    general_params = np.array([general_params_sheet["Hatch Distance (mm)"], general_params_sheet["Hatch Angle (mm)"], 
        general_params_sheet["Layer Angle Increment (deg)"], general_params_sheet["Hatch Sort Method"], 
        general_params_sheet["# Inner Contours"], general_params_sheet["# Outer Contours"], 
        general_params_sheet["Spot Compensation (Multiple)"], general_params_sheet["Volume Offset Hatch (mm)"]])
    general_params = general_params[:, ~np.isnan(general_params).any(axis=0)] # Long story short, filters out NaN columns
    general_params = np.hstack([arr.reshape(-1, 1) for arr in general_params]).astype(np.uint)
    debug_file.write("general_params: \n{}\n".format(general_params))

    # Get the custom parameters to go along with the provided ids 
    custom_params_sheet = excel_file.parse(3)
    custom_params = np.array([custom_params_sheet["Param 1"], custom_params_sheet["Param 2"], 
        custom_params_sheet["Param 3"], custom_params_sheet["Param 4"], 
        custom_params_sheet["Param 5"]])
    custom_params = custom_params[:, ~np.isnan(custom_params).any(axis=0)] # Long story short, filters out NaN columns
    custom_params = np.hstack([arr.reshape(-1, 1) for arr in custom_params]).astype(np.uint)
    debug_file.write("custom_params: \n{}\n".format(custom_params))

    # Can't do fancy numpy stuff because they aren't all the same data type (scan paths are strings)
    output = []
    for i in range(len(ids)):
        output.append([ids[i], bounds[i], scanpaths[i], general_params[i], custom_params[i]])
    return output 