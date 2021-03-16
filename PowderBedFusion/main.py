import numpy as np
import networkx as nx
import trimesh

from abc import ABC
from typing import Any, List, Optional, Tuple

from shapely.geometry import Polygon

class DocumentObject(ABC):

    def __init__(self, name):
        self._name = name
        self._label = 'Document Object'
        self._attributes = []

    # Attributes are those links to other document objects or properties
    @property
    def attributes(self):
        return self._attributes

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, label):
        self._label = label

    @property
    def name(self):
        return self._name

        # Protected method for assigning the set of Feature Attributes performed in constructor

    def _setAttributes(self, attributes):
        self._attributes = attributes

    def setName(self, name):
        self._name = name


    def boundingBox(self):  # const
        raise NotImplementedError('Abstract  method should be implemented in derived class')


class Document:

    def __init__(self):
        print('Initialising the Document Graph')

        # Create a direct acyclic graph using NetworkX
        self._graph = nx.DiGraph()

    def addObject(self, obj):

        if not issubclass(type(obj), DocumentObject):
            raise ValueError('Feature {:s} is not a Document Object'.format(obj))

        self._graph.add_node(obj)

        for attr in obj.attributes:
            # Add the subfeatures if they do not already exist in the document graph
            if attr is None:
                continue

            self.addObject(attr)

            # Add the depency link between parent and it's child attributes
            self._graph.add_edge(attr, obj)

        # Update the document accordingly
        self.recalculateDocument()

    def getObjectsByType(self, objType):
        objs = []

        for node in list(self._graph):

            # Determine if the document object requires boundary layers in calculation
            if type(node) is objType:
                objs.append(node)

        return objs

    def recalculateDocument(self):

        for node in list(nx.dag.topological_sort(self._graph)):

            # Determine if the document object requires boundary layers in calculation
            if type(node).usesBoundaryLayers():

                for childNode in list(nx.dag.ancestors(self._graph, node)):
                    childNode.setRequiresBoundaryLayers()

    @property
    def head(self):
        graphList = list(nx.dag.topological_sort(self._graph))
        return graphList[-1]

    @property
    def parts(self):

        objs = list(self._graph)
        parts = []

        for obj in objs:
            if issubclass(type(obj), Part):
                parts.append(obj)

        return parts

    @property
    def extents(self):
        # Method for calculating the total bounding box size of the document
        bbox = self.boundingBox
        return np.array([bbox[3] - bbox[0],
                         bbox[4] - bbox[1],
                         bbox[5] - bbox[2]])

    @property
    def partExtents(self):
        bbox = self.partBoundingBox
        return np.array([bbox[3] - bbox[0],
                         bbox[4] - bbox[1],
                         bbox[5] - bbox[2]])

    def getDependencyList(self):
        return list(nx.dag.topological_sort(self._graph))

    @property
    def partBoundingBox(self):
        """
        An (nx6) array containing the bounding box for all the parts. This is needed for calculating the grid
        """
        pbbox = np.vstack([part.boundingBox for part in self.parts])
        return np.hstack([np.min(pbbox[:, :3], axis=0), np.max(pbbox[:, 3:], axis=0)])

    @property
    def boundingBox(self):

        graphList = list(nx.dag.topological_sort(self._graph))
        graphList.reverse()
        return graphList[0].boundingBox

    def drawNetworkGraph(self):
        import networkx.drawing
        nodeLabels = [i.name for i in self._graph]
        networkLabels = dict(zip(self._graph, nodeLabels))
        networkx.drawing.draw(self._graph, labels=networkLabels)
    # networkx.drawing.draw_graphviz(self._graph, labels=networkLabels)


class Part(DocumentObject):
    """
    Part is a solid geometry within the document object tree. Currently this part is individually as part but will
    be sliced as part of a document tree structure.

    The part can be transformed and has a position (:attr:`~Part.origin`),
    rotation (:attr:`~Part.rotation`)  and additional scale factor (:attr:`~Part.scaleFactor`), which are collectively
    applied to the geometry in its local coordinate system :math:`(x,y,z)`. Changing the geometry using
    :meth:`~Part.setGeometryByMesh` or :meth:`~Part.setGeometry` along with any of the transformation attributes will set
    the part dirty and forcing the transformation and geometry to be re-computed on the next call in order to obtain
    the :attr:`Part.geometry`.

    Generally for AM and 3D printing the following function :meth:`~Part.getVectorSlice` is the most useful. This method
    provides the user with a slice for a given z-plane containing the boundaries consisting of a series of polygons.
    The output from this function is either a list of closed paths (coordinates) or a list of
    :class:`shapely.geometry.Polygon`. A bitmap slice can alternatively be obtained for certain AM process using
    :meth:`~Part.getBitmapSlice` in similar manner.
    """

    def __init__(self, name):

        super().__init__(name)

        self._geometry = None
        self._geometryCache = None

        self._bbox = np.zeros((1, 6))

        self._partType = 'Undefined'

        self._rotation = np.array((0.0, 0.0, 0.0))
        self._scaleFactor = np.array((1.0, 1.0, 1.0))
        self._origin = np.array((0.0, 0.0, 0.0))
        self._dirty = True

    def __str__(self):
        return 'Part <{:s}>'.format(self.name)

    def isDirty(self) -> bool:
        """
        When a transformation or the geometry object has been changed via methods in the part,
        the state is toggled dirty and the transformation matrix must be re-applied to generate a new internal
        representation of the geometry , which is then cached for future use.

        :return: The current state of the geometry
        """

        return self._dirty

    @property
    def rotation(self) -> np.ndarray:
        """ The part rotation is a 1x3 array representing the rotations :math:`(\\alpha, \\beta, \\gamma)`
        in degrees about X, Y, Z, applied sequentially in that order. """
        return self._rotation

    @rotation.setter
    def rotation(self, rotation: Any):

        rotation = np.asanyarray(rotation)

        if len(rotation) != 3:
            raise ValueError('Rotation value should be 1x3 Numpy array')

        self._rotation = rotation
        self._dirty = True

    @property
    def origin(self) -> np.ndarray:
        """ The origin or the translation of the part"""
        return self._origin

    @origin.setter
    def origin(self, origin: Any):

        origin = np.asanyarray(origin)

        if len(origin) != 3:
            raise ValueError('Origin value should be 1x3 Numpy array')

        self._origin = origin
        self._dirty = True

    @property
    def scaleFactor(self) -> np.ndarray:
        """
        The scale factor is a 1x3 matrix :math:`(s_x, s_y, s_z)` representing the scale factor of the part
        """
        return self._scaleFactor

    @scaleFactor.setter
    def scaleFactor(self, sf: Any):

        self._scaleFactor = np.asanyarray(sf).flatten()

        if len(self._scaleFactor) == 1:
            self._scaleFactor = self._scaleFactor * np.ones([3,])

        self._dirty = True

    def dropToPlatform(self, zPos: Optional[float] = 0.0) -> None:
        """
        Drops the part at a set height (parameter zPos) from its lowest point from the platform (assumed :math:`z=0`).

        :param zPos: The position the bottom of the part should be suspended above :math:`z=0`
        """

        self.origin[2] = -1.0* self.boundingBox[2] + zPos
        self._dirty = True

    def getTransform(self) -> np.ndarray:
        """
        Returns the transformation matrix (3x3 numpy matrix) used for the :class:`Part` consisting of a translation
        (:attr:`~Part.origin`), a :attr:`~Part.rotation` and a :attr:`~Part.scaleFactor`
        """

        Sx = trimesh.transformations.scale_matrix(factor = self._scaleFactor[0], direction=[1,0,0])
        Sy = trimesh.transformations.scale_matrix(factor=self._scaleFactor[1] , direction=[0,1,0])
        Sz = trimesh.transformations.scale_matrix(factor=self._scaleFactor[2], direction=[0,0,1])
        S = Sx*Sy*Sz
        T = trimesh.transformations.translation_matrix(self._origin)

        alpha, beta, gamma = np.deg2rad((self._rotation))

        R_e = trimesh.transformations.euler_matrix(alpha, beta, gamma, 'rxyz')

        M = trimesh.transformations.concatenate_matrices(T, R_e, S)

        return M

    def setGeometry(self, filename: str) -> None:
        """
        Sets the Part geometry based on a mesh filename.The mes must have a compatible file that can be
        imported via `trimesh`.

        :param filename: The mesh filename
        """
        self._geometry = trimesh.load_mesh(filename, use_embree=False, process=True, Validate_faces=False)

        print('Geometry information <{:s}> - [{:s}]'.format(self.name, filename))
        print('\t bounds', self._geometry.bounds)
        print('\t extent', self._geometry.extents)

        self._dirty = True

    def setGeometryByMesh(self, mesh: trimesh.Trimesh) -> None:
        """
         Sets the Part geometry based on an existing Trimesh object.

         :param mesh: The trimesh object loaded
         """
        self._geometry = mesh
        self._dirty = True

    @property
    def geometry(self) -> trimesh.Trimesh:
        """
        The geometry of the part with all transformations applied.
        """
        if not self._geometry:
            return None

        if self.isDirty():
            print('Updating {:s} Geometry Representation'.format(self.label))
            self._geometryCache = self._geometry.copy()
            self._geometryCache.apply_transform(self.getTransform())
            self._dirty = False

        return self._geometryCache

    @property
    def boundingBox(self) -> np.ndarray:  # const
        """
        The bounding box of the geometry transformed in the global coordinate frame :math:`(X,Y,Z). The bounding
        box is a 1x6 array consisting of the minimum coordinates followed by the maximum coordinates for the corners of
        the bounding box.
        """

        if not self.geometry:
            raise ValueError('Geometry was not set')
        else:
            return  self.geometry.bounds.flatten()

    @property
    def partType(self) -> str:
        """
        Returns the part type

        :return: The part type
        """

        return self._partType

    def getVectorSlice(self, z: float, returnCoordPaths: bool = True,
                       simplificationFactor = None, simplificationPreserveTopology: Optional[bool] = True) -> Any:
        """
        The vector slice is created by using `trimesh` to slice the mesh into a polygon

        :param returnCoordPaths: If True returns a list of closed paths representing the polygon, otherwise Shapely Polygons
        :param z: The slice's z-position
        :return: The vector slice at the given z level

        """
        if not self.geometry:
            raise ValueError('Geometry was not set')

        if z < self.boundingBox[2] or z > self.boundingBox[5]:
            return []

        transformMat = np.array(([1.0, 0.0, 0.0, 0.0],
                                 [0.0, 1.0, 0.0, 0.0],
                                 [0.0, 0.0, 1.0, 0.0],
                                 [0.0, 0.0, 0.0, 1.0]), dtype=np.float32)

        # Obtain the section through the STL polygon using Trimesh Algorithm (Shapely)
        sections = self.geometry.section(plane_origin=[0, 0, z],
                                         plane_normal=[0, 0, 1])

        if sections == None:
            return []

        # Obtain the 2D Planar Section at this Z-position
        planarSection, transform = sections.to_planar(transformMat)

        if not planarSection.is_closed:
            # Needed in case there are any holes in the stl mesh
            # Repairs the polygon boundary using a merge function built into Trimesh
            planarSection.fill_gaps(planarSection.scale / 100)

        # Obtain a closed list of shapely polygons
        polygons = planarSection.polygons_full

        if simplificationFactor:
            simpPolys = []

            for polygon in  polygons:
                simpPolys.append(polygon.simplify(simplificationFactor, preserve_topology=simplificationPreserveTopology))

            polygons = simpPolys

        if returnCoordPaths:
            return self.path2DToPathList(polygons)
        else:
            return polygons

    def path2DToPathList(self, shapes: List[Polygon]) -> List[np.ndarray]:
        """
        Returns the list of paths and coordinates from a cross-section (i.e. Trimesh Path2D). This is required to be
        done for performing boolean operations and offsetting with the PyClipper package

        :param shapes: A list of :class:`shapely.geometry.Polygon` representing a cross-section or container of
                        closed polygons
        :return: A list of paths (Numpy Coordinate Arrays) describing fully closed and oriented paths.
        """
        paths = []

        for poly in shapes:
            coords = np.array(poly.exterior.coords)
            paths.append(coords)

            for path in poly.interiors:
                coords = np.array(path.coords)
                paths.append(coords)

        return paths

    