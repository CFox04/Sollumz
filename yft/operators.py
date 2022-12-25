import bpy

from ..sollumz_properties import SollumType, LODLevel, FRAGMENT_TYPES
from ..tools.blenderhelper import get_children_recursive
from ..sollumz_helper import find_fragment_parent


class SOLLUMZ_OT_ADD_FRAG_LOD(bpy.types.Operator):
    bl_idname = "sollumz.addfraglod"
    bl_label = "Add LOD"

    @classmethod
    def poll(cls, context):
        active_obj = context.view_layer.objects.active
        if active_obj is None or active_obj.sollum_type != SollumType.FRAGMENT:
            return False

        return 3 > len(active_obj.sollumz_fragment_lods) >= 0

    def execute(self, context):
        active_obj = context.view_layer.objects.active
        frag_lods = active_obj.sollumz_fragment_lods
        frag_lods.add()

        return {"FINISHED"}


class SOLLUMZ_OT_REMOVE_FRAG_LOD(bpy.types.Operator):
    bl_idname = "sollumz.removefraglod"
    bl_label = "Remove LOD"

    @classmethod
    def poll(cls, context):
        active_obj = context.view_layer.objects.active
        if active_obj is None or active_obj.sollum_type != SollumType.FRAGMENT:
            return False

        active_lod_index = active_obj.sollumz_active_frag_lod_index

        return active_lod_index < len(active_obj.sollumz_fragment_lods) or 1 > len(active_obj.sollumz_fragment_lods) > 0

    def execute(self, context):
        active_obj = context.view_layer.objects.active
        frag_lods = active_obj.sollumz_fragment_lods
        active_lod_index = active_obj.sollumz_active_frag_lod_index

        frag_lods.remove(active_lod_index)

        return {"FINISHED"}


class SetLodLevelHelper:
    LOD_LEVEL: LODLevel = LODLevel.HIGH
    bl_description = "Set the viewing level for the selected Fragment."

    @classmethod
    def poll(cls, context):
        active_obj = context.view_layer.objects.active

        return active_obj is not None and find_fragment_parent(active_obj)

    def set_fragment_object_layer(self, frag_obj: bpy.types.Object, context: bpy.types.Context):
        context.scene.sollumz_frag_is_hidden = False
        frag_obj.hide_set(False)

        for child in get_children_recursive(frag_obj):
            if child.sollum_type not in FRAGMENT_TYPES or child.sollum_type == SollumType.FRAGVEHICLEWINDOW:
                continue

            if child.type == "MESH":
                child.sollumz_object_lods.set_active_lod(self.LOD_LEVEL)
                continue

    def execute(self, context):
        active_obj = context.view_layer.objects.active
        frag_obj = find_fragment_parent(active_obj)
        self.set_fragment_object_layer(frag_obj, context)

        return {"FINISHED"}


class SOLLUMZ_OT_SET_FRAG_VERY_HIGH(bpy.types.Operator, SetLodLevelHelper):
    bl_idname = "sollumz.set_frag_very_high"
    bl_label = "Very High"

    LOD_LEVEL = LODLevel.VERYHIGH


class SOLLUMZ_OT_SET_FRAG_HIGH(bpy.types.Operator, SetLodLevelHelper):
    bl_idname = "sollumz.set_frag_high"
    bl_label = "High"

    LOD_LEVEL = LODLevel.HIGH


class SOLLUMZ_OT_SET_FRAG_MED(bpy.types.Operator, SetLodLevelHelper):
    bl_idname = "sollumz.set_frag_med"
    bl_label = "Medium"

    LOD_LEVEL = LODLevel.MEDIUM


class SOLLUMZ_OT_SET_FRAG_LOW(bpy.types.Operator, SetLodLevelHelper):
    bl_idname = "sollumz.set_frag_low"
    bl_label = "Low"

    LOD_LEVEL = LODLevel.LOW


class SOLLUMZ_OT_SET_FRAG_VLOW(bpy.types.Operator, SetLodLevelHelper):
    bl_idname = "sollumz.set_frag_vlow"
    bl_label = "Very Low"

    LOD_LEVEL = LODLevel.VERYLOW


class SOLLUMZ_OT_SET_FRAG_HIDDEN(bpy.types.Operator, SetLodLevelHelper):
    bl_idname = "sollumz.set_frag_hidden"
    bl_label = "Hidden"

    @staticmethod
    def set_highest_lod_active(obj: bpy.types.Object):
        for lod_level in [LODLevel.HIGH, LODLevel.MEDIUM, LODLevel.LOW, LODLevel.VERYLOW]:
            if obj.sollumz_object_lods.get_lod(lod_level) is None:
                continue

            obj.sollumz_object_lods.set_active_lod(lod_level)

            break

    def execute(self, context):
        active_obj = context.view_layer.objects.active
        frag_obj = find_fragment_parent(active_obj)
        frag_hidden = context.scene.sollumz_frag_is_hidden

        do_hide = not frag_hidden
        context.scene.sollumz_frag_is_hidden = do_hide

        frag_obj.hide_set(do_hide)

        for child in get_children_recursive(frag_obj):
            if child.sollum_type not in FRAGMENT_TYPES or child.sollum_type == SollumType.FRAGVEHICLEWINDOW:
                continue

            if child.type == "MESH" and do_hide is False:
                SOLLUMZ_OT_SET_FRAG_HIDDEN.set_highest_lod_active(child)

            child.hide_set(do_hide)

        return {"FINISHED"}
