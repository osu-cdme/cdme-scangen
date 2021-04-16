"""
Vector Lengthening
=================

Provides:

1. "Lengthening" vectors below a certain length (by adding a jump vector to the end of them) via `lengthen_short_vectors()`

Relies on the following third-party libraries:

1. `numpy` for faster array operations

Potential Optimizations:

1. Use the `numba` library, which allows you to JIT-compile some code.

Notes:
- Functions have docstrings autoconfigured to work with Sphinx. That is not currently set up, but you should be able to set it up to automatically generate documentation formatted identically to https://pyslm.readthedocs.io/en/latest/index.html using the docstrings found here.
"""

# Standard Library Imports
import math

# Third-Party Imports
import numpy as np
from nptyping import NDArray

# Local Imports
from .defs import Vertex, Segment, BoundingBox

def lengthen_short_vectors(vertex_list: np.ndarray, cutoff: int) -> NDArray[Segment]:
    """Lengthens all vectors in a provided list that are shorter than `cutoff` such that they
    have a jump vector added that brings their burn time approximately to `cutoff` distance.

    :param vertex_list: The input list of vertices
    :type vertex_list: np.ndarray
    :param cutoff: The length we should effectively increase all vectors to, if shorter
    :type cutoff: int
    :return: A list of Segments where the short ones have been lengthened 
    :rtype: np.array[class:`Segment`]
    """

    # Convert our input vertices to segments
    segment_list = np.empty(len(vertex_list) // 2, dtype=object)
    for i in np.arange(0, len(vertex_list), 2):
        segment_list[i // 2] = Segment(vertex_list[i, 0], vertex_list[i, 1],
                                       vertex_list[i+1, 0], vertex_list[i+1, 1])

    # We know we'll have no more than twice the amount of initial vertices (which occurs if we
    #   want to lengthen every vertex) so we preallocate to twice the size 
    curr_idx = 0
    lengthened_segments = np.empty(0, dtype=object)
    for i in range(len(segment_list)):

        # Add original vector regardless
        lengthened_segments = np.append(lengthened_segments, segment_list[i])   
        
        # If shorter than the cutoff, add another zero-length vector at its extrapolated distance
        if segment_list[i].length < cutoff:
            lengthened_segments = np.append(lengthened_segments, 
                extrapolate_vector(segment_list[i], cutoff)) 

    # Convert segments back into vertices 
    output = np.empty((len(lengthened_segments) * 2, 2), dtype=np.ndarray)
    for i in range(len(lengthened_segments)):
        output[2 * i] = np.array([lengthened_segments[i].v1.x,
                                 lengthened_segments[i].v1.y])
        output[2 * i +
               1] = np.array([lengthened_segments[i].v2.x, lengthened_segments[i].v2.y])

    return output 

# Returns a zero-length segment at the extrapolated full-length position of the provided segment
def extrapolate_vector(segment: Segment, cutoff: int) -> Segment:
    """For a given class:`Segment`, returns a zero-length Segment that is at the 
    extrapolated end position of the vector, should it have gone `cutoff` length.

    :param segment: The segment we want to extrapolate. Vertex order matters; it extends v1 to v2's direction.
    :type segment: np.ndarray
    :param cutoff: The length we should effectively increase the vector to 
    :type cutoff: int
    :return: A zero-length segment that is at the extrapolated end position of the vector, should it have gone `cutoff` length.
    :rtype: class:`Segment`
    """

    # Get angle between points and intended distance
    angle_rads = np.arctan2(segment.v2.y - segment.v1.y, segment.v2.x - segment.v1.x)
    x_offset = cutoff * np.cos(angle_rads)
    y_offset = cutoff * np.sin(angle_rads)

    # Populate and return zero-length segment at that point 
    v1 = Vertex(segment.v1.x + x_offset, segment.v1.y + y_offset)
    v2 = Vertex(segment.v1.x + x_offset, segment.v1.y + y_offset)
    return Segment(v1, v2)