import bpy
from mathutils import Matrix

from ...cwxml import drawable as ydrxml
from ...sollumz_object import CWXMLConverter
from ...sollumz_properties import SollumType
from ...tools.blenderhelper import create_sollumz_object


class SkeletonCWXMLConverter(CWXMLConverter[ydrxml.SkeletonProperty]):

    def create_bpy_object(self, name: str, rotation_limits: list[ydrxml.RotationLimitItem]) -> bpy.types.Object:
        armature_data = bpy.data.armatures.new(name + ".skel")
        armature_object = create_sollumz_object(
            SollumType.DRAWABLE, armature_data, name=name)
        self.bpy_object = armature_object

        self.create_bones()

        if rotation_limits:
            self.apply_rotation_limits(rotation_limits)

        return armature_object

    def create_bones(self):
        """Create all bones for this skeleton based on the cwxml bones."""
        # Need to go into edit mode to create edit bones
        bpy.context.view_layer.objects.active = self.bpy_object
        bpy.ops.object.mode_set(mode="EDIT")

        for bone_cwxml in self.cwxml.bones:
            edit_bone = self.create_edit_bone(bone_cwxml)
            SkeletonCWXMLConverter.set_bone_transforms(edit_bone, bone_cwxml)

        bpy.ops.object.mode_set(mode="OBJECT")

        # Can't set pose bone properties until all edit_bones have been created
        # and back in object mode
        for bone_cwxml in self.cwxml.bones:
            pose_bone = self.bpy_object.pose.bones[bone_cwxml.name].bone
            SkeletonCWXMLConverter.set_pose_bone_properties(
                pose_bone, bone_cwxml)

    def apply_rotation_limits(self, rotation_limits: list[ydrxml.RotationLimitItem]):
        """Apply rotation limits to all pose bones of this skeleton based on
        the cwxml rotation limits given."""
        pose = self.bpy_object.pose
        tag_bone_map = {
            pose_bone.bone.bone_properties.tag: pose_bone.name for pose_bone in pose.bones}

        for rotation_limit in rotation_limits:
            pose_bone = pose.bones.get(tag_bone_map[rotation_limit.bone_id])
            SkeletonCWXMLConverter.set_rotation_limit(
                pose_bone, rotation_limit)

    def create_edit_bone(self, bone_cwxml: ydrxml.BoneItem) -> bpy.types.EditBone:
        """Create all edit bones for this skeleton."""
        armature: bpy.types.Armature = self.bpy_object.data

        edit_bone = armature.edit_bones.new(bone_cwxml.name)

        if bone_cwxml.parent_index != -1:
            edit_bone.parent = armature.edit_bones[bone_cwxml.parent_index]

        return edit_bone

    @staticmethod
    def set_bone_transforms(edit_bone: bpy.types.EditBone, bone_cwxml: ydrxml.BoneItem):
        """Set the transforms of edit_bone to that of bone_cwxml."""
        # https://github.com/LendoK/Blender_GTA_V_model_importer/blob/master/importer.py
        mat_rot = bone_cwxml.rotation.to_matrix().to_4x4()
        mat_loc = Matrix.Translation(bone_cwxml.translation)
        mat_sca = Matrix.Scale(1, 4, bone_cwxml.scale)

        edit_bone.head = (0, 0, 0)
        edit_bone.tail = (0, 0.05, 0)
        edit_bone.matrix = mat_loc @ mat_rot @ mat_sca

        if edit_bone.parent is not None:
            edit_bone.matrix = edit_bone.parent.matrix @ edit_bone.matrix

    @staticmethod
    def set_pose_bone_properties(pose_bone: bpy.types.PoseBone, bone_cwxml: ydrxml.BoneItem):
        """Set properties of pose bone based on the properties of the provided cwxml bone."""
        pose_bone.bone_properties.tag = bone_cwxml.tag
        # LimitRotation and Unk0 have their special meanings, can be deduced if needed when exporting
        flags_restricted = set(["LimitRotation", "Unk0"])
        for flag_cwxml in bone_cwxml.flags:
            if flag_cwxml in flags_restricted:
                continue

            flag = pose_bone.bone_properties.flags.add()
            flag.name = flag_cwxml

    @staticmethod
    def set_rotation_limit(pose_bone: bpy.types.PoseBone, rotation_limit: ydrxml.RotationLimitItem, ):
        """Set rotation limit of the pose bone provided to the rotation limit cwxml provided."""
        constraint = pose_bone.constraints.new("LIMIT_ROTATION")

        constraint.owner_space = "LOCAL"
        constraint.use_limit_x = True
        constraint.use_limit_y = True
        constraint.use_limit_z = True
        constraint.max_x = rotation_limit.max.x
        constraint.max_y = rotation_limit.max.y
        constraint.max_z = rotation_limit.max.z
        constraint.min_x = rotation_limit.min.x
        constraint.min_y = rotation_limit.min.y
        constraint.min_z = rotation_limit.min.z
