from ...sollumz_converter import BPYConverter
from ...cwxml.fragment import GroupItem


class PhysicsGroupBPYConverter(BPYConverter[GroupItem]):
    """Converts Fragment group objects to CWXML objects"""

    def create_cwxml(self, parent_index: int) -> GroupItem:
        self.cwxml = GroupItem()
        self.cwxml.name = self.bpy_object.name.replace(
            "_group", "").split(".")[0]
        self.cwxml.parent_index = parent_index

        self.set_physics_group_properties()

        return self.cwxml

    def set_physics_group_properties(self):
        """Set xml physics group properties based on the group_properties data-block."""
        group = self.bpy_object
        group_cwxml = self.cwxml

        group_cwxml.glass_window_index = group.group_properties.glass_window_index
        group_cwxml.glass_flags = group.group_properties.glass_flags
        group_cwxml.strength = group.group_properties.strength
        group_cwxml.force_transmission_scale_up = group.group_properties.force_transmission_scale_up
        group_cwxml.force_transmission_scale_down = group.group_properties.force_transmission_scale_down
        group_cwxml.joint_stiffness = group.group_properties.joint_stiffness
        group_cwxml.min_soft_angle_1 = group.group_properties.min_soft_angle_1
        group_cwxml.max_soft_angle_1 = group.group_properties.max_soft_angle_1
        group_cwxml.max_soft_angle_2 = group.group_properties.max_soft_angle_2
        group_cwxml.max_soft_angle_3 = group.group_properties.max_soft_angle_3
        group_cwxml.rotation_speed = group.group_properties.rotation_speed
        group_cwxml.rotation_strength = group.group_properties.rotation_strength
        group_cwxml.restoring_max_torque = group.group_properties.restoring_max_torque
        group_cwxml.latch_strength = group.group_properties.latch_strength
        group_cwxml.mass = group.group_properties.mass
        group_cwxml.min_damage_force = group.group_properties.min_damage_force
        group_cwxml.damage_health = group.group_properties.damage_health
        group_cwxml.unk_float_5c = group.group_properties.unk_float_5c
        group_cwxml.unk_float_60 = group.group_properties.unk_float_60
        group_cwxml.unk_float_64 = group.group_properties.unk_float_64
        group_cwxml.unk_float_68 = group.group_properties.unk_float_68
        group_cwxml.unk_float_6c = group.group_properties.unk_float_6c
        group_cwxml.unk_float_70 = group.group_properties.unk_float_70
        group_cwxml.unk_float_74 = group.group_properties.unk_float_74
        group_cwxml.unk_float_78 = group.group_properties.unk_float_78
        group_cwxml.unk_float_a8 = group.group_properties.unk_float_a8
