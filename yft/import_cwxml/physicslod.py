import bpy
from mathutils import Matrix, Vector
from typing import Union


from ...sollumz_converter import CWXMLConverter
from ...cwxml import fragment as yftxml
from ...sollumz_properties import SollumType
from ...tools.blenderhelper import create_sollumz_object
from ...tools.utils import get_list_item
from .physicsgroup import PhysicsGroupCWXMLConverter
from .physicschild import PhysicsChildCWXMLConverter


class PhysicsLodCWXMLConverter(CWXMLConverter[yftxml.LODProperty]):
    """Converts fragment physics lod cwxml to bpy object."""

    def __init__(self, cwxml: yftxml.LODProperty, materials: list[bpy.types.Material]):
        super().__init__(cwxml)
        self.groups: list[bpy.types.Object] = []
        self.materials: list[bpy.types.Material] = materials

    def create_bpy_object(self, lod_index: int) -> bpy.types.Object:
        if not self.cwxml.archetype.bounds:
            self.import_operator.report(
                {"WARNING"}, f"Failed to create {self.cwxml.tag_name}: Archetype is empty!")
            return

        self.bpy_object = create_sollumz_object(
            SollumType.FRAGLOD, name=self.cwxml.tag_name)

        self.set_lod_properties()

        for group_cwxml in self.cwxml.groups:
            self.create_and_parent_group(group_cwxml)

        for index, child_cwxml in enumerate(self.cwxml.children):
            self.create_and_parent_child(child_cwxml, index)

        self.bpy_object.lod_properties.type = lod_index + 1

        return self.bpy_object

    def set_lod_properties(self):
        """Set properties of lod object based on the lod cwxml."""
        lod = self.bpy_object
        lod_cwxml = self.cwxml

        lod.lod_properties.unknown_14 = lod_cwxml.unknown_14
        lod.lod_properties.unknown_18 = lod_cwxml.unknown_18
        lod.lod_properties.unknown_1c = lod_cwxml.unknown_1c
        lod.lod_properties.position_offset = lod_cwxml.position_offset
        lod.lod_properties.unknown_40 = lod_cwxml.unknown_40
        lod.lod_properties.unknown_40 = lod_cwxml.unknown_50
        lod.lod_properties.damping_linear_c = lod_cwxml.damping_linear_c
        lod.lod_properties.damping_linear_v = lod_cwxml.damping_linear_v
        lod.lod_properties.damping_linear_v2 = lod_cwxml.damping_linear_v2
        lod.lod_properties.damping_angular_c = lod_cwxml.damping_angular_c
        lod.lod_properties.damping_angular_v = lod_cwxml.damping_angular_v
        lod.lod_properties.damping_angular_v2 = lod_cwxml.damping_angular_v2
        # archetype properties
        lod.lod_properties.archetype_name = lod_cwxml.archetype.name
        lod.lod_properties.archetype_mass = lod_cwxml.archetype.mass
        lod.lod_properties.archetype_unknown_48 = lod_cwxml.archetype.unknown_48
        lod.lod_properties.archetype_unknown_4c = lod_cwxml.archetype.unknown_4c
        lod.lod_properties.archetype_unknown_50 = lod_cwxml.archetype.unknown_50
        lod.lod_properties.archetype_unknown_54 = lod_cwxml.archetype.unknown_54
        lod.lod_properties.archetype_inertia_tensor = lod_cwxml.archetype.inertia_tensor

    def create_and_parent_group(self, group_cwxml: yftxml.GroupItem):
        """Create a physics group for this LOD and parent it."""
        physics_group = PhysicsGroupCWXMLConverter(
            group_cwxml).create_bpy_object()

        physics_group.parent = self.get_physics_group_parent(group_cwxml)

        self.groups.append(physics_group)

    def get_physics_group_parent(self, group_cwxml: yftxml.GroupItem) -> Union[bpy.types.Object, None]:
        """Get the parent object of a physics group based on its parent index."""
        parent_index = group_cwxml.parent_index

        if parent_index == 255:
            return self.bpy_object

        parent = get_list_item(self.groups, parent_index)

        if parent is not None:
            return parent

        self.import_operator.report(
            {"WARNING"}, f"Failed to parent group '{group_cwxml.name}' to parent with index '{parent_index}': Index not found! Parenting to LOD...")

        return self.bpy_object

    def create_and_parent_child(self, child_cwxml: yftxml.ChildrenItem, index: int):
        """Create a physics child for this LOD and parent it."""
        group = get_list_item(self.groups, child_cwxml.group_index)

        if group is None:
            self.import_operator.report(
                {"WARNING"}, f"Failed to create physics child. Could not find fragment group with index {child_cwxml.group_index}!")
            return

        bounds_child = get_list_item(
            self.cwxml.archetype.bounds.children, index)

        physics_child = PhysicsChildCWXMLConverter(
            child_cwxml, group, self.materials).create_bpy_object(bounds_child, self.get_child_transform(index))

        physics_child.parent = group

    def get_child_transform(self, child_index: int):
        """Get transform matrix for child with the provided index."""
        transform_property = get_list_item(self.cwxml.transforms, child_index)

        if not transform_property:
            return Matrix()

        transform: Matrix = transform_property.value
        position_offset: Vector = self.cwxml.position_offset

        a = transform[3][0] + position_offset.x
        b = transform[3][1] + position_offset.y
        c = transform[3][2] + position_offset.z
        transform[3][0] = a
        transform[3][1] = b
        transform[3][2] = c

        return transform.transposed()
