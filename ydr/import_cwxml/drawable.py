import bpy

from ...sollumz_object import CWXMLConverter
from ...sollumz_properties import SollumType, LODLevel
from ...tools.blenderhelper import create_sollumz_object, get_children_recursive, join_objects, split_object_by_bones
from ...cwxml import drawable as ydrxml
from .geometry import GeometryCWXMLConverter
from .skeleton import SkeletonCWXMLConverter
from .light import LightCWXMLConverter
from .shader import ShaderCWXMLConverter


class DrawableCWXMLConverter(CWXMLConverter[ydrxml.Drawable]):
    """Converts Drawable CWXML objects to bpy objects."""
    IMPORT_CWXML_TYPE = ydrxml.Drawable

    @property
    def bones_cwxml(self) -> list[ydrxml.BoneItem]:
        """Bones of this drawable. Defaults to self.cwxml.skeleton.bones if none are provided."""
        if not self._bones_cwxml:
            return self.cwxml.skeleton.bones

        return self._bones_cwxml

    def __init__(self, cwxml: ydrxml.Drawable, external_bones: list[ydrxml.BoneItem] = None):
        super().__init__(cwxml)
        self.materials: list[bpy.types.Material] = []
        self._bones_cwxml: list[ydrxml.BoneItem] = external_bones or []

    def create_bpy_object(self, name: str) -> bpy.types.Object:
        if self.cwxml.has_skeleton():
            skeleton_converter = SkeletonCWXMLConverter(
                cwxml=self.cwxml.skeleton)

            self.bpy_object = skeleton_converter.create_bpy_object(
                name, self.cwxml.joints.rotation_limits)
        else:
            self.bpy_object = create_sollumz_object(SollumType.DRAWABLE)

        self.bpy_object.name = name
        self.set_drawable_lod_dist()
        self.create_all_drawable_models()

        for bound in self.cwxml.bounds:
            # BoundCWXMLConverter(cwxml=bound).create_bpy_object()
            pass

        for light in self.cwxml.lights:
            LightCWXMLConverter(
                light).create_bpy_object()

        if self.import_operator.import_settings.join_geometries:
            self.join_geometries()

        if self.cwxml.has_skeleton() and self.import_operator.import_settings.split_by_bone:
            self.split_geometries_by_vertex_group()

        return self.bpy_object

    def set_drawable_lod_dist(self):
        """Set the lod distance properties for this drawable to that of the drawable cwxml."""
        self.bpy_object.drawable_properties.lod_dist_high = self.cwxml.lod_dist_high
        self.bpy_object.drawable_properties.lod_dist_med = self.cwxml.lod_dist_med
        self.bpy_object.drawable_properties.lod_dist_low = self.cwxml.lod_dist_low
        self.bpy_object.drawable_properties.lod_dist_vlow = self.cwxml.lod_dist_vlow

    def create_all_drawable_models(self):
        """Create all drawable models and parent them to the drawable."""
        self.create_materials()

        for models_group, lod_level in zip(self.cwxml.drawable_model_groups, list(LODLevel)):
            for model_cwxml in models_group:
                model_object = self.create_drawable_model(
                    model_cwxml, lod_level)
                model_object.parent = self.bpy_object

    def create_materials(self):
        """Create all materials from this drawable's cwxml shader group."""
        for shader_cwxml in self.cwxml.shader_group.shaders:
            material = ShaderCWXMLConverter(
                shader_cwxml, self.filepath, self.cwxml.shader_group.texture_dictionary).create_bpy_object()
            self.materials.append(material)

    def create_drawable_model(self, model_cwxml: ydrxml.DrawableModelItem, lod_level: LODLevel):
        """Create a single drawable model given its cwxml."""
        model_object = create_sollumz_object(SollumType.DRAWABLE_MODEL)

        model_object.drawable_model_properties.sollum_lod = lod_level
        model_object.drawable_model_properties.render_mask = model_cwxml.render_mask
        model_object.drawable_model_properties.unknown_1 = model_cwxml.unknown_1
        model_object.drawable_model_properties.flags = model_cwxml.flags

        for geometry_cwxml in model_cwxml.geometries:
            # if self.import_operator.import_settings.split_by_bone:
            #     geometries = self.create_geometries_split_by_bone(
            #         geometry_cwxml)
            #     for geometry in geometries:
            #         geometry.parent = model_object
            # else:
            #     geometry = self.create_drawable_model_geometry(geometry_cwxml)
            #     geometry.parent = model_object
            geometry = self.create_drawable_model_geometry(geometry_cwxml)
            geometry.parent = model_object

        return model_object

    def create_drawable_model_geometry(self, geometry_cwxml: ydrxml.GeometryItem):
        """Create a geometry object for the given drawable model bpy object."""
        geometry_converter = GeometryCWXMLConverter(
            geometry_cwxml)

        geometry_converter.create_bpy_object(
            self.cwxml.name, self.bones_cwxml, self.materials)

        if self.cwxml.has_skeleton():
            geometry_converter.create_armature_modifier(self.bpy_object)

        return geometry_converter.bpy_object

    def create_geometries_split_by_bone(self, geometry_cwxml: ydrxml.GeometryItem):
        """Create a geometry object for the given drawable model bpy object."""
        geometry_converter = GeometryCWXMLConverter(
            geometry_cwxml)

        vertex_bone_map, index_bone_map = geometry_converter.get_vertices_indices_split_by_bone()

        geometries = []

        for bone_index, vertices in vertex_bone_map.items():
            geometry_converter.vertex_components = GeometryCWXMLConverter.get_vertex_components(
                vertices)
            geometry_converter.cwxml.index_buffer.data = index_bone_map[bone_index]
            bpy_object = geometry_converter.create_bpy_object(
                self.bones_cwxml[bone_index].name, self.bones_cwxml, self.materials)
            geometries.append(bpy_object)

        return geometries

    def join_geometries(self):
        """Join all geometries for this drawable."""
        for drawable_model in self.bpy_object.children:
            if drawable_model.sollum_type == SollumType.DRAWABLE_MODEL:
                geometries = [
                    child for child in drawable_model.children if child.sollum_type == SollumType.DRAWABLE_GEOMETRY]
                join_objects(geometries)

    def split_geometries_by_vertex_group(self):
        """Split all geometries by vertex group."""
        for geometry in get_children_recursive(self.bpy_object):
            if geometry.sollum_type == SollumType.DRAWABLE_GEOMETRY:
                split_object_by_bones(geometry, self.bpy_object.data)
