import bpy
from mathutils import Matrix, Vector
from typing import OrderedDict, Union

from ...sollumz_converter import CWXMLConverter
from ...cwxml import fragment as yftxml
from ...cwxml.drawable import GeometryItem
from ...sollumz_properties import LODLevel
from ...tools.blenderhelper import get_parent_bone
from ...tools.utils import get_list_item
from ...ydr.import_cwxml.drawable import DrawableCWXMLConverter, SkeletonCWXMLConverter
from ...ydr.import_cwxml.light import LightCWXMLConverter
from .physicslod import PhysicsLodCWXMLConverter
from .window import WindowCWXMLConverter


class FragmentCWXMLConverter(CWXMLConverter[yftxml.Fragment]):
    """Converts Fragment CWXML objects to bpy objects."""
    IMPORT_CWXML_FUNC = yftxml.Fragment.from_xml_file

    def __init__(self, cwxml: yftxml.Fragment):
        super().__init__(cwxml)
        self.materials: list[bpy.types.Material] = []
        self.grouped_geometries: dict[str, GeometryItem] = {}

    def create_bpy_object(self, name: str) -> bpy.types.Object:
        name = self.cwxml.name or name

        skeleton_converter = SkeletonCWXMLConverter(
            cwxml=self.cwxml.drawable.skeleton)
        self.bpy_object = skeleton_converter.create_bpy_object(
            name, self.cwxml.drawable.joints.rotation_limits)

        self.set_fragment_properties()
        self.create_materials()
        self.get_grouped_geometries()

        # if self.cwxml.lights:
        #     LightCWXMLConverter(
        #         self.cwxml.lights).create_bpy_object(self.bpy_object, self.drawable)

        for index, lod_cwxml in enumerate(self.cwxml.physics.get_populated_lods()):
            groups = self.create_physics_lod(lod_cwxml, index)
            self.create_vehicle_windows(groups)

        # if self.cwxml.bones_transforms:
        #     self.apply_bones_transforms()

        return self.bpy_object

    def set_fragment_properties(self):
        """Set fragment properties based on the cwxml"""
        fragment = self.bpy_object
        fragment_cwxml = self.cwxml

        fragment.fragment_properties.unk_b0 = fragment_cwxml.unknown_b0
        fragment.fragment_properties.unk_b8 = fragment_cwxml.unknown_b8
        fragment.fragment_properties.unk_bc = fragment_cwxml.unknown_bc
        fragment.fragment_properties.unk_c0 = fragment_cwxml.unknown_c0
        fragment.fragment_properties.unk_c4 = fragment_cwxml.unknown_c4
        fragment.fragment_properties.unk_cc = fragment_cwxml.unknown_cc
        fragment.fragment_properties.gravity_factor = fragment_cwxml.gravity_factor
        fragment.fragment_properties.buoyancy_factor = fragment_cwxml.buoyancy_factor

    def create_materials(self):
        """Create all materials for this Fragment."""
        self.materials = DrawableCWXMLConverter(
            self.cwxml.drawable).create_materials()

    def get_grouped_geometries(self):
        """Get geometries mapped by group."""
        # Map by lod level
        # lod_level: group_name: shader_index: GeometryItem
        grouped_geometries: dict[LODLevel, dict[str, dict[int, GeometryItem]]] = {
            lod_level.value: {} for lod_level in LODLevel}
        all_vertices, all_indices = self.get_all_vertices_indices()
        bones = self.cwxml.drawable.skeleton.bones

        def get_vertex_group_name(vertex):
            """Get name of vertex group that the vertex belongs to."""
            # If all blendindices are 0, then this vertex is in the root bone group.
            if tuple(vertex.blendindices) == (0, 0, 0, 0):
                return bones[0].name

            bone_names = []
            for i in vertex.blendindices:
                bone_name = bones[i].name

                if bone_name in bone_names or i == 0:
                    continue

                bone_names.append(bone_name)

            # Could possibly be in multiple groups. if that's the case,
            # the names will be joined with a comma.
            return ", ".join(bone_names)

        for lod_level, shader_groups in all_indices.items():
            for shader_index, vert_indices in shader_groups.items():
                lod_group = grouped_geometries[lod_level]
                # Map vertex indices to group vertex indices
                # lod_level: group_name: shader_index: indices
                index_map: dict[str, dict[int, int]] = {}
                for i in vert_indices:
                    vertex = all_vertices[lod_level][shader_index][i]

                    if not hasattr(vertex, "blendindices"):
                        continue

                    group_name = get_vertex_group_name(vertex)

                    if group_name not in index_map:
                        index_map[group_name] = {}

                    if shader_index not in index_map[group_name]:
                        index_map[group_name][shader_index] = {}

                    if group_name not in lod_group:
                        lod_group[group_name] = {}

                    if shader_index not in lod_group[group_name]:
                        lod_group[group_name][shader_index] = GeometryItem()
                        lod_group[group_name][shader_index].shader_index = shader_index

                    group_index_map = index_map[group_name][shader_index]
                    group_geom = lod_group[group_name][shader_index]
                    group_vertices = group_geom.vertex_buffer.data
                    group_indices = group_geom.index_buffer.data

                    if i not in group_index_map:
                        group_vertices.append(vertex)

                        new_vertex_index = len(group_vertices) - 1
                        group_index_map[i] = new_vertex_index

                    group_indices.append(group_index_map[i])

        self.grouped_geometries = grouped_geometries
        print(grouped_geometries[LODLevel.HIGH].keys())

        return grouped_geometries

    def get_all_vertices_indices(self):
        """Get combined vertices and indices for each lod level"""
        all_vertices = {lod_level.value: {} for lod_level in LODLevel}
        all_indices = {lod_level.value: {} for lod_level in LODLevel}

        for models_group, lod_level in zip(self.cwxml.drawable.drawable_model_groups, list(LODLevel)):
            for model in models_group:
                for i, geometry in enumerate(model.geometries):
                    vertex_data = geometry.vertex_buffer.get_data()
                    index_data = geometry.index_buffer.data
                    shader_index = geometry.shader_index

                    if shader_index not in all_vertices[lod_level]:
                        all_vertices[lod_level][shader_index] = []

                    if shader_index not in all_indices[lod_level]:
                        all_indices[lod_level][shader_index] = []

                    if i > 0:
                        index_data = [
                            vert_index + len(all_vertices[lod_level][shader_index]) for vert_index in index_data]

                    all_vertices[lod_level][shader_index].extend(vertex_data)
                    all_indices[lod_level][shader_index].extend(index_data)

        return all_vertices, all_indices

    def create_physics_lod(self, lod_cwxml: yftxml.LODProperty, index: int) -> list[bpy.types.Object]:
        """Create a physics lod object based on the lod cwxml. Returns a list of the LOD's physics groups."""
        physics_converter = PhysicsLodCWXMLConverter(
            lod_cwxml, self.materials, self.grouped_geometries, self.cwxml.drawable.skeleton.bones)
        physics_group = physics_converter.create_bpy_object(index)
        physics_group.parent = self.bpy_object

        return physics_converter.groups

    def create_vehicle_windows(self, groups: list[bpy.types.Object]):
        """Create vehicle class windows given a list of lod groups."""
        window_cwxml: yftxml.WindowItem

        for window_cwxml in self.cwxml.vehicle_glass_windows:
            window_group = get_list_item(
                groups, window_cwxml.item_id)

            if window_group is not None:
                group_name = window_group.name.replace("_group", "")

                window = WindowCWXMLConverter(
                    window_cwxml, group_name, self.materials).create_bpy_object()

                window.parent = window_group

    def apply_bones_transforms(self):
        """Apply the bones transforms defined in this fragment."""
        transforms = [prop.value for prop in self.cwxml.bones_transforms]

        child: bpy.types.Object
        for child in self.bpy_object.children:
            parent_bone = get_parent_bone(child)

            if parent_bone is None:
                return

            bone_index = parent_bone.bone_properties.tag

            child.matrix_basis = transforms[bone_index] if bone_index < len(
                transforms) else Matrix()
