"""
Vector Standardization
=====

Provides:
1. Splitting vectors above a certain length via `split_long_vectors()`
2. "Extending" vectors below a certain length by adding jump vectors via `extend_short_vectors()`

Relies on the following third-party libraries:
1. `numpy` for faster array operations

Potential Optimizations:
1. Use the `numba` library, which allows you to JIT-compile some code.

Notes:
- Functions have docstrings autoconfigured to work with Sphinx. That is not currently set up, but you should be able to set it up to automatically generate documentation formatted identically to https://pyslm.readthedocs.io/en/latest/index.html using the docstrings found here.
"""

# Standard Library Imports
import math
from copy import deepcopy

# Third-Party Imports
import numpy as np
from nptyping import NDArray
import timeit

# Local Imports
from defs import Vertex, Segment, BoundingBox


def split_long_vectors(vertex_list: np.ndarray, cutoff: int) -> NDArray[Segment]:
    """Splits a given list of segments such that no post-split segment is longer than `cutoff`.

    :param segment_list: A list of segments that should be split.
    :type segment_list: NDArray[class:`Segment`]
    :param cutoff: The maximum length that a given vector can be.
    :type cutoff: int
    :return: Returns the vector list split by `cutoff` length.
    :rtype: np.array[class:`Segment`]
    """

    # Convert our input vertices to segments
    segment_list = np.empty(len(vertex_list) // 2, dtype=object)
    for i in np.arange(0, len(vertex_list), 2):
        segment_list[i // 2] = Segment(vertex_list[i, 0], vertex_list[i, 1],
                                       vertex_list[i+1, 0], vertex_list[i+1, 1])

    # We know we will have at least as many segments as were passed in, so we preallocate to that
    split_segments = np.empty(0, dtype=object)
    for i in range(len(segment_list)):
        split_segments = np.append(
            split_segments, split_vector(segment_list[i], cutoff))

    # Convert segments back into vertices
    output = np.empty((len(split_segments) * 2, 2), dtype=np.ndarray)
    for i in range(len(split_segments)):
        output[2 * i] = np.array([split_segments[i].v1.x,
                                 split_segments[i].v1.y])
        output[2 * i +
               1] = np.array([split_segments[i].v2.x, split_segments[i].v2.y])

    return output


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
    output = []
    segments_away = 1
    start_point = Vertex(segment.v1)
    end_point = get_scaled_point(
        segment, cutoff * segments_away // segment.length)
    while math.dist([end_point.x, end_point.y], [segment.v1.x, segment.v1.y]) <= segment.length + .0000001:
        output.append(Segment(start_point, end_point))
        segments_away += 1
        start_point = deepcopy(end_point)
        end_point = get_scaled_point(
            segment, (cutoff * segments_away) // segment.length)
    return np.array(output)


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
