import bpy
from mathutils import Vector

from ...sollumz_converter import CWXMLConverter
from ...cwxml import fragment as yftxml
from ...sollumz_properties import SollumType
from ...tools.blenderhelper import create_sollumz_object
from ...tools.utils import get_list_item, multiW
from ...tools.meshhelper import create_uv_layer
from ...tools.fragmenthelper import shattermap_to_material


class WindowCWXMLConverter(CWXMLConverter[yftxml.WindowItem]):
    """Convert fragment glass window to bpy object."""

    FACE_INDICES = [[0, 1, 2, 3]]
    UV_INDICES = [[0, 1], [0, 0], [1, 0], [1, 1]]

    def __init__(self, cwxml: yftxml.WindowItem, group_name: str, materials: list[bpy.types.Material]):
        super().__init__(cwxml)
        self.name = group_name + " vehicle window"
        self.materials = materials

    def create_bpy_object(self) -> bpy.types.Object:
        mesh = self.create_mesh()
        self.create_materials(mesh)

        self.bpy_object = create_sollumz_object(
            SollumType.FRAGVEHICLEWINDOW, mesh, name=self.name)

        self.set_window_properties()

        return self.bpy_object

    def create_mesh(self):
        """Create window mesh data-block."""
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.get_verts(), [], self.FACE_INDICES)
        create_uv_layer(mesh, 0, "UVMap", self.UV_INDICES, False)

        return mesh

    def create_materials(self, mesh: bpy.types.Material):
        """Create materials for the window mesh."""
        material = shattermap_to_material(
            self.cwxml.shattermap, self.name + " shattermap.bmp")
        mesh.materials.append(material)

        mat_index = self.cwxml.unk_ushort_1 - 1
        glass_material = get_list_item(self.materials, mat_index)

        if glass_material is None:
            self.report(
                {"WARNING"}, f"Could not find glass material for window '{self.name}': Index {mat_index} is not a shader index.")
            return

        mesh.materials.append(glass_material)

    def set_window_properties(self):
        """Set properties of this window based on its cwxml."""
        window = self.bpy_object
        window_cwxml = self.cwxml

        window.vehicle_window_properties.unk_float_17 = window_cwxml.unk_float_17
        window.vehicle_window_properties.unk_float_18 = window_cwxml.unk_float_18
        window.vehicle_window_properties.cracks_texture_tiling = window_cwxml.cracks_texture_tiling

    def get_verts(self):
        """Get the 4 verts that make up the window object."""
        matrix = self.get_matrix()

        min = Vector((0, 0, 0))
        max = Vector((self.cwxml.width / 2, self.cwxml.height, 1))

        v0 = multiW(matrix, Vector((min.x, min.y, 0)))
        v1 = multiW(matrix, Vector((min.x, max.y, 0)))
        v2 = multiW(matrix, Vector((max.x, max.y, 0)))
        v3 = multiW(matrix, Vector((max.x, min.y, 0)))

        return [v0, v1, v2, v3]

    def get_matrix(self):
        """Get transposed and inverted window projection matrix."""
        mat = self.cwxml.projection_matrix
        mat[3][3] = 1

        return mat.transposed().inverted()
