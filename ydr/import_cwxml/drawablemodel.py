import bpy
from typing import Union

from ...cwxml.drawable import DrawableModelItem, GeometryItem
from ...sollumz_converter import CWXMLConverter
from ...sollumz_properties import SollumType
from ...tools.blenderhelper import create_sollumz_object, join_objects
from ..ydrimport import geometry_to_obj_split_by_bone, create_lights
from ..shader_materials import create_tinted_shader_graph


class DrawableModelCWXMLConverter(CWXMLConverter[DrawableModelItem]):
    """Converts Drawable Model CWXML objects to bpy objects."""

    def __init__(self, cwxml: DrawableModelItem, materials: list[bpy.types.Material]):
        super().__init__(cwxml)
        self.vertex_components: dict[int, GeometryItem.VertexComponents] = {}
        self.mesh: Union[bpy.types.Mesh, None] = None
        self.materials = materials

    def create_bpy_object(self, name: str = None) -> bpy.types.Object:
        """Create a single drawable model given its cwxml."""
        self.get_vertex_components_by_material()

    def get_vertex_components_by_material(self):
        """Return map of vertex components by material"""
        vertex_components = {}

        for geometry_cwxml in self.cwxml.geometries:
            vertex_components[geometry_cwxml.shader_index] = geometry_cwxml.get_vertex_components(
            )

        return vertex_components
