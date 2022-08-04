import bpy

from ...sollumz_properties import SollumType
from ...sollumz_converter import BPYConverter
from ...cwxml.fragment import ChildrenItem
from ...tools.blenderhelper import find_first_child
from ...tools.utils import prop_array_to_vector
from ...ydr.ydrexport import drawable_from_object


class PhysicsChildBPYConverter(BPYConverter[ChildrenItem]):
    """Converts Fragment child objects to CWXML objects"""

    def create_cwxml(self, group_index: int, materials: list[bpy.types.Material]) -> ChildrenItem:
        self.cwxml = ChildrenItem()
        self.cwxml.group_index = group_index

        self.create_child_drawable(materials)
        self.set_physics_child_properties()

        return self.cwxml

    def create_child_drawable(self, materials):
        """Create drawable for this Fragment Child."""
        drawable = find_first_child(
            self.bpy_object, lambda child: child.sollum_type == SollumType.DRAWABLE)

        if drawable is not None:
            self.cwxml.drawable = drawable_from_object(
                self.export_operator, drawable, "", None, materials, True, False)
        else:
            self.cwxml.drawable.shader_group = None
            self.cwxml.drawable.skeleton = None
            self.cwxml.drawable.joints = None

    def set_physics_child_properties(self):
        """Set xml physics child properties based on the child_properties data-block."""
        child = self.bpy_object
        child_cwxml = self.cwxml

        child_cwxml.bone_tag = child.child_properties.bone_tag
        child_cwxml.pristine_mass = child.child_properties.pristine_mass
        child_cwxml.damaged_mass = child.child_properties.damaged_mass
        child_cwxml.unk_vec = prop_array_to_vector(
            child.child_properties.unk_vec)
        child_cwxml.inertia_tensor = prop_array_to_vector(
            child.child_properties.inertia_tensor, 4)
