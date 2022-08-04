import bpy
from mathutils import Vector, Matrix

from ...sollumz_converter import BPYConverter
from ...cwxml.fragment import WindowItem
from ...tools.fragmenthelper import image_to_shattermap


class WindowBPYConverter(BPYConverter[WindowItem]):
    """Converts Fragment vehicle glass window objects to CWXML objects"""

    @property
    def shattermap_image(self) -> bpy.types.Image:
        """The image data-block of this window's shattermap material."""
        if self._shattermap_image is not None:
            return self._shattermap_image

        mat = self.bpy_object.data.materials[0]
        self._shattermap_image = mat.node_tree.nodes["ShatterMap"].image

        return self._shattermap_image

    def __init__(self, bpy_object: bpy.types.Object):
        super().__init__(bpy_object)
        self._shattermap_image = None

    def create_cwxml(self, group_index: int, materials: list[bpy.types.Material]) -> WindowItem:
        self.cwxml = WindowItem()
        self.cwxml.item_id = group_index

        self.cwxml.shattermap = image_to_shattermap(self.shattermap_image)

        self.set_window_properties()
        self.cwxml.unk_ushort_1 = materials.index(
            self.bpy_object.data.materials[1])

        self.calculate_projection_matrix()

        return self.cwxml

    def set_window_properties(self):
        """Set xml vehicle window properties based on the vehicle_window_properties data-block."""
        self.cwxml.unk_float_17 = self.bpy_object.vehicle_window_properties.unk_float_17
        self.cwxml.unk_float_18 = self.bpy_object.vehicle_window_properties.unk_float_18
        self.cwxml.cracks_texture_tiling = self.bpy_object.vehicle_window_properties.cracks_texture_tiling

    def calculate_projection_matrix(self):
        """Calculate projection matrix for this window based on its mesh data."""
        resx = self.shattermap_image.size[0]
        resy = self.shattermap_image.size[1]
        corners = WindowBPYConverter.get_corners(self.bpy_object.data)
        edges = WindowBPYConverter.create_edge_vectors(corners, resx, resy)

        self.cwxml.projection_matrix = WindowBPYConverter.create_projection_matrix(
            edges, corners[0])

    @staticmethod
    def get_corners(mesh: bpy.types.Mesh) -> list[Vector]:
        """
        Get the 3 corner vectors of the window mesh based on the uv coordinates.
        Returns ``[top_left, top_right, bottom_left]``
        """
        v1 = Vector()
        v2 = Vector()
        v3 = Vector()

        for loop in mesh.loops:
            vert_idx = loop.vertex_index
            uv = mesh.uv_layers[0].data[loop.index].uv
            if uv.x == 0 and uv.y == 1:
                v1 = mesh.vertices[vert_idx].co
            elif uv.x == 1 and uv.y == 1:
                v2 = mesh.vertices[vert_idx].co
            elif uv.x == 0 and uv.y == 0:
                v3 = mesh.vertices[vert_idx].co

        return v1, v2, v3

    @staticmethod
    def create_edge_vectors(corners: tuple[Vector, Vector, Vector], resx: float, resy: float):
        """Create 3 edge vectors from the corner vectors of the mesh."""
        THICKNESS = 0.01

        edge1: Vector = (corners[1] - corners[0]) / resx
        edge2: Vector = (corners[2] - corners[0]) / resy
        edge3: Vector = edge1.normalized().cross(edge2.normalized()) * THICKNESS

        return edge1, edge2, edge3

    @staticmethod
    def create_projection_matrix(edges: tuple[Vector, Vector, Vector], top_left: Vector):
        """Create projection matrix from the three edge vectors and the top_left corner vector."""
        matrix = Matrix()
        matrix[0] = edges[0].x, edges[1].x, edges[2].x, top_left.x
        matrix[1] = edges[0].y, edges[1].y, edges[2].y, top_left.y
        matrix[2] = edges[0].z, edges[1].z, edges[2].z, top_left.z
        matrix.invert()

        return matrix
