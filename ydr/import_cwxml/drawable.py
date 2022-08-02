import bpy
from mathutils import Vector

from ...sollumz_object import CWXMLConverter
from ...sollumz_properties import SollumType, LODLevel, SOLLUMZ_UI_NAMES
from ...tools.blenderhelper import create_sollumz_object, join_objects
from ...cwxml import drawable as ydrxml
from ...ybn.ybnimport import composite_to_obj, bound_to_obj
from ..ydrimport import geometry_to_obj_split_by_bone, create_lights
from ..shader_materials import create_tinted_shader_graph
from .geometry import GeometryCWXMLConverter
from .skeleton import SkeletonCWXMLConverter
from .shader import ShaderCWXMLConverter


class DrawableCWXMLConverter(CWXMLConverter[ydrxml.Drawable]):
    """Converts Drawable CWXML objects to bpy objects."""
    IMPORT_CWXML_FUNC = ydrxml.Drawable.from_xml_file

    @property
    def bones_cwxml(self) -> list[ydrxml.BoneItem]:
        """Bones of this drawable. Defaults to self.cwxml.skeleton.bones if none are provided."""
        if not self._bones_cwxml:
            return self.cwxml.skeleton.bones

        return self._bones_cwxml

    def __init__(self, cwxml: ydrxml.Drawable, external_bones: list[ydrxml.BoneItem] = None):
        super().__init__(cwxml)
        self.materials: list[bpy.types.Material] = []
        self.uses_external_skeleton = external_bones is not None
        self._bones_cwxml: list[ydrxml.BoneItem] = external_bones or []

    def create_bpy_object(self, name: str) -> bpy.types.Object:
        if self.cwxml.has_skeleton():
            skeleton_converter = SkeletonCWXMLConverter(
                cwxml=self.cwxml.skeleton)

            self.bpy_object = skeleton_converter.create_bpy_object(
                name, self.cwxml.joints.rotation_limits)
        else:
            self.bpy_object = create_sollumz_object(
                SollumType.DRAWABLE, name=name)

        self.set_drawable_lod_dist()
        self.create_all_drawable_models()
        self.create_embedded_collisions()
        self.create_lights()

        if self.import_operator.import_settings.join_geometries:
            self.join_geometries()

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

                if self.cwxml.has_skeleton() and not self.uses_external_skeleton:
                    self.parent_drawable_model_bones(
                        model_object, model_cwxml.bone_index)

    def create_materials(self):
        """Create all materials from this drawable's cwxml shader group."""
        for shader_cwxml in self.cwxml.shader_group.shaders:
            material = ShaderCWXMLConverter(
                shader_cwxml, self.filepath, self.cwxml.shader_group.texture_dictionary).create_bpy_object()
            self.materials.append(material)

    def create_embedded_collisions(self):
        """Create all collisions defined in the drawable."""
        # TODO: Old code. Ybn import still needs rewrite.
        for bound in self.cwxml.bounds:
            bobj = None
            if bound.type == "Composite":
                bobj = composite_to_obj(
                    bound, SOLLUMZ_UI_NAMES[SollumType.BOUND_COMPOSITE], True)
                bobj.parent = self.bpy_object
            else:
                bobj = bound_to_obj(bound)
                if bobj:
                    bobj.parent = self.bpy_object

    def create_lights(self):
        """Create all lights for this drawable."""
        # TODO: Old code. Lights import needs rewrite.
        lights_cwxml = self.cwxml.lights
        if lights_cwxml:
            create_lights(lights_cwxml, self.bpy_object)

    def create_drawable_model(self, model_cwxml: ydrxml.DrawableModelItem, lod_level: LODLevel):
        """Create a single drawable model given its cwxml."""
        model_object = create_sollumz_object(SollumType.DRAWABLE_MODEL)

        model_object.drawable_model_properties.sollum_lod = lod_level
        model_object.drawable_model_properties.render_mask = model_cwxml.render_mask
        model_object.drawable_model_properties.unknown_1 = model_cwxml.unknown_1
        model_object.drawable_model_properties.flags = model_cwxml.flags

        import_settings = self.import_operator.import_settings
        if not import_settings.join_geometries and import_settings.split_by_bone and model_cwxml.has_skin == 1:
            # TODO: This is old code. Still need to implement split by bone in rewrite.
            child_objs = geometry_to_obj_split_by_bone(
                model_cwxml, self.materials, self.bones_cwxml)
            for child_obj in child_objs:
                child_obj.parent = model_object
                for mat in self.materials:
                    child_obj.data.materials.append(mat)
                create_tinted_shader_graph(child_obj)
        else:
            for geometry_cwxml in model_cwxml.geometries:
                geometry = self.create_drawable_model_geometry(geometry_cwxml)
                geometry.parent = model_object

        return model_object

    def parent_drawable_model_bones(self, model_object: bpy.types.Object, bone_index: int):
        """Set drawable model parent bone based on its bone index."""
        armature = self.bpy_object

        if armature.type != "ARMATURE":
            return

        parent_bone_name = None
        has_bone_translation = False

        if len(armature.pose.bones) > bone_index:
            parent_bone_name = armature.pose.bones[bone_index].name
            translation: Vector = self.bones_cwxml[bone_index].translation

            if translation is not None and translation.magnitude > 0:
                has_bone_translation = True

        if parent_bone_name is not None:
            # Preserve transforms after parenting
            original_world_mat = model_object.matrix_world.copy()

            model_object.parent_type = "BONE"
            model_object.parent_bone = parent_bone_name

            if has_bone_translation is False:
                model_object.matrix_world = original_world_mat

    def create_drawable_model_geometry(self, geometry_cwxml: ydrxml.GeometryItem):
        """Create a geometry object for the given drawable model bpy object."""
        geometry_converter = GeometryCWXMLConverter(
            geometry_cwxml)

        geometry_converter.create_bpy_object(
            self.cwxml.name, self.bones_cwxml, self.materials)

        if self.cwxml.has_skeleton():
            geometry_converter.create_armature_modifier(self.bpy_object)

        return geometry_converter.bpy_object

    def join_geometries(self):
        """Join all geometries for this drawable."""
        for drawable_model in self.bpy_object.children:
            if drawable_model.sollum_type == SollumType.DRAWABLE_MODEL:
                geometries = [
                    child for child in drawable_model.children if child.sollum_type == SollumType.DRAWABLE_GEOMETRY]
                join_objects(geometries)
