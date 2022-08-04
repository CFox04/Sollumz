import bpy

from ...sollumz_properties import BOUND_TYPES, SollumType
from ...sollumz_converter import BPYConverter
from ...cwxml.fragment import LODProperty, TransformItem
from ...ybn.ybnexport import composite_from_objects
from ...sollumz_helper import get_children_with_sollum_type
from ...tools.utils import prop_array_to_vector, divide_vector_inv
from .physicsgroup import PhysicsGroupBPYConverter
from .physicschild import PhysicsChildBPYConverter


def get_group_index(physics_group: bpy.types.Object, physics_groups: list[bpy.types.Object], default=0):
    """Get the group index of a Fragment Group. If the Fragment Group cannot be found,
    the default value will be returned."""
    if physics_group.sollum_type != SollumType.FRAGGROUP or physics_group not in physics_groups:
        return default

    return physics_groups.index(physics_group)


class PhysicsLodBPYConverter(BPYConverter[LODProperty]):
    """Converts Fragment LOD objects to CWXML objects"""

    @property
    def physics_groups(self) -> list[bpy.types.Object]:
        """All Fragment Group objects under this LOD."""
        if self._physics_groups:
            return self._physics_groups

        self._physics_groups = get_children_with_sollum_type(
            self.bpy_object, [SollumType.FRAGGROUP])

        return self._physics_groups

    def __init__(self, bpy_object: bpy.types.Object, materials: list[bpy.types.Material]):
        super().__init__(bpy_object)
        # How could we avoid passing materials through PhysicsLOD then into PhysicsChild?
        self.materials = materials
        self._physics_groups = []

    def create_cwxml(self) -> LODProperty:
        self.cwxml = LODProperty()
        self.create_archetype_bounds()
        self.create_physics_groups()
        self.create_physics_children()
        self.set_lod_properties()
        self.set_lod_archetype_properties()

        return self.cwxml

    def create_archetype_bounds(self):
        """Create the bounds for this LOD's archetype."""
        frag_bounds = get_children_with_sollum_type(
            self.bpy_object, BOUND_TYPES)

        self.cwxml.archetype.bounds = composite_from_objects(
            frag_bounds, self.export_settings, True)

    def create_physics_groups(self):
        """Create all physics groups CWXML objects under this LOD."""
        for physics_group in self.physics_groups:
            parent_index = get_group_index(
                physics_group.parent, self.physics_groups, 255)

            self.cwxml.groups.append(
                PhysicsGroupBPYConverter(physics_group).create_cwxml(parent_index))

    def create_physics_children(self):
        """Create all physics children CWXML objects defined under this LOD."""
        physics_children = get_children_with_sollum_type(
            self.bpy_object, [SollumType.FRAGCHILD])

        for physics_child in physics_children:
            group_index = get_group_index(
                physics_child.parent, self.physics_groups)

            self.cwxml.children.append(
                PhysicsChildBPYConverter(physics_child).create_cwxml(group_index, self.materials))

            self.create_physics_child_transforms(physics_child)

    def create_physics_child_transforms(self, physics_child: bpy.types.Object):
        """Create the xml Transform matrix for the provided Fragment Child."""
        pos_offset = self.cwxml.position_offset

        transform = physics_child.matrix_basis.transposed()
        a = transform[3][0] - pos_offset.x
        b = transform[3][1] - pos_offset.y
        c = transform[3][2] - pos_offset.z
        transform[3][0] = a
        transform[3][1] = b
        transform[3][2] = c

        self.cwxml.transforms.append(TransformItem("Item", transform))

    def set_lod_properties(self):
        """Set xml LOD properties based on the lod_properties data-block."""
        lod = self.bpy_object
        lod_cwxml = self.cwxml

        lod_cwxml.unknown_14 = lod.lod_properties.unknown_14
        lod_cwxml.unknown_18 = lod.lod_properties.unknown_18
        lod_cwxml.unknown_1c = lod.lod_properties.unknown_1c
        pos_offset = prop_array_to_vector(lod.lod_properties.position_offset)
        lod_cwxml.position_offset = pos_offset
        lod_cwxml.unknown_40 = prop_array_to_vector(
            lod.lod_properties.unknown_40)
        lod_cwxml.unknown_50 = prop_array_to_vector(
            lod.lod_properties.unknown_50)
        lod_cwxml.damping_linear_c = prop_array_to_vector(
            lod.lod_properties.damping_linear_c)
        lod_cwxml.damping_linear_v = prop_array_to_vector(
            lod.lod_properties.damping_linear_v)
        lod_cwxml.damping_linear_v2 = prop_array_to_vector(
            lod.lod_properties.damping_linear_v2)
        lod_cwxml.damping_angular_c = prop_array_to_vector(
            lod.lod_properties.damping_angular_c)
        lod_cwxml.damping_angular_v = prop_array_to_vector(
            lod.lod_properties.damping_angular_v)
        lod_cwxml.damping_angular_v2 = prop_array_to_vector(
            lod.lod_properties.damping_angular_v2)

    def set_lod_archetype_properties(self):
        """Set xml LOD archetype properties based on the lod_properties data-block."""
        lod = self.bpy_object
        lod_cwxml = self.cwxml

        lod_cwxml.archetype.name = lod.lod_properties.archetype_name
        lod_cwxml.archetype.mass = lod.lod_properties.archetype_mass
        lod_cwxml.archetype.mass_inv = 1 / lod.lod_properties.archetype_mass
        lod_cwxml.archetype.unknown_48 = lod.lod_properties.archetype_unknown_48
        lod_cwxml.archetype.unknown_4c = lod.lod_properties.archetype_unknown_4c
        lod_cwxml.archetype.unknown_50 = lod.lod_properties.archetype_unknown_50
        lod_cwxml.archetype.unknown_54 = lod.lod_properties.archetype_unknown_54
        arch_it = prop_array_to_vector(
            lod.lod_properties.archetype_inertia_tensor)
        lod_cwxml.archetype.inertia_tensor = arch_it
        lod_cwxml.archetype.inertia_tensor_inv = divide_vector_inv(arch_it)
