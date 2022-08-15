import bpy

from ..sollumz_properties import SOLLUMZ_UI_NAMES, SollumType, LODLevel, items_from_enums
from ..sollumz_ui import SOLLUMZ_PT_OBJECT_PANEL


class SOLLUMZ_PT_MODEL_LODS_PANEL(bpy.types.Panel):
    bl_label = "Level of Detail (LODs)"
    bl_idname = "SOLLUMZ_PT_MODEL_LODS_PANEL"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_parent_id = SOLLUMZ_PT_OBJECT_PANEL.bl_idname
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        active_obj = context.view_layer.objects.active
        return active_obj is not None and active_obj.sollum_type == SollumType.DRAWABLE_MODEL

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        active_obj = context.view_layer.objects.active
        active_lod_level = active_obj.sollumz_active_lod

        layout.prop(active_obj, "sollumz_active_lod")
        layout.prop(active_obj.sollumz_lod_meshes,
                    active_lod_level, text="LOD Mesh")


class LODMeshes(bpy.types.PropertyGroup):
    def set_lod_mesh(context: bpy.types.Context, lod_mesh: bpy.types.Mesh, lod_level: LODLevel):
        active_obj = context.view_layer.objects.active
        active_lod = active_obj.sollumz_active_lod

        if active_lod == lod_level and isinstance(lod_mesh, bpy.types.Mesh):
            active_obj.data = lod_mesh

    def update_high(self, context):
        lod_level = LODLevel.HIGH
        LODMeshes.set_lod_mesh(context, self[lod_level], lod_level)

    def update_medium(self, context):
        lod_level = LODLevel.MEDIUM
        LODMeshes.set_lod_mesh(context, self[lod_level], lod_level)

    def update_low(self, context):
        lod_level = LODLevel.LOW
        LODMeshes.set_lod_mesh(context, self[lod_level], lod_level)

    def update_vlow(self, context):
        lod_level = LODLevel.VERYLOW
        LODMeshes.set_lod_mesh(context, self[lod_level], lod_level)

    sollumz_high: bpy.props.PointerProperty(
        name=SOLLUMZ_UI_NAMES[LODLevel.HIGH], type=bpy.types.Mesh, update=update_high)
    sollumz_medium: bpy.props.PointerProperty(
        name=SOLLUMZ_UI_NAMES[LODLevel.MEDIUM], type=bpy.types.Mesh, update=update_medium)
    sollumz_low: bpy.props.PointerProperty(
        name=SOLLUMZ_UI_NAMES[LODLevel.LOW], type=bpy.types.Mesh, update=update_low)
    sollumz_verylow: bpy.props.PointerProperty(
        name=SOLLUMZ_UI_NAMES[LODLevel.VERYLOW], type=bpy.types.Mesh, update=update_vlow)


def update_active_lod(self: bpy.types.Object, context):
    active_lod = self.sollumz_active_lod
    lod_mesh = self.sollumz_lod_meshes.get(active_lod)

    if isinstance(lod_mesh, bpy.types.Mesh):
        self.data = lod_mesh


def register():
    bpy.types.Object.sollumz_lod_meshes = bpy.props.PointerProperty(
        type=LODMeshes)
    bpy.types.Object.sollumz_active_lod = bpy.props.EnumProperty(
        items=items_from_enums(LODLevel), name="Active LOD", description="The active LOD to be displayed in the viewport", update=update_active_lod)


def unregister():
    del bpy.types.Object.sollumz_lod_meshes
    del bpy.types.Object.sollumz_active_lod
