import os
import bpy
from traceback import format_exc
from mathutils import Matrix, Vector
from typing import Dict, Union, Optional
from ..tools.blenderhelper import create_empty_object, material_from_image, create_mesh_object, remove_number_suffix
from ..tools.meshhelper import create_uv_layer
from ..tools.utils import multiply_homogeneous
from ..sollumz_properties import SollumType, SollumzImportSettings, LODLevel, SOLLUMZ_UI_NAMES
from ..cwxml.fragment import YFT, Fragment, LODProperty, GroupItem, ChildrenItem, WindowItem
from ..cwxml.drawable import Drawable, BoneItem, ShaderGroupProperty
from ..ydr.ydrimport import shadergroup_to_materials, shader_item_to_material, skeleton_to_obj, rotation_limits_to_obj, create_lights
from ..ybn.ybnimport import bound_to_obj
from ..ydr.ydrexport import calculate_bone_tag
from .. import logger
from .properties import LODProperties
from .create_drawable_mesh import create_drawable_mesh, add_armature_constraint


def import_yft(filepath: str, import_settings: SollumzImportSettings):
    yft_xml: YFT = YFT.from_xml_file(filepath)

    hi_xml: YFT | None = None

    if import_settings.import_with_hi:
        hi_path = find_hi_yft(filepath)

        if os.path.exists(hi_path):
            # Only the drawable is needed
            hi_xml = YFT.from_xml_file(hi_path)
        else:
            logger.warning(
                f"Could not find _hi yft for {os.path.basename(filepath)}! Make sure there is a file named '{os.path.basename(hi_path)}' in the same directory!")

    create_fragment_obj(yft_xml, filepath,
                        split_by_group=import_settings.split_by_group, hi_xml=hi_xml)


def find_hi_yft(yft_filepath: str) -> str or None:
    yft_dir = os.path.dirname(yft_filepath)
    yft_name = os.path.basename(yft_filepath).split(".")[0]

    hi_path = os.path.join(yft_dir, f"{yft_name}_hi.yft.xml")

    return hi_path


def create_fragment_obj(frag_xml: Fragment, filepath: str, split_by_group: bool = False, hi_xml: Optional[Fragment] = None):
    frag_obj = create_frag_armature(frag_xml)
    drawable_xml = frag_xml.drawable

    set_fragment_properties(frag_xml, frag_obj)

    materials = None
    hi_materials = None

    if hi_xml is not None:
        materials, hi_materials = create_materials_with_hi(
            drawable_xml.shader_group, hi_xml.drawable.shader_group, filepath)
        rename_materials(hi_materials)
    else:
        materials: list[bpy.types.Material] = shadergroup_to_materials(
            frag_xml.drawable.shader_group, filepath)
        rename_materials(materials)

    mesh_empty = create_empty_object(SollumType.NONE, f"{frag_obj.name}.mesh")
    mesh_empty.parent = frag_obj

    mesh_objs = create_drawable_mesh(drawable_xml, materials, frag_obj,
                                     mesh_empty, split_by_group)

    if hi_xml is not None:
        hi_mesh_objs = create_drawable_mesh(hi_xml.drawable, hi_materials,
                                            frag_obj, mesh_empty, split_by_group)
        create_very_high_lods(mesh_objs, hi_mesh_objs)

    create_frag_collisions(frag_xml, frag_obj)

    create_frag_lods(frag_xml, frag_obj)
    set_all_bone_physics_properties(frag_obj.data, frag_xml)
    create_frag_child_meshes(
        frag_xml, frag_obj, mesh_empty, materials, hi_materials, hi_xml)
    create_vehicle_windows(frag_xml, frag_obj, materials)

    if frag_xml.lights:
        lights_parent = create_lights(frag_xml.lights, frag_obj, frag_obj)
        lights_parent.name = f"{frag_obj.name}.lights"


def create_frag_armature(frag_xml: Fragment):
    name = frag_xml.name.replace("pack:/", "")
    skel = bpy.data.armatures.new(f"{name}.skel")
    frag_obj = create_mesh_object(SollumType.FRAGMENT, name, skel)

    skeleton_to_obj(frag_xml.drawable.skeleton, frag_obj)
    rotation_limits_to_obj(frag_xml.drawable.joints.rotation_limits, frag_obj)

    return frag_obj


def create_materials_with_hi(shader_group: ShaderGroupProperty, hi_shader_group: ShaderGroupProperty, filepath: str):
    """Returns a list of non_hi and a list of _hi materials."""
    # The hi model will always contain more shaders than the non hi model, so we create those materials first
    hi_materials: list[bpy.types.Material] = shadergroup_to_materials(
        hi_shader_group, filepath)
    non_hi_materials: list[bpy.types.Material] = []
    non_hi_index = 0

    # Now we add the corresponding non_hi shaders to the non_hi_materials list
    for i, shader in enumerate(hi_shader_group.shaders):
        if non_hi_index >= len(shader_group.shaders):
            break

        if shader_group.shaders[non_hi_index].name != shader.name:
            continue

        non_hi_materials.append(hi_materials[i])
        non_hi_index += 1

    # Sometimes, the non_hi model will also contain shaders that the hi model does not have, so we need to add those as well.
    if len(non_hi_materials) < len(shader_group.shaders):
        for shader in shader_group.shaders[non_hi_index:]:
            non_hi_materials.append(shader_item_to_material(
                shader, shader_group, filepath))

    return non_hi_materials, hi_materials


def create_very_high_lods(mesh_objs: list[bpy.types.Object], hi_mesh_objs: list[bpy.types.Object]):
    """Add the hi_meshes to the very high LOD level of each corresponding non_hi_mesh."""
    hi_meshes_by_name: dict[str, bpy.types.Object] = {
        remove_number_suffix(obj.name): obj for obj in hi_mesh_objs}

    for mesh in mesh_objs:
        mesh_name = remove_number_suffix(mesh.name)

        if mesh_name not in hi_meshes_by_name:
            continue

        hi_mesh = hi_meshes_by_name[mesh_name]
        hi_mesh.data.name = f"{mesh_name}_very_high"
        mesh.sollumz_object_lods.set_lod_mesh(LODLevel.VERYHIGH, hi_mesh.data)
        mesh.sollumz_object_lods.set_active_lod(LODLevel.VERYHIGH)

        bpy.data.objects.remove(hi_mesh)

        # In case a .00# suffix got added
        mesh.name = mesh_name


def rename_materials(materials: list[bpy.types.Material]):
    """Rename materials to use texture name."""
    for material in materials:
        for node in material.node_tree.nodes:
            if not isinstance(node, bpy.types.ShaderNodeTexImage) or not node.is_sollumz or node.name != "DiffuseSampler":
                continue

            material.name = node.sollumz_texture_name
            break


def create_frag_lods(frag_xml: Fragment, frag_obj: bpy.types.Object):
    for i, lod_xml in frag_xml.get_lods_by_id().items():
        if not lod_xml.groups:
            continue

        lod_props: LODProperties = frag_obj.sollumz_fragment_lods.add()
        set_lod_properties(lod_xml, lod_props)
        lod_props.number = i


def set_all_bone_physics_properties(armature: bpy.types.Armature, frag_xml: Fragment):
    """Set the physics group properties for all bones in the armature."""
    groups_xml: list[GroupItem] = frag_xml.physics.lod1.groups

    for group_xml in groups_xml:
        if group_xml.name not in armature.bones:
            logger.warning(
                f"No bone exists for the physics group {group_xml.name}! Skipping...")
            continue

        bone = armature.bones[group_xml.name]
        bone.sollumz_use_physics = True
        set_group_properties(group_xml, bone)


def drawable_is_empty(drawable: Drawable):
    return len(drawable.all_models) == 0


def get_child_transforms(lod_xml: LODProperty, child_index: int) -> Matrix:
    transform = lod_xml.transforms[child_index].value
    a = transform[3][0] + lod_xml.position_offset.x
    b = transform[3][1] + lod_xml.position_offset.y
    c = transform[3][2] + lod_xml.position_offset.z
    transform[3][0] = a
    transform[3][1] = b
    transform[3][2] = c

    return transform.transposed()


def create_frag_collisions(frag_xml: Fragment, frag_obj: bpy.types.Object) -> Union[bpy.types.Object, None]:
    bounds_xml = frag_xml.physics.lod1.archetype.bounds

    if bounds_xml is None:
        logger.warn(
            "Fragment has no collisions! (Make sure the yft file has not been damaged) Skipping...")
        return None

    collisions_empty = create_empty_object(
        SollumType.NONE, f"{frag_obj.name}.col")
    collisions_empty.parent = frag_obj

    for i, bound_xml in enumerate(bounds_xml.children):
        bound_obj = bound_to_obj(bound_xml)
        bound_obj.parent = collisions_empty

        bone = find_bound_bone(i, frag_xml)
        if bone is None:
            continue

        bound_obj.name = f"{bone.name}.col"
        add_armature_constraint(bound_obj, frag_obj, bone.name, False)
        bound_obj.child_properties.mass = frag_xml.physics.lod1.children[i].pristine_mass


def find_bound_bone(bound_index: int, frag_xml: Fragment) -> Union[BoneItem, None]:
    """Get corresponding bound bone based on children"""
    children = frag_xml.physics.lod1.children

    if bound_index >= len(children):
        return

    corresponding_child = children[bound_index]
    for bone in frag_xml.drawable.skeleton.bones:
        if bone.tag != corresponding_child.bone_tag:
            continue

        return bone


def create_frag_child_meshes(frag_xml: Fragment, frag_obj: bpy.types.Object, parent_obj: bpy.types.Object, materials: list[bpy.types.Material], hi_materials: Optional[list[bpy.types.Material]], hi_xml: Optional[Fragment] = None):
    lod_xml = frag_xml.physics.lod1
    children_xml: list[ChildrenItem] = lod_xml.children
    hi_children: list[ChildrenItem] = hi_xml.physics.lod1.children if hi_xml else []
    bones = frag_xml.drawable.skeleton.bones

    bone_name_by_tag: dict[str, BoneItem] = {
        bone.tag: bone.name for bone in bones}

    for i, child_xml in enumerate(children_xml):
        group_index = child_xml.group_index

        if group_index >= len(lod_xml.groups):
            logger.warning(
                "A fragment child has an invalid group index! Skipping...")
            continue

        if child_xml.bone_tag not in bone_name_by_tag:
            logger.warning(
                "A fragment child has an invalid bone tag! Skipping...")
            continue

        bone_name = bone_name_by_tag[child_xml.bone_tag]

        if drawable_is_empty(child_xml.drawable):
            continue

        child_obj = create_drawable_mesh(
            child_xml.drawable, materials, frag_obj, parent_obj)[0]
        add_armature_constraint(child_obj, frag_obj, bone_name)
        child_obj.name = f"{bone_name}.child"
        child_obj.is_physics_child_mesh = True

        if hi_children:
            child_hi_obj = create_drawable_mesh(
                hi_children[i].drawable, hi_materials, frag_obj, parent_obj)[0]
            child_hi_obj.data.name = f"{bone_name}_very_high"

            child_obj.sollumz_object_lods.set_lod_mesh(
                LODLevel.VERYHIGH, child_hi_obj.data)
            child_obj.sollumz_object_lods.set_active_lod(LODLevel.VERYHIGH)

            bpy.data.objects.remove(child_hi_obj)

        # Rename lod meshes
        for lod in child_obj.sollumz_object_lods.lods:
            if lod.mesh is None:
                continue
            lod_level_name = SOLLUMZ_UI_NAMES[lod.type].lower().replace(
                ' ', '_')
            lod.mesh.name = f"{bone_name}_{lod_level_name}"


def create_vehicle_windows(frag_xml: Fragment, frag_obj: bpy.types.Object, materials: list[bpy.types.Material]):
    if not frag_xml.vehicle_glass_windows:
        return

    veh_windows_empty = create_empty_object(
        SollumType.NONE, f"{frag_obj.name}.glass_shards")
    veh_windows_empty.parent = frag_obj

    window_xml: WindowItem
    for window_xml in frag_xml.vehicle_glass_windows:
        window_bone = get_window_bone(
            window_xml, frag_xml, frag_obj.data.bones)
        window_location = window_bone.matrix_local.translation

        window_name = f"{window_bone.name}_glass_shard"

        try:
            mesh = create_vehicle_window_mesh(
                window_xml, window_name, window_bone.matrix_local)
        except:
            logger.error(
                f"Error during creation of vehicle window mesh:\n{format_exc()}")
            continue

        texcoords = [[0, 1], [0, 0], [1, 0], [1, 1]]
        create_uv_layer(mesh, 0, texcoords, flip_uvs=False)

        if window_xml.shattermap:
            shattermap_mat = shattermap_to_material(
                window_xml.shattermap, mesh.name + "_shattermap.bmp")
            mesh.materials.append(shattermap_mat)

        # UnkUShort1 indexes the geometry that the window uses.
        # The VehicleGlassWindow uses the same material that the geometry uses.
        geometry_index = window_xml.unk_ushort_1
        window_mat = get_geometry_material(frag_xml, materials, geometry_index)
        mesh.materials.append(window_mat)

        window_obj = bpy.data.objects.new(mesh.name, mesh)
        window_obj.sollum_type = SollumType.FRAGVEHICLEWINDOW

        window_obj.location = window_location
        add_armature_constraint(window_obj, frag_obj,
                                window_bone.name, set_transforms=False)

        set_veh_window_properties(window_xml, window_obj)

        bpy.context.collection.objects.link(window_obj)
        window_obj.parent = veh_windows_empty


def get_window_bone(window_xml: WindowItem, frag_xml: Fragment, bpy_bones: bpy.types.ArmatureBones) -> bpy.types.Bone:
    children_xml: list[ChildrenItem] = frag_xml.physics.lod1.children

    child_id: int = window_xml.item_id

    if child_id < 0 or child_id >= len(children_xml):
        return bpy_bones[0]

    child_xml = children_xml[child_id]

    for bone in bpy_bones:
        if calculate_bone_tag(bone.name) != child_xml.bone_tag:
            continue

        return bone

    return bpy_bones[0]


def create_vehicle_window_mesh(window_xml: WindowItem, name: str, child_matrix: Matrix):
    verts = calculate_window_verts(window_xml)
    # verts = [(vert - child_matrix.translation) @ child_matrix
    #          for vert in verts]
    faces = [[0, 1, 2, 3]]

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.transform(Matrix.Translation(-child_matrix.translation))

    return mesh


def calculate_window_verts(window_xml: WindowItem):
    """Calculate the 4 vertices of the window from the projection matrix."""
    proj_mat = get_window_projection_matrix(window_xml)

    min = Vector((0, 0, 0))
    max = Vector((window_xml.width / 2, window_xml.height, 1))

    v0 = multiply_homogeneous(proj_mat, Vector((min.x, min.y, 0)))
    v1 = multiply_homogeneous(proj_mat, Vector((min.x, max.y, 0)))
    v2 = multiply_homogeneous(proj_mat, Vector((max.x, max.y, 0)))
    v3 = multiply_homogeneous(proj_mat, Vector((max.x, min.y, 0)))

    return v0, v1, v2, v3


def get_window_projection_matrix(window_xml: WindowItem):
    proj_mat: Matrix = window_xml.projection_matrix
    # proj_mat[3][3] is currently an unknown value so it is set to 1 (CW does the same)
    proj_mat[3][3] = 1

    return proj_mat.transposed().inverted_safe()


def get_rgb(value):
    if value == "##":
        return [0, 0, 0, 1]
    elif value == "--":
        return [1, 1, 1, 1]
    else:
        value = int(value, 16)
        return [value / 255, value / 255, value / 255, 1]


def shattermap_to_image(shattermap, name):
    width = int(len(shattermap[0]) / 2)
    height = int(len(shattermap))

    img = bpy.data.images.new(name, width, height)

    pixels = []
    i = 0
    for row in reversed(shattermap):
        frow = [row[x:x + 2] for x in range(0, len(row), 2)]
        for value in frow:
            pixels.append(get_rgb(value))
            i += 1

    pixels = [chan for px in pixels for chan in px]
    img.pixels = pixels
    return img


def shattermap_to_material(shattermap, name):
    img = shattermap_to_image(shattermap, name)
    return material_from_image(img, name, "ShatterMap")


def get_geometry_material(frag_xml: Fragment, materials: list[bpy.types.Material], geometry_index: int) -> Union[bpy.types.Material, None]:
    """Get the material that the given geometry uses."""
    for dmodel in frag_xml.drawable.drawable_models_high:
        geometries = dmodel.geometries

        if geometry_index > len(geometries):
            return None

        geometry = geometries[geometry_index]
        shader_index = geometry.shader_index

        if shader_index > len(materials):
            return None

        return materials[shader_index]


def set_fragment_properties(frag_xml: Fragment, frag_obj: bpy.types.Object):
    frag_obj.fragment_properties.unk_b0 = frag_xml.unknown_b0
    frag_obj.fragment_properties.unk_b8 = frag_xml.unknown_b8
    frag_obj.fragment_properties.unk_bc = frag_xml.unknown_bc
    frag_obj.fragment_properties.unk_c0 = frag_xml.unknown_c0
    frag_obj.fragment_properties.unk_c4 = frag_xml.unknown_c4
    frag_obj.fragment_properties.unk_cc = frag_xml.unknown_cc
    frag_obj.fragment_properties.gravity_factor = frag_xml.gravity_factor
    frag_obj.fragment_properties.buoyancy_factor = frag_xml.buoyancy_factor


def set_lod_properties(lod_xml: LODProperty, lod_props: LODProperties):
    lod_props.unknown_14 = lod_xml.unknown_14
    lod_props.unknown_18 = lod_xml.unknown_18
    lod_props.unknown_1c = lod_xml.unknown_1c
    lod_props.position_offset = lod_xml.position_offset
    lod_props.unknown_40 = lod_xml.unknown_40
    lod_props.unknown_50 = lod_xml.unknown_50
    lod_props.damping_linear_c = lod_xml.damping_linear_c
    lod_props.damping_linear_v = lod_xml.damping_linear_v
    lod_props.damping_linear_v2 = lod_xml.damping_linear_v2
    lod_props.damping_angular_c = lod_xml.damping_angular_c
    lod_props.damping_angular_v = lod_xml.damping_angular_v
    lod_props.damping_angular_v2 = lod_xml.damping_angular_v2
    # archetype properties
    lod_props.archetype_name = lod_xml.archetype.name
    lod_props.archetype_mass = lod_xml.archetype.mass
    lod_props.archetype_unknown_48 = lod_xml.archetype.unknown_48
    lod_props.archetype_unknown_4c = lod_xml.archetype.unknown_4c
    lod_props.archetype_unknown_50 = lod_xml.archetype.unknown_50
    lod_props.archetype_unknown_54 = lod_xml.archetype.unknown_54
    lod_props.archetype_inertia_tensor = lod_xml.archetype.inertia_tensor


def set_group_properties(group_xml: GroupItem, bone: bpy.types.Bone):
    bone.group_properties.name = group_xml.name
    bone.group_properties.glass_window_index = group_xml.glass_window_index
    bone.group_properties.glass_flags = group_xml.glass_flags
    bone.group_properties.strength = group_xml.strength
    bone.group_properties.force_transmission_scale_up = group_xml.force_transmission_scale_up
    bone.group_properties.force_transmission_scale_down = group_xml.force_transmission_scale_down
    bone.group_properties.joint_stiffness = group_xml.joint_stiffness
    bone.group_properties.min_soft_angle_1 = group_xml.min_soft_angle_1
    bone.group_properties.max_soft_angle_1 = group_xml.max_soft_angle_1
    bone.group_properties.max_soft_angle_2 = group_xml.max_soft_angle_2
    bone.group_properties.max_soft_angle_3 = group_xml.max_soft_angle_3
    bone.group_properties.rotation_speed = group_xml.rotation_speed
    bone.group_properties.rotation_strength = group_xml.rotation_strength
    bone.group_properties.restoring_max_torque = group_xml.restoring_max_torque
    bone.group_properties.latch_strength = group_xml.latch_strength
    bone.group_properties.min_damage_force = group_xml.min_damage_force
    bone.group_properties.damage_health = group_xml.damage_health
    bone.group_properties.unk_float_5c = group_xml.unk_float_5c
    bone.group_properties.unk_float_60 = group_xml.unk_float_60
    bone.group_properties.unk_float_64 = group_xml.unk_float_64
    bone.group_properties.unk_float_68 = group_xml.unk_float_68
    bone.group_properties.unk_float_6c = group_xml.unk_float_6c
    bone.group_properties.unk_float_70 = group_xml.unk_float_70
    bone.group_properties.unk_float_74 = group_xml.unk_float_74
    bone.group_properties.unk_float_78 = group_xml.unk_float_78
    bone.group_properties.unk_float_a8 = group_xml.unk_float_a8


def set_veh_window_properties(window_xml: WindowItem, window_obj: bpy.types.Object):
    window_obj.vehicle_window_properties.unk_float_17 = window_xml.unk_float_17
    window_obj.vehicle_window_properties.unk_float_18 = window_xml.unk_float_18
    window_obj.vehicle_window_properties.cracks_texture_tiling = window_xml.cracks_texture_tiling
