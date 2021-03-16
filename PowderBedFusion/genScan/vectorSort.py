import numpy as np
import networkx as nx

import abc

from .hatchingTools import *

class BaseSort(abc.ABC):
    def __init__(self):
        pass

    def __str__(self):
        return 'BaseSorter Feature'

    @abc.abstractmethod
    def sort(self, vectors: np.ndarray) -> np.ndarray:
        """
        Sorts the scan vectors in a particular order

        :param vectors: The un-sorted array of scan vectors
        :return: The sorted array of scan vectors
        """
        raise NotImplementedError('Sort method must be implemented')

class AlternateSort(BaseSort):
    """
    Sort method flips pairs of scan vectors so that their direction alternates across adjacent vectors.
    """
    def __init__(self):
        pass

    def __str__(self):
        return 'Alternating Hatch Sort'

    def sort(self, scanVectors: np.ndarray) -> np.ndarray:
        """ This approach simply flips the odd pair of hatches"""
        sv = to3DHatchArray(scanVectors)
        sv[1:-1:2] = np.flip(sv[1:-1:2], 1)

        #vectorCopy = scanVectors.copy()
        # return vectorCopy

        return from3DHatchArray(sv)


class LinearSort(BaseSort):
    """
    A linear sort approaches to sorting the scan vectors based on the current hatch angle specified in
    :attr:`pyslm.hatching.sorting.LinearSort.hatchAngle`. The approach takes the dot product of the hatch mid-point
    and the projection along the X-axis is sorted in ascending order (+ X direction).
    """

    def __init__(self):
        self._hatchAngle = 0.0

    @property
    def hatchAngle(self) -> float:
        """
        The hatch angle reference across the scan vectors to be sorted
        """
        return self._hatchAngle

    @hatchAngle.setter
    def hatchAngle(self, angle: float):
        self._hatchAngle = angle

    def sort(self, scanVectors: np.ndarray) -> np.ndarray:
        # requires an n x 2 x 2 array

        # Sort along the x-axis and obtain the indices of the sorted array

        theta_h = np.deg2rad(self._hatchAngle)

        # Find the unit vector normal based on the hatch angle
        norm = np.array([np.cos(theta_h), np.sin(theta_h)])

        midPoints = np.mean(scanVectors, axis=1)
        idx2 = norm.dot(midPoints.T)
        idx3 = np.argsort(idx2)

        sortIdx = np.arange(len(midPoints))[idx3]

        return scanVectors[sortIdx]