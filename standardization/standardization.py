"""
Vector Standardization
=====

Provides:
1. Splitting vectors above a certain length via `split_long_vectors()`
2. "Extending" vectors below a certain length by adding jump vectors via `extend_short_vectors()`

Relies on the following third-party libraries:
1. `numpy` for faster array operations
2. `numba` for just-in-time compilation

Notes:
- Functions have docstrings autoconfigured to work with Sphinx. That is not currently set up, but you should be able to set it up to automatically generate documentation formatted identically to https://pyslm.readthedocs.io/en/latest/index.html using the docstrings found here.
"""

# Standard Library Imports
import math
from copy import deepcopy

# Third-Party Imports
import numpy as np
from nptyping import NDArray
from numba import njit
import timeit

# Local Imports
from defs import Vertex, Segment, BoundingBox


@njit
def split_long_vectors(segment_list: NDArray[Segment], cutoff: int) -> NDArray[Segment]:
    """Splits a given list of segments such that no post-split segment is longer than `cutoff`.

    :param segment_list: A list of segments that should be split.
    :type segment_list: NDArray[class:`Segment`]
    :param cutoff: The maximum length that a given vector can be.
    :type cutoff: int
    :return: Returns the vector list split by `cutoff` length.
    :rtype: np.array[class:`Segment`]
    """

    # We know we will have at least as many segments as were passed in, so we preallocate to that
    output = np.empty(len(segment_list))
    for segment in segment_list:
        output.put(split_vector(segment, cutoff))
    return output


@njit
def split_vector(segment: Segment, cutoff: int) -> NDArray[Segment]:
    """Splits a given segment into segments such that each individual segment is no longer than `cutoff`.

    Note: With `cutoff` = 1mm, will split a 5.14mm vector into 1-1-1-1-1-.14 rather than dividing it equally.

    :param segment: The segment to split.
    :type segment: class:`Segment`
    :param cutoff: The maximum length that subsegments should be.
    :type cutoff: int
    :return: Returns the given vector split by `cutoff` length.
    :rtype: np.array[class:`Segment`]
    """

    # Segment is short enough to not need split
    if segment.length <= cutoff:
        return [segment]

    # Iterate along the segment by distance
    output = np.array()
    segments_away = 1
    start_point = Vertex(segment.v1)
    end_point = get_scaled_point(
        segment, cutoff * segments_away // segment.length)
    while math.dist(end_point, segment.v1) <= segment.length + .0000001:
        output.put(Segment(start_point, end_point))
        segments_away += 1
        start_point = deepcopy(end_point)
        end_point = get_scaled_point(
            segment, (cutoff * segments_away) // segment.length)
    return output


@njit
def get_scaled_point(segment: Segment, fraction: float) -> Vertex:
    """Takes the provided segment and returns the subsegment starting at the provided fraction along the part.

    TODO: Make sure the documentation of this function is accurate. It's confusing at best.

    :param segment: The starting vertex of the overall, full-length segment.
    :type segment: class:`Segment`
    :param fraction: The fraction along the overall segment that the end of this subsegment should be.
    :type fraction: float
    :return: The subset of the given vector.
    :rtype: Vertex
    """

    v = Vertex()

    # Scaled X
    v.x = segment.v1.x + fraction * \
        (segment.v2.x - segment.v1.x) if segment.v2.x > segment.v1.x else segment.v1.x - \
        fraction * (segment.v1.x - segment.v2.x)

    # Scaled Y
    v.y = segment.v1.y + fraction * \
        (segment.v2.y - segment.v1.y) if segment.v2.y > segment.v1.y else segment.v1.y - \
        fraction * (segment.v1.y - segment.v2.y)

    return v