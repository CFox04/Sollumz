import bpy
from mathutils import Matrix
from typing import Union

from ...sollumz_converter import CWXMLConverter
from ...cwxml import fragment as yftxml
from ...sollumz_properties import SollumType
from ...tools.blenderhelper import create_sollumz_object, get_parent_bone
from ...tools.utils import get_list_item
from ...ydr.import_cwxml.drawable import DrawableCWXMLConverter
from ...ydr.import_cwxml.light import LightCWXMLConverter
from .physicslod import PhysicsLodCWXMLConverter
from .window import WindowCWXMLConverter


class FragmentCWXMLConverter(CWXMLConverter[yftxml.Fragment]):
    """Converts Fragment CWXML objects to bpy objects."""
    IMPORT_CWXML_FUNC = yftxml.Fragment.from_xml_file

    def __init__(self, cwxml: yftxml.Fragment):
        super().__init__(cwxml)
        self.materials: list[bpy.types.Material] = []
        self.drawable: Union[bpy.types.Object, None] = None

    def create_bpy_object(self, name: str) -> bpy.types.Object:
        self.bpy_object = create_sollumz_object(
            SollumType.FRAGMENT, name=self.cwxml.name or name)

        self.set_fragment_properties()
        self.create_drawable()

        if self.cwxml.lights:
            LightCWXMLConverter(
                self.cwxml.lights).create_bpy_object(self.bpy_object, self.drawable)

        for index, lod_cwxml in enumerate(self.cwxml.physics.get_populated_lods()):
            groups = self.create_physics_lod(lod_cwxml, index)
            self.create_vehicle_windows(groups)

        if self.cwxml.bones_transforms:
            self.apply_bones_transforms()

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

    def create_drawable(self):
        """Create the drawable for this fragment."""
        drawable_cwxml = self.cwxml.drawable

        drawable_converter = DrawableCWXMLConverter(
            drawable_cwxml)
        drawable = drawable_converter.create_bpy_object(drawable_cwxml.name)
        drawable.matrix_basis = drawable_cwxml.matrix
        drawable.parent = self.bpy_object

        self.materials = drawable_converter.materials
        self.drawable = drawable

        return drawable

    def create_physics_lod(self, lod_cwxml: yftxml.LODProperty, index: int) -> list[bpy.types.Object]:
        """Create a physics lod object based on the lod cwxml. Returns a list of the LOD's physics groups."""
        physics_converter = PhysicsLodCWXMLConverter(lod_cwxml, self.materials)
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
        for child in self.drawable.children:
            parent_bone = get_parent_bone(child)

            if parent_bone is None:
                return

            bone_index = parent_bone.bone_properties.tag

            child.matrix_basis = transforms[bone_index] if bone_index < len(
                transforms) else Matrix()
