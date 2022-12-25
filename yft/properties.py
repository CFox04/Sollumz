import bpy
from typing import Union

from ..sollumz_properties import SOLLUMZ_UI_NAMES, SollumType, LODLevel, items_from_enums


class FragmentProperties(bpy.types.PropertyGroup):
    unk_b0: bpy.props.FloatProperty(name="UnknownB0")
    unk_b8: bpy.props.FloatProperty(name="UnknownB8")
    unk_bc: bpy.props.FloatProperty(name="UnknownBC")
    unk_c0: bpy.props.FloatProperty(name="UnknownC0", default=65280)
    unk_c4: bpy.props.FloatProperty(name="UnknownC4")
    unk_cc: bpy.props.FloatProperty(name="UnknownCC")
    gravity_factor: bpy.props.FloatProperty(name="Gravity Factor")
    buoyancy_factor: bpy.props.FloatProperty(name="Buoyancy Factor")


class LODProperties(bpy.types.PropertyGroup):
    def get_name(self) -> str:
        return f"LOD{self.number}"

    number: bpy.props.IntProperty(name="Number", default=1)

    unknown_14: bpy.props.FloatProperty(name="Unknown14")
    unknown_18: bpy.props.FloatProperty(name="Unknown18")
    unknown_1c: bpy.props.FloatProperty(name="Unknown1C")
    position_offset: bpy.props.FloatVectorProperty(name="Position Offset")
    unknown_40: bpy.props.FloatVectorProperty(name="Unknown40")
    unknown_50: bpy.props.FloatVectorProperty(name="Unknown50")
    damping_linear_c: bpy.props.FloatVectorProperty(
        name="Damping Linear C", default=(0.02, 0.02, 0.02))
    damping_linear_v: bpy.props.FloatVectorProperty(
        name="Damping Linear V", default=(0.02, 0.02, 0.02))
    damping_linear_v2: bpy.props.FloatVectorProperty(
        name="Damping Linear V2", default=(0.01, 0.01, 0.01))
    damping_angular_c: bpy.props.FloatVectorProperty(
        name="Damping Angular C", default=(0.02, 0.02, 0.02))
    damping_angular_v: bpy.props.FloatVectorProperty(
        name="Damping Angular V", default=(0.02, 0.02, 0.02))
    damping_angular_v2: bpy.props.FloatVectorProperty(
        name="Damping Angular V2", default=(0.01, 0.01, 0.01))
    # archetype properties
    archetype_name: bpy.props.StringProperty(name="Name")
    archetype_mass: bpy.props.FloatProperty(name="Mass")
    archetype_unknown_48: bpy.props.FloatProperty(name="Unknown48", default=1)
    archetype_unknown_4c: bpy.props.FloatProperty(
        name="Unknown4c", default=150)
    archetype_unknown_50: bpy.props.FloatProperty(
        name="Unknown50", default=6.28)
    archetype_unknown_54: bpy.props.FloatProperty(name="Unknown54", default=1)
    archetype_inertia_tensor: bpy.props.FloatVectorProperty(
        name="Inertia Tensor")


class GroupProperties(bpy.types.PropertyGroup):
    glass_window_index: bpy.props.IntProperty(name="Glass Window Index")
    glass_flags: bpy.props.IntProperty(name="Glass Flags")
    strength: bpy.props.FloatProperty(name="Strength")
    force_transmission_scale_up: bpy.props.FloatProperty(
        name="Force Transmission Scale Up")
    force_transmission_scale_down: bpy.props.FloatProperty(
        name="Force Transmission Scale Down")
    joint_stiffness: bpy.props.FloatProperty(name="Joint Stiffness")
    min_soft_angle_1: bpy.props.FloatProperty(
        name="Min Soft Angle 1", default=-1)
    max_soft_angle_1: bpy.props.FloatProperty(
        name="Max Soft Angle 1", default=1)
    max_soft_angle_2: bpy.props.FloatProperty(
        name="Max Soft Angle 2", default=1)
    max_soft_angle_3: bpy.props.FloatProperty(
        name="Max Soft Angle 3", default=1)
    rotation_speed: bpy.props.FloatProperty(name="Rotation Speed")
    rotation_strength: bpy.props.FloatProperty(name="Restoring Strength")
    restoring_max_torque: bpy.props.FloatProperty(name="Restoring Max Torque")
    latch_strength: bpy.props.FloatProperty(name="Latch Strength")
    min_damage_force: bpy.props.FloatProperty(name="Min Damage Force")
    damage_health: bpy.props.FloatProperty(name="Damage Health")
    unk_float_5c: bpy.props.FloatProperty(name="UnkFloat5C")
    unk_float_60: bpy.props.FloatProperty(name="UnkFloat60")
    unk_float_64: bpy.props.FloatProperty(name="UnkFloat64")
    unk_float_68: bpy.props.FloatProperty(name="UnkFloat68")
    unk_float_6c: bpy.props.FloatProperty(name="UnkFloat6C")
    unk_float_70: bpy.props.FloatProperty(name="UnkFloat70")
    unk_float_74: bpy.props.FloatProperty(name="UnkFloat74")
    unk_float_78: bpy.props.FloatProperty(name="UnkFloat78")
    unk_float_a8: bpy.props.FloatProperty(name="UnkFloatA8")


class ChildProperties(bpy.types.PropertyGroup):
    mass: bpy.props.FloatProperty(name="Mass", min=0)
    damaged: bpy.props.BoolProperty(name="Damaged")


class VehicleWindowProperties(bpy.types.PropertyGroup):
    unk_float_17: bpy.props.FloatProperty(name="Unk Float 17")
    unk_float_18: bpy.props.FloatProperty(name="Unk Float 18")
    cracks_texture_tiling: bpy.props.FloatProperty(
        name="Cracks Texture Tiling")


class ObjectLODProps(bpy.types.PropertyGroup):
    def update_object(self, context):
        obj: bpy.types.Object = self.id_data

        active_obj_lod = obj.sollumz_object_lods.active_lod

        if active_obj_lod == self and self.mesh is not None:
            obj.data = self.mesh
            obj.hide_set(False)
        elif self.mesh is None:
            obj.hide_set(True)

    type: bpy.props.EnumProperty(
        items=items_from_enums(LODLevel))
    mesh: bpy.props.PointerProperty(
        type=bpy.types.Mesh, update=update_object)


class LODLevels(bpy.types.PropertyGroup):
    def get_lod(self, lod_type: str) -> Union[ObjectLODProps, None]:
        for lod in self.lods:
            if lod.type == lod_type:
                return lod

    def set_lod_mesh(self, lod_type: str, mesh: bpy.types.Mesh) -> Union[ObjectLODProps, None]:
        for lod in self.lods:
            if lod.type == lod_type:
                lod.mesh = mesh
                return lod

    def add_lod(self, lod_type: str, mesh: Union[bpy.types.Mesh, None] = None) -> ObjectLODProps:
        # Can't have multiple lods with the same type
        if self.get_lod(lod_type):
            return None

        self.lods.add()
        i = len(self.lods) - 1
        obj_lod = self.lods[i]
        obj_lod.type = lod_type

        if mesh is not None:
            obj_lod.mesh = mesh

        return obj_lod

    def remove_lod(self, lod_type: str):
        for i, lod in enumerate(self.lods):
            if lod.type == lod_type:
                self.lods.remove(i)
                return

    def set_active_lod(self, lod_type: str):
        for i, lod in enumerate(self.lods):
            if lod.type == lod_type:
                self.active_lod_index = i
                return

    def update_active_lod(self, context):
        self.active_lod.update_object(context)

    def add_empty_lods(self):
        """Add all LOD lods with no meshes assigned."""
        self.add_lod(LODLevel.VERYHIGH)
        self.add_lod(LODLevel.HIGH)
        self.add_lod(LODLevel.MEDIUM)
        self.add_lod(LODLevel.LOW)
        self.add_lod(LODLevel.VERYLOW)

    # def rename_meshes(self, obj_name: str):
    #     """Rename meshes to <obj_name>_<lod_level>"""
    #     for lod in self.lods:
    #         if lod.mesh is None:
    #             continue
    #         lod_level = SOLLUMZ_UI_NAMES[lod.type].lower().replace(' ', '_')
    #         lod.mesh.name = f"{obj_name}_{lod_level}"

    @property
    def active_lod(self) -> Union[ObjectLODProps, None]:
        if self.active_lod_index < len(self.lods):
            return self.lods[self.active_lod_index]

    lods: bpy.props.CollectionProperty(type=ObjectLODProps)
    active_lod_index: bpy.props.IntProperty(
        min=0, update=update_active_lod)


def register():
    bpy.types.Object.fragment_properties = bpy.props.PointerProperty(
        type=FragmentProperties)
    bpy.types.Object.child_properties = bpy.props.PointerProperty(
        type=ChildProperties)
    bpy.types.Object.vehicle_window_properties = bpy.props.PointerProperty(
        type=VehicleWindowProperties)
    bpy.types.Object.is_physics_child_mesh = bpy.props.BoolProperty(
        name="Is Physics Child", description="Whether or not this fragment mesh is a physics child. Usually wheels meshes are physics children.")

    bpy.types.Object.sollumz_fragment_lods = bpy.props.CollectionProperty(
        type=LODProperties)
    bpy.types.Object.sollumz_active_frag_lod_index = bpy.props.IntProperty(
        min=0)

    bpy.types.Object.glass_thickness = bpy.props.FloatProperty(
        name="Thickness", default=0.1)

    bpy.types.Scene.create_fragment_type = bpy.props.EnumProperty(
        items=[
            (SollumType.FRAGMENT.value,
             SOLLUMZ_UI_NAMES[SollumType.FRAGMENT], "Create a fragment object."),
            (SollumType.FRAGLOD.value,
             SOLLUMZ_UI_NAMES[SollumType.FRAGLOD], "Create a fragment LOD object."),
            (SollumType.FRAGGROUP.value,
             SOLLUMZ_UI_NAMES[SollumType.FRAGGROUP], "Create a fragment group object."),
            (SollumType.FRAGCHILD.value,
             SOLLUMZ_UI_NAMES[SollumType.FRAGCHILD], "Create a fragment child object."),
        ],
        name="Type",
        default=SollumType.FRAGMENT.value
    )
    bpy.types.Object.sollumz_object_lods = bpy.props.PointerProperty(
        type=LODLevels)

    bpy.types.Scene.sollumz_frag_is_hidden = bpy.props.BoolProperty()

    bpy.types.Bone.group_properties = bpy.props.PointerProperty(
        type=GroupProperties)
    bpy.types.Bone.sollumz_use_physics = bpy.props.BoolProperty(
        name="Use Physics", description="Whether or not to use physics for this fragment bone")


def unregister():
    del bpy.types.Object.fragment_properties
    del bpy.types.Object.child_properties
    del bpy.types.Object.vehicle_window_properties
    del bpy.types.Object.is_physics_child_mesh
    del bpy.types.Object.sollumz_fragment_lods
    del bpy.types.Object.sollumz_active_frag_lod_index
    del bpy.types.Object.sollumz_object_lods

    del bpy.types.Scene.sollumz_frag_is_hidden

    del bpy.types.Bone.group_properties
    del bpy.types.Bone.sollumz_use_physics
