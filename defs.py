import numpy as np
import math


class Vertex:

    def __init__(self, *args, **kwargs):

        # Zero-length constructor
        if not len(args):
            self.x = 0
            self.y = 0

        # Constructor that takes in a Vertex (essentially a deep copy)
        elif isinstance(args[0], Vertex):
            self.x = args[0].x
            self.y = args[0].y

        # x/y pair
        elif isinstance(args[0], int) and isinstance(args[1], int):
            self.x = args[0]
            self.y = args[1]

        else:
            raise Exception(
                "Invalid Vertex() constructor w/ arguments ({}, {})!".format(args[0], args[1]))

    def __str__(self):
        return "({},{})".format(self.x, self.y)


class Segment:
    def __init__(self, *args, **kwargs):

        # Zero-argument constructor
        if not len(args):
            self.v1 = Vertex()
            self.v2 = Vertex()

        # Two-Vertex Variant
        if isinstance(args[0], Vertex) and isinstance(args[1], Vertex):
            self.v1 = args[0]
            self.v2 = args[1]

        # Four-Coordinate Variant
        if isinstance(args[0], float) and isinstance(args[1], float) and isinstance(args[2], float) and isinstance(args[3], float):
            self.v1 = Vertex(args[0], args[1])
            self.v2 = Vertex(args[2], args[3])

        self.length = math.dist([v1.x, v1.y], [v2.x, v2.y])

    def __str__(self):
        return "<{}->{}>".format(self.v1, self.v2)


class BoundingBox:
    def __init__(self, tl: Vertex = Vertex(), tr: Vertex = Vertex(), bl: Vertex = Vertex(), br: Vertex = Vertex()):
        self.tl = tl
        self.tr = tr
        self.bl = bl
        self.br = br
        self.width = tl.x - tr.x
        self.height = tr.y - br.y

    def __str__(self):
        return "<tl={},tr={},bl={},br={}>".format(self.tl, self.tr, self.bl, self.br)
