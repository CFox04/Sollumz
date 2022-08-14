import bpy
from typing import Union

from ...sollumz_converter import CWXMLConverter
from ...cwxml import fragment as yftxml
from ...cwxml import drawable as ydrxml
from ...sollumz_properties import LODLevel, SollumType
from ...tools.blenderhelper import create_sollumz_object, join_objects
from ...ydr.import_cwxml.geometry import GeometryCWXMLConverter


class PhysicsGroupCWXMLConverter(CWXMLConverter[yftxml.GroupItem]):
    """Converts fragment physics group cwxml to bpy object."""

    def __init__(self, cwxml: yftxml.LODProperty, materials: list[bpy.types.Material], geometries: dict[LODLevel, Union[ydrxml.GeometryItem, None]]):
        super().__init__(cwxml)
        self.materials: list[bpy.types.Material] = materials
        self.geometries = geometries

    def create_bpy_object(self) -> bpy.types.Object:
        if self.geometries is not None:
            self.create_object_from_geometry()

        if self.bpy_object is None:
            self.bpy_object = create_sollumz_object(
                SollumType.FRAGGROUP, name=self.cwxml.name)

        self.set_physics_group_properties()

        return self.bpy_object

    def create_object_from_geometry(self):
        """Create group object from a geometry cwxml"""
        if self.geometries is None:
            return

        geometries = self.geometries[LODLevel.HIGH]

        if not geometries:
            return

        self.bpy_object = PhysicsGroupCWXMLConverter.create_and_join_geometries(
            geometries, self.materials, self.cwxml.name)
        self.bpy_object.sollum_type = SollumType.FRAGGROUP

    def set_physics_group_properties(self):
        """Set properties of physics group object based on the provided cwxml."""
        group = self.bpy_object
        group_cwxml = self.cwxml

        group.group_properties.name = group_cwxml.name
        group.group_properties.glass_window_index = group_cwxml.glass_window_index
        group.group_properties.glass_flags = group_cwxml.glass_flags
        group.group_properties.strength = group_cwxml.strength
        group.group_properties.force_transmission_scale_up = group_cwxml.force_transmission_scale_up
        group.group_properties.force_transmission_scale_down = group_cwxml.force_transmission_scale_down
        group.group_properties.joint_stiffness = group_cwxml.joint_stiffness
        group.group_properties.min_soft_angle_1 = group_cwxml.min_soft_angle_1
        group.group_properties.max_soft_angle_1 = group_cwxml.max_soft_angle_1
        group.group_properties.max_soft_angle_2 = group_cwxml.max_soft_angle_2
        group.group_properties.max_soft_angle_3 = group_cwxml.max_soft_angle_3
        group.group_properties.rotation_speed = group_cwxml.rotation_speed
        group.group_properties.rotation_strength = group_cwxml.rotation_strength
        group.group_properties.restoring_max_torque = group_cwxml.restoring_max_torque
        group.group_properties.latch_strength = group_cwxml.latch_strength
        group.group_properties.mass = group_cwxml.mass
        group.group_properties.min_damage_force = group_cwxml.min_damage_force
        group.group_properties.damage_health = group_cwxml.damage_health
        group.group_properties.unk_float_5c = group_cwxml.unk_float_5c
        group.group_properties.unk_float_60 = group_cwxml.unk_float_60
        group.group_properties.unk_float_64 = group_cwxml.unk_float_64
        group.group_properties.unk_float_68 = group_cwxml.unk_float_68
        group.group_properties.unk_float_6c = group_cwxml.unk_float_6c
        group.group_properties.unk_float_70 = group_cwxml.unk_float_70
        group.group_properties.unk_float_74 = group_cwxml.unk_float_74
        group.group_properties.unk_float_78 = group_cwxml.unk_float_78
        group.group_properties.unk_float_a8 = group_cwxml.unk_float_a8

    @staticmethod
    def create_and_join_geometries(geometries: list[ydrxml.GeometryItem], materials: list[bpy.types.Material], name: str):
        geometry_objs = []
        for geometry_cwxml in geometries:
            geometry_obj = GeometryCWXMLConverter(
                geometry_cwxml, materials).create_bpy_object(name)
            geometry_objs.append(geometry_obj)

        return join_objects(geometry_objs)
