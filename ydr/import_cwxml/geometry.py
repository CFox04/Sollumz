import bpy
from typing import Union

from ...cwxml.drawable import GeometryItem, BoneItem
from ...sollumz_converter import CWXMLConverter
from ...sollumz_properties import SollumType
from ...tools.meshhelper import create_uv_layer, create_vertexcolor_layer
from ...tools.blenderhelper import create_sollumz_object
from ..shader_materials import create_tinted_shader_graph


class GeometryCWXMLConverter(CWXMLConverter[GeometryItem]):
    """Converts geometry inside drawables to bpy objects."""

    def __init__(self, cwxml: GeometryItem, materials: list[bpy.types.Material]):
        super().__init__(cwxml)
        self.mesh: bpy.types.Mesh = None
        self.materials = materials
        self.vertex_components: GeometryItem.VertexComponents = {}

    def create_bpy_object(self, name: str, bones: Union[list[BoneItem], None] = None) -> bpy.types.Object:
        self.set_vertex_components()

        # Editing mesh data-block before assigning it to an object is a lot quicker for some reason
        mesh = self.create_mesh(name)

        geometry_object = create_sollumz_object(
            SollumType.DRAWABLE_GEOMETRY, mesh, name=name)
        self.bpy_object = geometry_object

        if bones is not None:
            self.create_vertex_groups(bones)
            self.set_geometry_weights()

        if self.materials:
            create_tinted_shader_graph(geometry_object)

        return geometry_object

    def set_vertex_components(self):
        """Get vertex components from cwxml and set self.vertex_components"""
        self.vertex_components = self.cwxml.get_vertex_components()

    def create_mesh(self, name: str) -> bpy.types.Mesh:
        """Create the mesh data-block for this geometry."""

        # Split indices into groups of 3
        indices = self.cwxml.index_buffer.data
        faces = [indices[i:i + 3] for i in range(0, len(indices), 3)]
        print(name, len(indices), len(self.cwxml.vertex_buffer.data))
        if name == "chassis":
            print(len(faces))

        mesh: bpy.types.Mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertex_components.positions, [], faces)
        mesh.validate()
        self.mesh = mesh

        self.create_material()
        self.set_smooth_normals()

        # self.create_uv_layers()
        # self.create_vertex_color_layers()

        return mesh

    def create_material(self):
        """Set material for this geometry based on the index of the shader on the drawable.
        Displays warning when not found."""
        if not self.materials:
            return

        shader_index = self.cwxml.shader_index
        if not 0 <= shader_index < len(self.materials):
            self.import_operator.report(
                {"WARNING"}, f"Material not set for {self.mesh}. Shader index of {shader_index} not found!")
            return

        self.mesh.materials.append(self.materials[shader_index])

    def set_smooth_normals(self):
        """Set the normals of this geometry and smooth them."""
        self.mesh.polygons.foreach_set(
            "use_smooth", [True] * len(self.mesh.polygons))
        self.mesh.normals_split_custom_set_from_vertices(
            self.vertex_components.normals)
        self.mesh.use_auto_smooth = True

    def create_uv_layers(self):
        """Create all uv layers for this geometry."""
        for i, (name, coords) in enumerate(self.vertex_components.uv_map.items()):
            create_uv_layer(self.mesh, i, name, coords)

    def create_vertex_color_layers(self):
        """Create all vertex color layers for this geometry."""
        for i, (name, coords) in enumerate(self.vertex_components.color_map.items()):
            create_vertexcolor_layer(self.mesh, i, name, coords)

    def create_vertex_groups(self, bones: list[BoneItem]):
        """Create vertex groups for this geometry based on the number
        of bones present in the drawable skeleton."""

        # Some drawables have weights defined, but no associated bones (just the bone indices).
        # This is common in mp clothing, where the weights are defined, but the bone
        # indices index the bones on the mp skeleton (which has to be acquired externally).
        # These weights will still be imported, but under the name "EXTERNAL_BONE". This will
        # allow the remaining bones to be acquired later if need be.
        bone_ids = self.cwxml.bone_ids
        bpy_vertex_groups = self.bpy_object.vertex_groups

        for bone_index in self.vertex_components.vertex_groups.keys():
            bone_name = "UNKNOWN_BONE"

            if bones and bone_index < len(bones):
                bone_name = bones[bone_index].name
            elif bone_ids and bone_index < len(bone_ids):
                bone_name = f"EXTERNAL_BONE.{bone_index}"

            bpy_vertex_groups.new(name=bone_name)

    def set_geometry_weights(self):
        """Set weights for this geometry."""
        for i, vertex_group in enumerate(self.vertex_components.vertex_groups.values()):
            for vertex_index, weight in vertex_group:
                self.bpy_object.vertex_groups[i].add(
                    [vertex_index], weight, "ADD")

    def create_armature_modifier(self, armature_object: bpy.types.Object):
        modifier = self.bpy_object.modifiers.new("Armature", "ARMATURE")
        modifier.object = armature_object
