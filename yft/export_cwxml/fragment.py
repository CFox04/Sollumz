import os
import bpy
from mathutils import Matrix

from ...sollumz_converter import BPYConverter
from ...sollumz_properties import SollumType, SollumzExportSettings
from ...sollumz_helper import get_children_with_sollum_type
from ...cwxml.fragment import BoneTransformItem, Fragment
from ...ydr.ydrexport import get_used_materials, drawable_from_object, lights_from_object
from ...tools.meshhelper import get_bound_center, get_sphere_radius
from ...tools.blenderhelper import get_parent_bone, find_first_child
from .physicslod import PhysicsLodBPYConverter, get_group_index
from .window import WindowBPYConverter


class FragmentBPYConverter(BPYConverter[Fragment]):
    """Converts Fragment bpy objects to CWXML objects."""

    def create_cwxml(self) -> Fragment:
        self.cwxml = Fragment()
        # Object name without .00# suffix
        self.cwxml.name = self.bpy_object.name.split(".")[0]

        drawable = find_first_child(
            self.bpy_object, lambda child: child.sollum_type == SollumType.DRAWABLE)

        if drawable is None:
            self.export_operator.report(
                {"WARNING"}, f"Failed to create Fragment XML for {self.bpy_object.name}: No drawable to export!")
            return

        materials = get_used_materials(drawable)
        self.cwxml.drawable = drawable_from_object(
            self.export_operator, drawable, self.filepath, None, materials, self.export_settings, is_frag=True)

        lights_from_object(self.bpy_object, self.cwxml.lights,
                           self.export_settings, armature_obj=drawable)

        self.create_lods(materials)
        self.create_bone_transforms(drawable)
        self.create_vehicle_windows(materials)
        self.set_fragment_bounds()
        self.set_fragment_properties()

        return self.cwxml

    def create_lods(self, materials: list[bpy.types.Material]):
        """Create all LOD xml objects."""
        lods = {1: None, 2: None, 3: None}

        for child in self.bpy_object.children:
            if child.sollum_type != SollumType.FRAGLOD:
                continue

            lod_cwxml = PhysicsLodBPYConverter(child, materials).create_cwxml()

            lod_index: int = child.lod_properties.type
            lods[lod_index] = lod_cwxml
            # TODO: Temporary. Should be handled in cwxml code
            lod_cwxml.tag_name = f"LOD{lod_index}"

        self.cwxml.physics.lod1 = lods[1]
        self.cwxml.physics.lod2 = lods[2]
        self.cwxml.physics.lod3 = lods[3]

    def create_bone_transforms(self, drawable: bpy.types.Object):
        """Create all bone transforms based on the Drawable Models' matrix_basis."""
        # Index the matrix by bone_index
        bone_transforms_map = {}

        for child in self.bpy_object.children:
            if child.sollum_type != SollumType.DRAWABLE_MODEL:
                continue

            parent_bone = get_parent_bone(child)

            if parent_bone is None:
                continue

            bone_index = parent_bone.bone_properties.tag
            bone_transforms_map[bone_index] = child.matrix_basis

        for bone_index in range(len(drawable.data.bones)):
            matrix = bone_transforms_map.get(bone_index) or Matrix()
            self.cwxml.bones_transforms.append(
                BoneTransformItem("Item", matrix))

    def create_vehicle_windows(self, materials: list[bpy.types.Material]):
        """Create all vehicle window CWXML objects."""
        frag_windows = get_children_with_sollum_type(
            self.bpy_object, [SollumType.FRAGVEHICLEWINDOW])
        frag_groups = get_children_with_sollum_type(
            self.bpy_object, [SollumType.FRAGGROUP])

        for frag_window in frag_windows:
            group_index = get_group_index(frag_window.parent, frag_groups)
            self.cwxml.vehicle_glass_windows.append(
                WindowBPYConverter(frag_window).create_cwxml(group_index, materials))

    def set_fragment_bounds(self):
        """Set the BoundingSphereCenter and BoundingSphereRadius of this Fragment xml."""
        use_transforms = self.export_settings.use_transforms

        self.cwxml.bounding_sphere_center = get_bound_center(
            self.bpy_object, world=use_transforms)
        self.cwxml.bounding_sphere_radius = get_sphere_radius(
            self.cwxml.drawable.bounding_box_max, self.cwxml.bounding_sphere_center)

    def set_fragment_properties(self):
        """Set Fragment properties from fragment_properties data-block to XML."""
        fragment = self.bpy_object
        fragment_cwxml = self.cwxml

        fragment_cwxml.unknown_b0 = fragment.fragment_properties.unk_b0
        fragment_cwxml.unknown_b8 = fragment.fragment_properties.unk_b8
        fragment_cwxml.unknown_bc = fragment.fragment_properties.unk_bc
        fragment_cwxml.unknown_c0 = fragment.fragment_properties.unk_c0
        fragment_cwxml.unknown_c4 = fragment.fragment_properties.unk_c4
        fragment_cwxml.unknown_cc = fragment.fragment_properties.unk_cc
        fragment_cwxml.gravity_factor = fragment.fragment_properties.gravity_factor
        fragment_cwxml.buoyancy_factor = fragment.fragment_properties.buoyancy_factor

    @classmethod
    def bpy_to_xml_file(cls, filepath: str, bpy_object: bpy.types.Object, export_operator):
        # Implement bpy_to_xml_file method to allow exporting with a _hi yft.
        fragment_cwxml: Fragment = super().bpy_to_xml_file(
            filepath, bpy_object, export_operator)

        export_settings: SollumzExportSettings = cls.export_operator.export_settings

        if export_settings.export_with_hi:
            hi_cwxml = FragmentBPYConverter.convert_to_hi(fragment_cwxml)
            hi_cwxml.name = hi_cwxml.name + "_hi"
            filepath = os.path.join(os.path.dirname(filepath),
                                    os.path.basename(filepath).replace(".yft.xml", "_hi.yft.xml"))

            hi_cwxml.write_xml(filepath)

        return fragment_cwxml

    @staticmethod
    def convert_to_hi(fragment_cwxml: Fragment):
        """Convert Fragment cwxml to a _hi Fragment by removing lods and windows."""
        fragment_cwxml.drawable.drawable_models_med = None
        fragment_cwxml.drawable.drawable_models_low = None
        fragment_cwxml.drawable.drawable_models_vlow = None
        fragment_cwxml.vehicle_glass_windows = None

        for child in fragment_cwxml.physics.lod1.children:
            child.drawable.drawable_models_med = None
            child.drawable.drawable_models_low = None
            child.drawable.drawable_models_vlow = None

        return fragment_cwxml
