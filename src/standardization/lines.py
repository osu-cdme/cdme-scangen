from defs import Vertex, Segment, BoundingBox
import numpy

# Return: The intersection point if they intersect, None if they're parallel or colinear
# Algorithm is from some random StackOverflow post, but a similar one is outlined @ https://stackoverflow.com/a/60368757/6402548


def line_intersects_line(s1: Segment, s2: Segment) -> Vertex:
    """Calculates the intersection point of two segments.

    :param s1: The first segment.
    :type s1: Segment
    :param s2: The second segment.
    :type s2: Segment
    :return: If no intersection exists, None. If an intersection exists, the intersection point.
    :rtype: Vertex
    """
    def det(a, b, c, d):
        return a * d - b * c

    x1 = s1.v1.x, y1 = s1.v1.y
    x2 = s1.v2.x, y2 = s1.v2.y
    x3 = s2.v1.x, y3 = s2.v1.y
    x4 = s2.v2.x, y4 = s2.v2.y

    detL1 = det(x1, y1, x2, y2)
    detL2 = det(x3, y3, x4, y4)
    x1mx2 = x1 - x2
    x3mx4 = x3 - x4
    y1my2 = y1 - y2
    y3my4 = y3 - y4

    denom = det(x1mx2, y1my2, x3mx4, y3my4)
    if denom == 0.0:  # Lines don't seem to cross
        return None

    xnom = det(detL1, x1mx2, detL2, x3mx4)
    ynom = det(detL1, y1my2, detL2, y3my4)
    intersect = Vertex(xnom / denom, ynom / denom)
    if not numpy.isfinite(intersect.x) or not numpy.isfinite(intersect.y):
        return None
    return intersect
