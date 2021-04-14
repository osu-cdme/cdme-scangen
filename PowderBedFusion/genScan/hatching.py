import abc
import time
from typing import Any, Tuple, List

from skimage.measure import approximate_polygon, subdivide_polygon

import numpy as np
import pyclipper

from shapely.geometry import Polygon as ShapelyPolygon
from .vectorSort import AlternateSort, BaseSort, LinearSort
from ..genLayer import Layer, Model, LayerGeometry, ContourGeometry, HatchGeometry, PointsGeometry


def getExposurePoints(layer: Layer, models: List[Model], includePowerDeposited: bool = True):
    """
    A utility method to return a list of exposure points given a :class:`Layer` with an associated :class:`Model`
    which contains the :class:`BuildStyle` that provides the point exposure distance or an effective laser speed to
    spatially discretise the scan vectors into a series of points. If the optional parameter `includePowerDeposited` is
    set to True, the laser power deposited in included. Note the :attr:`BuildStyle.pointDistance` parameter must
    be set or this method will fail.

    :param layer: The layer to process
    :param models: A list of models containing buildstyles which are referenced with the layer's :class:`LayerGeometry`
    :param includePowerDeposited: Set to true to return the calculated power deposited.

    :return: Returns a list of coordinates (nx2) in the global domain with an optional power deposited.
    """

    if not isinstance(models, list):
        models = [models]

    exposurePoints = []

    for layerGeom in layer.geometry:

        # Get the model given the mid
        model = next(x for x in models if x.mid == layerGeom.mid)

        # Get the buildstyle from the model
        buildStyle = next(
            x for x in model.buildStyles if x.bid == layerGeom.bid)

        if buildStyle.pointDistance < 1:
            raise ValueError('The point distance parameter in the buildstyle (mid: {:d}, bid: {:d}) must be set'.format(
                model.mid, buildStyle.bid))

        pointDistance = buildStyle.pointDistance * 1e-3  # Convert to mm
        energyPerExposure = buildStyle.laserPower * \
            (buildStyle.pointExposureTime * 1e-6)  # convert to mu s

        if isinstance(layerGeom, HatchGeometry):

            # Calculate the length of the hatch vector and the direction
            coords = layerGeom.coords.reshape(-1, 2, 2)
            delta = np.diff(coords, axis=1).reshape(-1, 2)
            lineDist = np.hypot(delta[:, 0], delta[:, 1]).reshape(-1, 1)

            # Normalise each scan vector direction
            dir = -1.0 * delta / lineDist

            # Calculate the number of exposure points across the hatch vector based on its length
            numPoints = np.ceil(lineDist / pointDistance).astype(np.int)

            # Pre-populate some arrays to extrapolate the exposure points from
            totalPoints = int(np.sum(numPoints))
            idxArray = np.zeros([totalPoints, 1])
            pntsArray = np.zeros([totalPoints, 2])
            dirArray = np.zeros([totalPoints, 2])

            # Take the first coordinate
            p0 = coords[:, 1, :].reshape(-1, 2)

            idx = 0
            for i in range(len(numPoints)):
                j = int(numPoints[i])
                idxArray[idx:idx + j, 0] = np.arange(0, j)
                pntsArray[idx:idx + j] = p0[i]
                dirArray[idx:idx + j] = dir[i]
                idx += j

            # Calculate the hatch exposure points
            hatchExposurePoints = pntsArray + pointDistance * idxArray * dirArray

            # Add an extra column for the energy deposited per exposure
            if includePowerDeposited:
                col = np.ones([len(hatchExposurePoints), 1])
                col[:] = energyPerExposure

                hatchExposurePoints = np.hstack([hatchExposurePoints, col])

            # append to the list
            exposurePoints.append(hatchExposurePoints)

        if isinstance(layerGeom, ContourGeometry):

            # Calculate the length of the hatch vector and the direction
            coords = layerGeom.coords

            delta = np.diff(coords, axis=0)
            lineDist = np.hypot(delta[:, 0], delta[:, 1]).reshape(-1, 1)

            # Normalise each scan vector direction
            dir = 1.0 * delta / lineDist

            # Calculate the number of exposure points across the hatch vector based on its length
            numPoints = np.ceil(lineDist / pointDistance).astype(np.int)

            # Pre-populate some arrays to extrapolate the exposure points from
            totalPoints = int(np.sum(numPoints))
            idxArray = np.zeros([totalPoints, 1])
            pntsArray = np.zeros([totalPoints, 2])
            dirArray = np.zeros([totalPoints, 2])

            # Take the first coordinate
            p0 = coords

            idx = 0
            for i in range(len(numPoints)):
                j = int(numPoints[i])
                idxArray[idx:idx + j, 0] = np.arange(0, j)
                pntsArray[idx:idx + j] = p0[i]
                dirArray[idx:idx + j] = dir[i]
                idx += j

            # Calculate the hatch exposure points
            hatchExposurePoints = pntsArray + pointDistance * idxArray * dirArray

            # Add an extra column for the energy deposited per exposure
            if includePowerDeposited:
                col = np.ones([len(hatchExposurePoints), 1])
                col[:] = energyPerExposure

                hatchExposurePoints = np.hstack([hatchExposurePoints, col])

            # append to the list
            exposurePoints.append(hatchExposurePoints)

    exposurePoints = np.vstack(exposurePoints)

    return exposurePoints


class BaseHatcher(abc.ABC):
    """
    The BaseHatcher class provides common methods used for generating the 'contour' and infill 'hatch' scan vectors.

    The class provides an interface tp generate a variety of hatching patterns used. The developer should re-implement a
    subclass and re-define the abstract method, :~meth:`BaseHatcher.hatch`, which will be called.

    The user typically specifies a boundary, which may be offset the boundary of region using
    :meth:`~BaseHatcher.offsetBoundary`. This is typically performed before generating the infill.
    Following offsetting, the a series of hatch lines are generated using :meth:`~BaseHatcher.generateHatching` to fill
    the entire boundary region using :meth:`~BaseHatcher.polygonBoundingBox`. To obtain the final clipped in-fill, the
    hatches are clipped using :meth:`~BaseHatcher.clipLines` which are clipped in the same sequential order they are generated using a technique
    explained further in the class method. The generated scan paths should be stored into collections of LayerGeometry
    accordingly.

    For all polygon manipulation operations used for offsetting and clipping, internally this calls provides automatic
    conversion to the integer coordinate system used by ClipperLib by internally calling
    :meth:`~BaseHatcher.scaleToClipper` and :meth:`~BaseHatcher.scaleFromClipper`.
    """

    PYCLIPPER_SCALEFACTOR = 1e4
    """
    The scaling factor used for polygon clipping and offsetting in `PyClipper <http://pyclipper.com>`_ for the decimal
    component of each polygon coordinate. This should be set to inverse of the required decimal tolerance i.e. 0.01
    requires a minimum scalefactor of 1e2. This scaling factor is used in :meth:`~BaseHatcher.scaleToClipper`
    and :meth:`~BaseHatcher.scaleFromClipper`.
    """

    def __init__(self):
        pass

    def __str__(self):
        return 'BaseHatcher <{:s}>'.format(self.name)

    def scaleToClipper(self, feature: Any):
        """
        Transforms geometry created **to pyclipper**  by upscaling into the integer coordinates  **from** the original
        floating point coordinate system.

        :param feature: The geometry to scale to pyclipper
        :return: The scaled geometry
        """
        return pyclipper.scale_to_clipper(feature, BaseHatcher.PYCLIPPER_SCALEFACTOR)

    def scaleFromClipper(self, feature: Any):
        """
        Transforms geometry created **from pyclipper** upscaled integer coordinates back **to** the original
        floating point coordinate system.

        :param feature: The geometry to scale to pyclipper
        :return: The scaled geometry
        """
        return pyclipper.scale_from_clipper(feature, BaseHatcher.PYCLIPPER_SCALEFACTOR)

    @classmethod
    def error(cls) -> float:
        """
        Returns the accuracy of the polygon clipping depending on the chosen scale factor :attr:`.PYCLIPPER_SCALEFACTOR`.
        """
        return 1. / cls.PYCLIPPER_SCALEFACTOR

    def offsetPolygons(self, polygons, offset: float):
        """
        Offsets a set of boundaries across a collection of polygons by the offset parameter.

        .. note::
            Note that if any polygons are expanded overlap with adjacent polygons, the offsetting will **NOT** unify
            into a single shape.

        :param polygons: A list of closed polygons which are individually offset from each other.
        :param offset: The offset distance applied to the polygon
        :return: A list of boundaries offset from the subject
        """
        return [self.offsetBoundary(poly, offset) for poly in polygons]

    def offsetBoundary(self, paths, offset: float):
        """
        Offsets a single path for a single polygon.

        :param paths: Closed polygon path list for offsetting
        :param offset: The offset applied to the poylgon
        :return: A list of boundaries offset from the subject
        """
        pc = pyclipper.PyclipperOffset()

        clipperOffset = self.scaleToClipper(offset)

        # Append the paths to libClipper offsetting algorithm
        for path in paths:
            pc.AddPath(self.scaleToClipper(path),
                       pyclipper.JT_ROUND,
                       pyclipper.ET_CLOSEDPOLYGON)

        # Perform the offseting operation
        boundaryOffsetPolys = pc.Execute2(clipperOffset)

        offsetContours = []
        # Convert these nodes back to paths
        for polyChild in boundaryOffsetPolys.Childs:
            offsetContours += self._getChildPaths(polyChild)

        return offsetContours

    def _getChildPaths(self, poly):

        offsetPolys = []

        # Create single closed polygons for each polygon
        paths = [path.Contour for path in poly.Childs]  # Polygon holes
        paths.append(poly.Contour)  # Path holes

        # Append the first point to the end of each path to close loop
        for path in paths:
            path.append(path[0])

        paths = self.scaleFromClipper(paths)

        offsetPolys.append(paths)

        for polyChild in poly.Childs:
            if len(polyChild.Childs) > 0:
                for polyChild2 in polyChild.Childs:
                    offsetPolys += self._getChildPaths(polyChild2)

        return offsetPolys

    def boundaryBoundingBox(self, boundaries):
        """
        Returns the bounding box of a list of boundaries, typically generated by the tree representation in PyClipper.

        :param boundaries: A list of polygon
        :return: A (1x6) numpy array
        """

        # Essentially iterates through all vertices in boundingBox and gets min-x, min-y, max-x, max-y coordinates
        # Would also theoretically work with z-coordinates, but we trim those out at some point in here with all the [:2] stuff
        bboxList = [self.polygonBoundingBox(
            boundary) for boundary in boundaries]

        # Takes individual boundary bboxes and compiles them all to get the overall bounding box
        bboxList = np.vstack(bboxList)
        bbox = np.hstack([np.min(bboxList[:, :2], axis=0),
                         np.max(bboxList[:, -2:], axis=0)])

        return bbox

    def polygonBoundingBox(self, obj) -> np.ndarray:
        """
        Returns the bounding box of the polygon - typically this represents a single shape with an exterior and a list of
        boundaries within an array

        :param obj: Geometry object
        :return: A (1x6) numpy array representing the bounding box of a polygon
        """
        # Path (n,2) coords that

        if not isinstance(obj, list):
            obj = [obj]

        bboxList = []

        for subObj in obj:
            path = np.array(subObj)[:, :2]  # Use only coordinates in XY plane

            # np.min(path, axis=0) iterates through each coord and returns pair made of minimum x present and minimum y present
            # The max function works similarly
            bboxList.append(
                np.hstack([np.min(path, axis=0), np.max(path, axis=0)]))

        # The above loop gets bboxes for individual sequences; this takes the bboxes of all those sequences and outputs one overall bbox square
        bboxList = np.vstack(bboxList)
        bbox = np.hstack([np.min(bboxList[:, :2], axis=0),
                         np.max(bboxList[:, -2:], axis=0)])

        return bbox

    def clipLines(self, paths, lines):
        """
        This function clips a series of lines (hatches) across a closed polygon using pyclipper.

        .. note ::
            The order is guaranteed from the list of lines used, so these do not require sorting usually. However,
            the position may require additional sorting to cater for the user's requirements.

        :param paths: The set of boundary paths for trimming the lines
        :param lines: The un-trimmed lines to clip from the boundary

        :return: A list of trimmed lines (open paths)
        """

        startTime = time.time()

        pc = pyclipper.Pyclipper()

        for path in paths:
            coords = self.scaleToClipper(path)
            for boundary in path:
                pc.AddPath(self.scaleToClipper(boundary),
                           pyclipper.PT_CLIP, True)

        # print('time to add polygon', time.time()-startTime, 's')
        startTime = time.time()

        # Reshape line list to create n lines with 2 coords(x,y,z)
        lineList = lines.reshape(-1, 2, 3)
        lineList = tuple(map(tuple, lineList))
        lineList = self.scaleToClipper(lineList)

        pc.AddPaths(lineList, pyclipper.PT_SUBJECT, False)

        # print('time to add hatches', time.time() - startTime, 's')
        startTime = time.time()

        # Note open paths (lines) have to used PyClipper::Execute2 in order to perform trimming
        result = pc.Execute2(pyclipper.CT_INTERSECTION,
                             pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)

        # print('time to clip hatches', time.time() - startTime, 's')
        startTime = time.time()

        # Cast from PolyNode Struct from the result into line paths since this is not a list
        lineOutput = pyclipper.PolyTreeToPaths(result)

        return self.scaleFromClipper(lineOutput)

    def generateHatching(self, paths, hatchSpacing: float, hatchAngle: float = 90.0) -> np.ndarray:
        """
        Generates un-clipped hatches which is guaranteed to cover the entire polygon region base on the maximum extent
        of the polygon bounding box

        :param paths: Boundary paths to generate hatches to cover
        :param hatchSpacing: Hatch Spacing to use
        :param hatchAngle: Hatch angle (degrees) to rotate the scan vectors

        :return: Returns the list of unclipped scan vectors

        """

        # Hatch angle
        theta_h = np.radians(hatchAngle)  # 'rad'

        # Feed all our paths in, and this gives us a 1x4 array in order min-x, min-y, max-x, max-y
        bbox = self.boundaryBoundingBox(paths)

        # Expand the bounding box
        # This reshape will make the first row min-x/min-y and the second row max-x/max-y,
        #   and the axis=0 means mean will get the mean of the first elements then the mean of the second elements
        test = bbox.reshape(2, 2)
        bboxCentre = np.mean(bbox.reshape(2, 2), axis=0)

        # Calculates the diagonal length for which is the longest
        diagonal = bbox[2:] - bboxCentre

        # Dotting a vector with itself is square of its magnitude, so this line is just a quick way to get vector magnitude
        # Not sure why numpy.linalg.norm(diagonal) wasn't used but we don't need to understand the specifics I suppose
        bboxRadius = np.sqrt(diagonal.dot(diagonal))

        # Construct a square which wraps the radius
        # We space hatches along the x and then rotate all the hatches;
        #   We hatch to the outermost bbox point, so we can do this without worrying

        # Question: This basically duplicates each value; why? Is that intentional?
        # Answer: The y-values get tiled such that each x-value is tied to a pair of y-values.
        # Presumably, we tile this twice because even at 45deg, we will still have enough hatches to fill the entire area
        x = np.tile(np.arange(-bboxRadius, bboxRadius, hatchSpacing,
                              dtype=np.float32).reshape(-1, 1), (2)).flatten()
        y = np.array([-bboxRadius, bboxRadius])
        y = np.resize(y, x.shape)
        z = np.arange(0, x.shape[0] / 2, 0.5).astype(np.int64)

        # This doesn't just contenate them all; this basically says that the first triplet is the first x, the first
        # y, then the first z, then does so with the second, and on and on and on...
        coords = np.hstack([x.reshape(-1, 1),
                            y.reshape(-1, 1),
                            z.reshape(-1, 1)])

        # Create the 2D rotation matrix with an additional row, column to preserve the hatch order
        c, s = np.cos(theta_h), np.sin(theta_h)
        R = np.array([(c, -s, 0),
                      (s, c, 0),
                      (0, 0, 1.0)])

        # Apply the rotation matrix and translate to bounding box centre
        coords = np.matmul(R, coords.T)
        coords = coords.T + np.hstack([bboxCentre, 0.0])

        return coords

    def clipperToHatchArray(self, coords: np.ndarray) -> np.ndarray:
        """
        A helper method which converts the raw polygon edge lists returned by pyclipper into a numpy array.

        :param coords: The list of hatches generated from pyclipper
        :return: The hatch coordinates transfromed into a (n x 2 x 3) numpy array.
        """
        return np.transpose(np.dstack(coords), axes=[2, 0, 1])

    @ abc.abstractmethod
    def hatch(self, boundaryFeature) -> Layer:
        """
        The hatch method should be re-implemented by a child class to generate a :class:`Layer` containing the scan
        vectors used for manufacturing the layer.

        :param boundaryFeature: The collection of boundaries of closed polygons within a layer.
        :raises: :class:`NotImplementedError`
        """
        raise NotImplementedError()


class InnerHatchRegion(abc.ABC):
    """
    The InnerHatchRegion class provides a representation for a single sub-region used for efficiently generating
    various sub-scale hatch infills. This requires providing a boundary (:attr:`~InnerHatchRegion.boundary`) to represent
    the region used. The user typically in dervived :class:`BaseHatcher` class should set via
    :meth:`~InnerHatchRegion.setRequiresClipping` if the region requires further clipping.

    Finally the derived class must generate a set of hatch vectors covering the boundary region, by re-implementing the
    abstract method :meth:`~InnerHatchRegion.hatch`. If the boundary requires clipping, the interior hatches are also
    clipped.
    """

    def __init__(self):

        self._origin = np.array([[0, 0]])
        self._orientation = 0.0

        self._region = []
        self._requiresClipping = False
        self._isIntersecting = False

    def transformCoordinates2D(self, coords: np.ndarray) -> np.ndarray:
        """
        Transforms a set of (n x 2) coordinates using the rotation angle
        :attr:`InnerHatchRegion.orientation` using the 2D rotation matrix in :meth:`InnerHatchRegion.rotationMatrix2D`.

        :param coords: (nx2) coordinates to be transformed
        :return:  The transformed coordinates
        """
        R = self.rotationMatrix2D()

        # Apply the rotation matrix and translate to bounding box centre
        coords = np.matmul(R, coords.T)
        coords = coords.T + np.hstack([self._origin])

        return coords

    def transformCoordinates(self, coords: np.ndarray) -> np.ndarray:
        """
        Transforms a set of (n x 3) coordinates with a sort id using the rotation angle
        :attr:`InnerHatchRegion.orientation` using the 3D rotation matrix in :meth:`InnerHatchRegion.rotationMatrix3D`.

        :param coords: (nx3) coordinates to be transformed
        :return:  The transformed coordinates
        """

        R = self.rotationMatrix3D()

        # Apply the rotation matrix and translate to bounding box centre
        coords = np.matmul(R, coords.T).T
        coords[:, :2] += self._origin

        return coords

    def rotationMatrix2D(self) -> np.ndarray:
        """
        Generates an affine matrix covering the transformation based on the origin and orientation based on a rotation
        around the local coordinate system. This should be used when only a series of x,y coordinate required to be
        transformed.

        :return: Affine Transformation Matrix
        """
        # Create the rotation matrix
        c, s = np.cos(self._orientation), np.sin(self._orientation)
        R = np.array([(c, -s),
                      (s, c)])
        return R

    def rotationMatrix3D(self) -> np.ndarray:
        """
        Generates an affine matrix covering the transformation based on the origin and orientation based on a rotation
        around the local coordinate system. A pseudo third row and column is provided to retain the hatch sort id used.

        :return: Affine Transformation Matrix
        """
        # Create the rotation matrix
        c, s = np.cos(self._orientation), np.sin(self._orientation)
        R = np.array([(c, -s, 0),
                      (s, c, 0),
                      (0, 0, 1.0)])

        # T = np.diag([1.0,1.0,0])
        # T[:2,:2] = self._origin

        return R

    @ property
    def orientation(self) -> float:
        """
        The orientation describes the rotation of the local coordinate system with respect to the global
        coordinate system :math:`(x,y)`. The angle of rotation is given in rads.
        """
        return self._orientation

    @ orientation.setter
    def orientation(self, angle: float):
        self._orientation = angle

    @ property
    def origin(self):
        """ The origin is the :math:`(x\\prime,y\\prime)` position of of the local coordinate system. """
        return self._origin

    @ origin.setter
    def origin(self, coord):
        self._origin = coord

    def setIntersecting(self, intersectingState: bool) -> None:
        """
        Setting True indicates the region has been intersected

        :param intersectingState: True if the region intersects
        """
        self._isIntersecting = intersectingState

    def setRequiresClipping(self, clippingState: bool) -> None:
        """
        Sets the internal region to require additional clipping following hatch generation.

        :param clippingState: True if the region requires additional clipping
        """
        self._requiresClipping = True

    def __str__(self):
        return 'InnerHatchRegion <{:s}>'

    @ abc.abstractmethod
    def boundary(self) -> ShapelyPolygon:
        """ The boundary of the internal region

        :raises: :class:`NotImplementedError`
        """
        raise NotImplementedError

    def isIntersecting(self) -> bool:
        """
        Returns if the region requires additional clipping.
        """

        return self._isIntersecting

    def requiresClipping(self) -> bool:
        """
        Returns if the region requires additional clipping.
        """
        return self._requiresClipping

    @ abc.abstractmethod
    def hatch(self) -> np.ndarray:
        """
        The hatch method should provide a list of hatch vectors, within the boundary. This must  be re-implemented in
        the derived class. The hatch vectors should be ordered.

        :raises: :class:`NotImplementedError`
        """
        raise NotImplementedError()


class Hatcher(BaseHatcher):
    """
    Provides a generic SLM Hatcher 'recipe' with standard parameters for defining the hatch across regions. This
    includes generating multiple contour offsets and then a generic hatch infill pattern by re-implementing the
    :meth:`BaseHatcher.hatch` method. This class may be derived from to provide additional or customised behavior.
    """

    def __init__(self):

        super().__init__()

        # Contour private attributes
        self._numInnerContours = 1
        self._numOuterContours = 1
        self._spotCompensation = 0.08  # mm
        self._contourOffset = 1.0 * self._spotCompensation
        self._volOffsetHatch = self._spotCompensation

        # Hatch private attributes
        self._layerAngleIncrement = 0  # 66 + 2 / 3
        self._hatchDistance = 0.08  # mm
        self._hatchAngle = 45
        self._hatchSortMethod = None

    @ property
    def hatchDistance(self) -> float:
        """ The distance between adjacent hatch scan vectors. """
        return self._hatchDistance

    @ hatchDistance.setter
    def hatchDistance(self, value: float):
        self._hatchDistance = value

    @ property
    def hatchAngle(self) -> float:
        """ The base hatch angle used for hatching the region expressed in degrees :math:`[-180,180]`."""
        return self._hatchAngle

    @ hatchAngle.setter
    def hatchAngle(self, value: float):
        self._hatchAngle = value

    @ property
    def layerAngleIncrement(self) -> float:
        """
        An additional offset used to increment the hatch angle between layers in degrees. This is typically set to
        66.6:math:`^{\circ}` per layer to provide additional uniformity of the scan vectors across multiple layers.
        By default this is set to 0.0"""
        return self._layerAngleIncrement

    @ layerAngleIncrement.setter
    def layerAngleIncrement(self, value):
        self._layerAngleIncrement = value

    @ property
    def hatchSortMethod(self):
        """ The hatch sort method used once the hatch vectors have been generated """
        return self._hatchSortMethod

    @ hatchSortMethod.setter
    def hatchSortMethod(self, sortObj):
        if not isinstance(sortObj, BaseSort):
            raise TypeError(
                "The Hatch Sort Method should be derived from the BaseSort class")

        self._hatchSortMethod = sortObj

    @ property
    def numInnerContours(self) -> int:
        """
        The total number of inner contours to generate by offsets from the boundary region.
        """
        return self._numInnerContours

    @ numInnerContours.setter
    def numInnerContours(self, value: int):
        self._numInnerContours = value

    @ property
    def numOuterContours(self) -> int:
        """
        The total number of outer contours to generate by offsets from the boundary region.
        """
        return self._numOuterContours

    @ numOuterContours.setter
    def numOuterContours(self, value: int):
        self._numOuterContours = value

    @ property
    def spotCompensation(self) -> float:
        """
        The spot (laser point) compensation factor is the distance to offset the outer-boundary and other internal hatch
        features in order to factor in the exposure radius of the laser.
        """
        return self._spotCompensation

    @ spotCompensation.setter
    def spotCompensation(self, value: float):
        self._spotCompensation = value

    @ property
    def volumeOffsetHatch(self) -> float:
        """
        An additional offset may be added (positive or negative) between the contour and the internal hatching.
        """
        return self._volOffsetHatch

    @ volumeOffsetHatch.setter
    def volumeOffsetHatch(self, value: float):
        self._volOffsetHatch = value

    def hatch(self, boundaryFeature):
        """
        Generates a series of contour or boundary offsets along with a basic full region internal hatch.

        :param boundaryFeature: The collection of boundaries of closed polygons within a layer. Comes from Part.getVectorSlice(z).
        :return: A :class:`Layer` object containing a list of :class:`LayerGeometry` objects generated
        """

        # Essentially a check that our input slice isn't empty; boundaryFeature is Part.getVectorSlice(z)'s output.
        if len(boundaryFeature) == 0:
            return

        # Init new layer to hold all the hatches we are about to fill it with
        layer = Layer(0, 0)

        # First generate a boundary with the spot compensation applied
        # Spot compensation is essentially
        offsetDelta = 0.0
        offsetDelta -= self._spotCompensation

        # Generate outer contours by continually updating offsetDelta to be the distance from complete outside to the current contour
        for i in range(self._numOuterContours):
            offsetDelta -= self._contourOffset
            offsetBoundary = self.offsetBoundary(boundaryFeature, offsetDelta)

            for poly in offsetBoundary:
                for path in poly:

                    # Represents a continuous path, unlike hatching, which has jumps included
                    contourGeometry = ContourGeometry()

                    # Grab the actual vertices
                    contourGeometry.coords = np.array(path)[:, :2]

                    # Referenced later (at least, during visualization, if not more)
                    contourGeometry.subType = "outer"

                    # Append to the layer
                    layer.geometry.append(contourGeometry)

        # Repeat the above for inner contours
        for i in range(self._numInnerContours):

            offsetDelta -= self._contourOffset
            offsetBoundary = self.offsetBoundary(boundaryFeature, offsetDelta)

            for poly in offsetBoundary:
                for path in poly:
                    contourGeometry = ContourGeometry()
                    contourGeometry.coords = np.array(path)[:, :2]
                    contourGeometry.subType = "inner"  # Only difference from above
                    layer.geometry.append(contourGeometry)

        # The final offset is applied to the boundary
        # volOffsetHatch is essentially the distance between contours and hatches; very similar to OASIS's hatch-to-contour spacing
        offsetDelta -= self._volOffsetHatch
        curBoundary = self.offsetBoundary(boundaryFeature, offsetDelta)

        # The function now moves on from contours and starts generating the actual hatches inside the given boundary
        scanVectors = []

        # This if works correctly if curBoundary is just one boundary; the second loop here (which never gets run because it's the `else` of an `if True`)
        #   works if curBoundary is an iterable of some sort, likely just a numpy array.
        # TODO: These code blocks are the same other than the second one doing the iteration; should be an easy way to avoid rewriting that code. For example, make curBoundary a one-long list. I'm just not editing that right now because I'm just documenting and it isn't strictly necessary.
        if True:

            # paths is set to our overall layer geometry set waaaaay inward
            paths = curBoundary

            # Figure out what hatch angle should be this layer
            # Hatch angle will change per layer
            # TODO change the layer angle increment
            layerHatchAngle = np.mod(
                self._hatchAngle + self._layerAngleIncrement, 180)

            # We constrain hatchAngle to be [-90, 90];
            # this is because, for example, -30deg is the same as 150deg and we don't want that ambiguity

            # The layer hatch angle needs to be bound by +ve X vector (i.e. -90 < theta_h < 90 )
            if layerHatchAngle > 90:
                layerHatchAngle = layerHatchAngle - 180

            # Actually generates the hatches given the outline of the area we want, the space between hatches (I think?) and the hatch angle
            # TODO: Verify that _hatchDistance is the same thing as the space between hatches

            # Generate the un-clipped hatch regions based on the layer hatchAngle and hatch distance
            hatches = self.generateHatching(
                paths, self._hatchDistance, layerHatchAngle)

            # The value we get back from generateHatching isn't constrainted to the bounds of the boundary 'paths' that we passed in, so we do that here
            # Clip the hatch fill to the boundary
            clippedPaths = self.clipLines(paths, hatches)

            # Merge the lines together
            if len(clippedPaths) > 0:

                # Turns the input clippedPaths sequence into a (nx2x3) numpy array;
                #   n is # of hatches, 2 is how many vertices per hatch, and 3 is xyz of each vertex
                # TODO: Figure out: On actual debugging; this array is actually nx2x2... why?
                clippedLines = self.clipperToHatchArray(clippedPaths)

                # Extract only x-y coordinates and sort based on the pseudo-order stored in the z component.
                # TODO: Figure out: If we are just grabbing xyz coordinates, shouldn't the indexing be :2 instead of :3?
                clippedLines = clippedLines[:, :, :3]
                id = np.argsort(clippedLines[:, 0, 1])
                clippedLines = clippedLines[id, :, :]

                scanVectors.append(clippedLines)

        # Variant of the `if` block that treats curBoundary like an iterable; I assume it's used if you have several hollow areas, but the current code doesn't treat it that way
        else:

            # Iterate through each closed polygon region in the slice. The currently individually sliced.
            for contour in curBoundary:
                # print('{:=^60} \n'.format(' Generating hatches '))

                paths = contour

                # Hatch angle will change per layer
                # TODO change the layer angle increment
                layerHatchAngle = np.mod(
                    self._hatchAngle + self._layerAngleIncrement, 180)

                # The layer hatch angle needs to be bound by +ve X vector (i.e. -90 < theta_h < 90 )
                if layerHatchAngle > 90:
                    layerHatchAngle = layerHatchAngle - 180

                # Generate the un-clipped hatch regions based on the layer hatchAngle and hatch distance
                hatches = self.generateHatching(
                    paths, self._hatchDistance, layerHatchAngle)

                # Clip the hatch fill to the boundary
                clippedPaths = self.clipLines(paths, hatches)

                # Merge the lines together
                if len(clippedPaths) == 0:
                    continue

                clippedLines = self.clipperToHatchArray(clippedPaths)

                # Extract only x-y coordinates and sort based on the pseudo-order stored in the z component.
                clippedLines = clippedLines[:, :, :3]
                id = np.argsort(clippedLines[:, 0, 2])
                clippedLines = clippedLines[id, :, :]

                scanVectors.append(clippedLines)

        # If we have scan vectors...
        if len(clippedLines) > 0:
            # Scan vectors have been created for the hatched region

            # Construct a HatchGeometry containing the list of points
            # HatchGeometry is similar to ContourGeometry, but includes Jump vectors, which ContourGeometry can ignore due to it being one continuous line
            hatchGeom = HatchGeometry()

            # Only copy the (x,y) points from the coordinate array.
            # Essentially transposing it because... sure?
            hatchVectors = np.vstack(scanVectors)
            # Trim z-coords (this one is expected, the :3 above is something I'm confused by)
            hatchVectors = hatchVectors[:, :, :2].reshape(-1, 2)

            # Note the does not require positional sorting
            # I assume this is for cases where you want to reorder your hatches
            if self.hatchSortMethod:
                hatchVectors = self.hatchSortMethod.sort(hatchVectors)

            hatchGeom.coords = hatchVectors

            layer.geometry.append(hatchGeom)

        return layer


class StripeHatcher(Hatcher):
    """
    The Stripe Hatcher extends the standard :class:`Hatcher` but generates a set of stripe hatches of a fixed width
    (:attr:`~.stripeWidth`) to cover a region.
    This has the effect of limiting the max length of the scan vectors  across a region in order to mitigate the
    effects of residual stress.
    """

    def __init__(self):
        super().__init__()

        self._stripeWidth = 5.0
        self._stripeOverlap = 0.1
        self._stripeOffset = 0.5

    def __str__(self):
        return 'StripeHatcher'

    @ property
    def stripeWidth(self) -> float:
        """ The stripe width """
        return self._stripeWidth

    @ stripeWidth.setter
    def stripeWidth(self, width):
        self._stripeWidth = width

    @ property
    def stripeOverlap(self) -> float:
        """ The length of overlap between adjacent stripes"""
        return self._stripeOverlap

    @ stripeOverlap.setter
    def stripeOverlap(self, overlap: float):
        self._stripeOverlap = overlap

    @ property
    def stripeOffset(self) -> float:
        """ The stripe offset is the relative distance (hatch spacing) to move the scan vectors between adjacent stripes"""
        return self._stripeOffset

    @ stripeOffset.setter
    def stripeOffset(self, offset: float):
        self._stripeOffset = offset

    def generateHatching(self, paths, hatchSpacing: float, hatchAngle: float = 90.0) -> np.ndarray:
        """
        Generates un-clipped hatches which is guaranteed to cover the entire polygon region based on the maximum extent
        of the polygon bounding box

        :param paths:
        :param hatchSpacing: Hatch Spacing to use
        :param hatchAngle: Hatch angle (degrees) to rotate the scan vectors

        :return: Returns the list of unclipped scan vectors

        """
        # Hatch angle
        theta_h = np.radians(hatchAngle)  # 'rad'

        # Get the bounding box of the paths
        bbox = self.boundaryBoundingBox(paths)

        # Expand the bounding box
        bboxCentre = np.mean(bbox.reshape(2, 2), axis=0)

        # Calculates the diagonal length for which is the longest
        diagonal = bbox[2:] - bboxCentre
        bboxRadius = np.sqrt(diagonal.dot(diagonal))

        numStripes = int(2 * bboxRadius / self._stripeWidth) + 1

        # Construct a square which wraps the radius
        hatchOrder = 0
        coords = []

        for i in np.arange(0, numStripes):
            startX = -bboxRadius + i * self._stripeWidth - self._stripeOverlap
            endX = startX + self._stripeWidth + self._stripeOverlap

            y = np.tile(np.arange(-bboxRadius + np.mod(i, 2) * self._stripeOffset * hatchSpacing,
                                  bboxRadius +
                                  np.mod(i, 2) * self._stripeOffset *
                                  hatchSpacing, hatchSpacing,
                                  dtype=np.float32).reshape(-1, 1), (2)).flatten()
            # x = np.tile(np.arange(startX, endX, hatchSpacing, dtype=np.float32).reshape(-1, 1), (2)).flatten()
            x = np.array([startX, endX])
            x = np.resize(x, y.shape)
            z = np.arange(hatchOrder, hatchOrder +
                          y.shape[0] / 2, 0.5).astype(np.int64)

            hatchOrder += x.shape[0] / 2

            coords += [np.hstack([x.reshape(-1, 1),
                                  y.reshape(-1, 1),
                                  z.reshape(-1, 1)])]

        coords = np.vstack(coords)

        # Create the rotation matrix
        c, s = np.cos(theta_h), np.sin(theta_h)
        R = np.array([(c, -s, 0),
                      (s, c, 0),
                      (0, 0, 1.0)])

        # Apply the rotation matrix and translate to bounding box centre
        coords = np.matmul(R, coords.T)
        coords = coords.T + np.hstack([bboxCentre, 0.0])

        return coords


class BasicIslandHatcher(Hatcher):
    """
    BasicIslandHatcher extends the standard :class:`Hatcher` and generates a set of islands of fixed size (:attr:`.islandWidth`)
    which covers a region. This has the effect of limiting the max length of the scan whilst by orientating the scan vectors orthogonal to each other
    mitigating any preferential distortion or curling in a single direction and any effects to micro-structure.

    """

    def __init__(self):

        super().__init__()

        self._islandWidth = 5.0
        self._islandOverlap = 0.1
        self._islandOffset = 0.5

    def __str__(self):
        return 'IslandHatcher'

    @ property
    def islandWidth(self) -> float:
        """ The island width """
        return self._islandWidth

    @ islandWidth.setter
    def islandWidth(self, width: float):
        self._islandWidth = width

    @ property
    def islandOverlap(self) -> float:
        """ The length of overlap between adjacent islands"""
        return self._islandOverlap

    @ islandOverlap.setter
    def islandOverlap(self, overlap: float):
        self._islandOverlap = overlap

    @ property
    def islandOffset(self) -> float:
        """ The island offset is the relative distance (hatch spacing) to move the scan vectors between adjacent checkers. """
        return self._islandOffset

    @ islandOffset.setter
    def islandOffset(self, offset: float):
        self._islandOffset = offset

    def generateHatching(self, paths, hatchSpacing: float, hatchAngle: float = 90.0) -> np.ndarray:
        """
        Generates un-clipped hatches which is guaranteed to cover the entire polygon region base on the maximum extent
        of the polygon bounding box.
        :param paths: The boundaries that the hatches should fill entirely
        :param hatchSpacing: The hatch spacing
        :param hatchAngle: The hatch angle (degrees) to rotate the scan vectors
        :return: Returns the list of unclipped scan vectors covering the region
        """
        # Hatch angle
        theta_h = np.radians(hatchAngle)  # 'rad'

        # Get the bounding box of the paths
        bbox = self.boundaryBoundingBox(paths)

        # Expand the bounding box
        bboxCentre = np.mean(bbox.reshape(2, 2), axis=0)

        # Calculates the diagonal length for which is the longest
        diagonal = bbox[2:] - bboxCentre
        bboxRadius = np.sqrt(diagonal.dot(diagonal))

        numIslands = int(2 * bboxRadius / self._islandWidth) + 1

        # Construct a square which wraps the radius
        hatchOrder = 0
        coords = []

        for i in np.arange(0, numIslands):
            for j in np.arange(0, numIslands):

                startX = -bboxRadius + i * \
                    (self._islandWidth) - self._islandOverlap
                endX = startX + (self._islandWidth) + self._islandOverlap

                startY = -bboxRadius + j * \
                    (self._islandWidth) - self._islandOverlap
                endY = startY + (self._islandWidth) + self._islandOverlap

                if np.mod(i + j, 2):
                    y = np.tile(np.arange(startY + np.mod(i + j, 2) * self._islandOffset * hatchSpacing,
                                          endY +
                                          np.mod(i + j, 2) * self._islandOffset *
                                          hatchSpacing, hatchSpacing,
                                          dtype=np.float32).reshape(-1, 1), (2)).flatten()

                    x = np.array([startX, endX])
                    x = np.resize(x, y.shape)
                    z = np.arange(hatchOrder, hatchOrder +
                                  y.shape[0] / 2, 0.5).astype(np.int64)

                else:
                    x = np.tile(np.arange(startX + np.mod(i + j, 2) * self._islandOffset * hatchSpacing,
                                          endX +
                                          np.mod(i + j, 2) * self._islandOffset *
                                          hatchSpacing, hatchSpacing,
                                          dtype=np.float32).reshape(-1, 1), (2)).flatten()

                    y = np.array([startY, endY])
                    y = np.resize(y, x.shape)
                    z = np.arange(hatchOrder, hatchOrder +
                                  y.shape[0] / 2, 0.5).astype(np.int64)

                hatchOrder += x.shape[0] / 2

                coords += [np.hstack([x.reshape(-1, 1),
                                      y.reshape(-1, 1),
                                      z.reshape(-1, 1)])]

        coords = np.vstack(coords)

        # Create the rotation matrix
        c, s = np.cos(theta_h), np.sin(theta_h)
        R = np.array([(c, -s, 0),
                      (s, c, 0),
                      (0, 0, 1.0)])

        # Apply the rotation matrix and translate to bounding box centre
        coords = np.matmul(R, coords.T)
        coords = coords.T + np.hstack([bboxCentre, 0.0])

        return coords