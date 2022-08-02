import bpy
from mathutils import Matrix
from typing import Union

from ...sollumz_converter import CWXMLConverter
from ...sollumz_properties import SollumType
from ...cwxml import fragment as yftxml, bound as ybnxml
from ...tools.blenderhelper import create_sollumz_object
from ...ybn.ybnimport import bound_to_obj
from ...ydr.import_cwxml.drawable import DrawableCWXMLConverter


class PhysicsChildCWXMLConverter(CWXMLConverter[yftxml.ChildrenItem]):
    """Converts Fragment physics children CWXML objects to bpy objects."""

    def __init__(self, cwxml: yftxml.ChildrenItem, group: bpy.types.Object, materials: list[bpy.types.Material]):
        super().__init__(cwxml)
        self.group = group
        self.materials: list[bpy.types.Material] = materials

    def create_bpy_object(self, bound_cwxml: Union[ybnxml.BoundItem, None] = None, transform: Union[Matrix, None] = None) -> bpy.types.Object:
        name = self.group.name.replace("_group", "_child")

        self.bpy_object = create_sollumz_object(
            SollumType.FRAGCHILD, name=name)

        self.set_physics_child_properties()

        if bound_cwxml is not None:
            self.create_collisions(bound_cwxml)

        if self.cwxml.drawable.drawable_models_high:
            self.create_drawable()

        if transform is not None:
            self.bpy_object.matrix_basis = transform

        return self.bpy_object

    def set_physics_child_properties(self):
        """Set the properties of this physics child based on its cwxml."""
        child = self.bpy_object
        child_cwxml = self.cwxml

        child.child_properties.group = self.group
        child.child_properties.bone_tag = child_cwxml.bone_tag
        child.child_properties.pristine_mass = child_cwxml.pristine_mass
        child.child_properties.damaged_mass = child_cwxml.damaged_mass
        child.child_properties.unk_vec = child_cwxml.unk_vec
        child.child_properties.inertia_tensor = child_cwxml.inertia_tensor

    def create_collisions(self, bound_cwxml: ybnxml.BoundItem):
        """Create collisions for this child."""
        bound = bound_to_obj(bound_cwxml)
        bound.parent = self.group
        bound.name = self.group.name.replace("_group", "_col")

    def create_drawable(self):
        """Create drawable for this child."""
        drawable = DrawableCWXMLConverter(
            self.cwxml.drawable, materials=self.materials).create_bpy_object()
        drawable.matrix_basis = self.cwxml.drawable.matrix
        drawable.parent = self.bpy_object
