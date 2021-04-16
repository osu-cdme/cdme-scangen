# Standard Library Imports
from typing import Optional

# Third-Party Imports
import numpy as np

# Local Imports
# ...have to make these absolute because the __name__ of this file is src.island.island for some reason
#   See here for details: https://stackoverflow.com/questions/14132789/relative-imports-for-the-billionth-time/14132912
from pyslm.hatching.hatching import Hatcher
from pyslm.geometry import Layer, LayerGeometry, ContourGeometry, HatchGeometry
from pyslm.hatching import hatching


class BasicIslandHatcherRandomOrder(Hatcher):
    """
    BasicIslandHatcher extends the standard :class:`Hatcher` and generates a set of islands of fixed size (:attr:`.islandWidth`)
    which covers a region. This has the effect of limiting the max length of the scan whilst by orientating the scan vectors orthogonal to each other
    mitigating any preferential distortion or curling in a single direction and any effects to micro-structure.

    This version of BasicIslandHatcher reorders the islands such that they are done in a random order on each layer rather than row-by-row, column-by-column, 
    as in the author's implementation.
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

        # Generate random order
        island_order = np.empty((numIslands ** 2, 2), dtype=int)
        idx = 0
        for i in np.arange(0, numIslands):
            for j in np.arange(0, numIslands):
                island_order[idx] = np.array([i, j])
                idx += 1
        np.random.shuffle(island_order)

        # Iterate through islands and gen hatches
        for island_coords in island_order:
            i, j = island_coords[0], island_coords[1]

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
