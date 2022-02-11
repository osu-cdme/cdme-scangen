# This is a utility to allow the creation of HDF5 type files from scanpath data generated by the pyslm based slicer.

import numpy as np
import h5py
import xml.etree.ElementTree as ET
import math
import os

# Adds a layer to an existing HDF5 file.
def addHDF5Layer(HDF5FileName:str,layer:h5py.File):
    top=h5py.File(HDF5FileName,'r+')
    thisLayer=top.create_group(layer.name)


# generates an n by 1 numpy array listing the powers in order of each step in the print for the layer passed in
def generatePowerList(layerTree:ET.ElementTree):
    powerList = np.array([])
    trajectoryTree = layerTree.find('.//TrajectoryList')
    if not trajectoryTree:
        raise ValueError('No TrajectoryList found in layerTree')
    segmentStyleTree = layerTree.find('.//SegmentStyleList')
    if not segmentStyleTree:
        raise ValueError('No SegmentStyleList found in layerTree')
    
    # this section pulls every segment from the trajectory list, finds the segstyle attached to it, pulls the power from that segstyle and collects them in a list
    for segment in trajectoryTree.findall('.//Segment'):
        styleID = segment.find('.//SegStyle').text
        segmentStyles = segmentStyleTree.findall(".//SegmentStyle")

        # Get power based on linked segStyle and whether it's a jump or not 
        found = False
        for segmentStyle in segmentStyles:
            if segmentStyle.find('.//ID').text == styleID:
                if len(segmentStyle.findall('.//Traveler')):
                    powerList = np.append(powerList, int(segmentStyle.find('.//Power').text))
                else:
                    pass
                    # powerList = np.append(powerList, 0)
                found = True
                break

        if not found:
            raise ValueError('SegmentStyleID {} not found in SegmentStyleList'.format(styleID)) 

    print(len(powerList))

    return powerList

# generate an n by 1 numpy array listing the velocities in order of each step in the print for the layer passed in
def generateVelocityList(layerTree:ET.ElementTree):
    velocityList = np.array([])
    trajectoryTree = layerTree.find('TrajectoryList')
    segmentStyleTree = layerTree.find('SegmentStyleList')
    VelocityProfileTree = layerTree.find('VelocityProfileList')

    for segment in trajectoryTree.findall('Segment'):
        associatedSegStyle = segmentStyleTree.find(segment.find('segStyle'))
        associatedVelocityProfile = VelocityProfileTree.find(associatedSegStyle.find('VelocityProfileID'))
        velocity = associatedVelocityProfile.find('Velocity')

        velocityList = np.append(velocityList, velocity)

    return velocityList

# generates an n by 2 numpy array listing each vertex in order of the print for the layer passed in
def generatePointList(layerTree:ET.ElementTree):
    pointList = np.array([])
    trajectoryTree = layerTree.find('TrajectoryList')

    # There is a separate start point for each path so the paths must be iterated through to pull it since its not labelled a segment
    for path in trajectoryTree.findall("Path"):

        startPoint = path.find('Start')
        startX = startPoint.find('X')
        startY = startPoint.find('Y')

        pointList = np.append(pointList,[startX,startY])

        for segment in path.findall('Segment'):
            x = segment.find('X')
            y = segment.find('Y')

            pointList = np.append(pointList,[x,y])

    return pointList

# generates an n by 2 list of edges where the entries are the index of the start and end points in the pointList (NOTE:kinda redundant? the point list is ordered)
def generateEdges(pointList:np.ndarray):
    edgeList = np.array([])

    pointListLength = len(pointList)
    for i in range(pointListLength-1):
        edgeList = np.append(edgeList,[i,i+1])

    return edgeList

def generateTimeList(layerTree:ET.ElementTree):
    segmentStyleTree = layerTree.find('SegmentStyleList')
    VelocityProfileTree = layerTree.find('VelocityProfileList')
    timeList = np.array([])
    trajectoryTree = layerTree.find('TrajectoryList')

    timeList = np.append(timeList,0.0)

    # There is a separate start point for each path so the paths must be iterated through to pull it since its not labelled as a segment
    for path in trajectoryTree.findall("Path"):
        startPoint = path.find('Start')
        startX = startPoint.find('X')
        startY = startPoint.find('Y')

        for segment in path.findall('Segment'):
            endX = segment.find('X')
            endY = segment.find('Y')

            # this chunk finds the speed associated with the current end point
            associatedSegStyle = segmentStyleTree.find(segment.find('segStyle'))
            associatedVelocityProfile = VelocityProfileTree.find(associatedSegStyle.find('VelocityProfileID'))
            velocity = associatedVelocityProfile.find('Velocity')

            distance = math.sqrt(pow(endX-startX,2)+pow(endY-startY,2))

            time = distance/velocity

            timeList = np.append(timeList,time)

            # need to update the start point for the distance on the next iteration through loop
            startX = endX
            startY = endY

    return timeList

# Makes an HDF5 file for a layer from a layer file from a .scn file, the .scn must be unzipped and the individual layer file passed in
def convertLayerSCNtoHDF5(fileDirectory:str,root:h5py.File,layerNum:int):
    print("fileDirectory: " + str(fileDirectory))
    layerTree = ET.parse(fileDirectory)
    treeRoot = layerTree.getroot()
    print("treeRoot: " + str(treeRoot))
    for child in treeRoot: 
        print(child)
        for child2 in child: 
            print(child2)
            for child3 in child2:
                print(child3)
    layerFolder = root.create_group(str(layerNum))
    
    print('converting layer folder')

    print("Generating power list")
    layerFolder.create_dataset('/'+str(layerNum)+'/edgeData/power', data=generatePowerList(layerTree))
    print("generating velocity list")
    velocityList = generateVelocityList(layerTree)    
    layerFolder.create_dataset('/'+str(layerNum)+'/edgeData/velocity',   velocityList)
    print("generating point list")
    pointList = generatePointList(layerTree)
    layerFolder.create_dataset('/'+str(layerNum)+'/points', pointList)
    print("generating edges")
    layerFolder.create_dataset('/'+str(layerNum)+'/edges',  generateEdges(pointList))
    print("generating times")
    layerFolder.create_dataset('/'+str(layerNum)+'/pointData/time', generateTimeList(layerTree))

    return layerFolder
    
# Converts a directory containing the unzipped layer files (.xml suffix) into an HDF5 file. directory must NOT have any other files in it
def convertSCNtoHDF5(inputDirectory:str, outputName:str):
    numLayers = len(os.listdir(inputDirectory + '/'))
    file=h5py.File(outputName,'w')

    for i in range(numLayers):
        convertLayerSCNtoHDF5(inputDirectory + '/scan_' + str(i + 1) + '.xml',file, i)
    
    