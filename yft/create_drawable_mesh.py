import bpy
from typing import Dict, NamedTuple
from collections import defaultdict
from ..tools.blenderhelper import create_mesh_object
from ..cwxml.drawable import GeometryItem, Drawable, BoneItem
from ..sollumz_properties import LODLevel, SollumType, SOLLUMZ_UI_NAMES
from .geometry_data import GeometryData, VertexAttributes
from .properties import LODLevels
from .. import logger

LODsByGroup = Dict[str, dict[LODLevel, GeometryData]]
GeomDataByBone = Dict[int, dict[LODLevel, GeometryData]]
GeomsByBone = Dict[int, dict[LODLevel, list[GeometryItem]]]


def create_drawable_mesh(drawable_xml: Drawable, materials: list[bpy.types.Material], armature_obj: bpy.types.Object, parent_obj: bpy.types.Object, split_by_group=False):
    """Create fragment mesh joining all skinned geometries. Any non-skinned meshes will be split and parented to their corresponding bone. Returns all mesh objects."""
    bones: list[BoneItem] = drawable_xml.skeleton.bones

    if not bones:
        joined_geom = create_joined_mesh(
            drawable_xml, materials, armature_obj, parent_obj)
        return [joined_geom]

    skinned_geoms: list[bpy.types.Object] = []

    if split_by_group:
        skinned_geoms = create_split_drawable_mesh(
            drawable_xml, materials, armature_obj, parent_obj)
    else:
        skinned_geoms = create_skinned_drawable_mesh(
            drawable_xml, materials, armature_obj, parent_obj)

    non_skinned_geoms = create_non_skinned_drawable_mesh(
        drawable_xml, materials, armature_obj, parent_obj)

    return skinned_geoms + non_skinned_geoms


def create_joined_mesh(drawable_xml: Drawable, materials: list[bpy.types.Material], armature_obj: bpy.types.Object, parent_obj: bpy.types.Object):
    """Create a joined mesh from the drawable. This will break any rigging, so only use on drawables with no skeleton."""
    geometry_data_by_lod = get_joined_geometry_data(drawable_xml)
    name = f"{armature_obj.name}.mesh_object"
    bones: list[BoneItem] = drawable_xml.skeleton.bones

    geom = create_drawable_geometry(
        name, geometry_data_by_lod, materials, bones)
    geom.parent = parent_obj

    return geom


def ensure_bones(func):
    """Decorator to ensure drawable has bones and warn if not. Function must take in drawable_xml as first argument."""
    def inner(drawable_xml: Drawable, *args):
        if not drawable_xml.skeleton.bones:
            logger.warning(
                f"Cannot create a rigged mesh from drawable '{drawable_xml.name}': Drawable contains no bones! Aborting...")
            return
        return func(drawable_xml, *args)

    return inner


@ensure_bones
def create_skinned_drawable_mesh(drawable_xml: Drawable, materials: list[bpy.types.Material], armature_obj: bpy.types.Object, parent_obj: bpy.types.Object):
    """Create the skinned portion of the mesh (parts of mesh with vertex groups)."""
    bones: list[BoneItem] = drawable_xml.skeleton.bones

    skinned_geometry_data = get_joined_geometry_data(
        drawable_xml, only_skinned=True)
    geom = create_drawable_geometry(
        bones[0].name, skinned_geometry_data, materials, bones)
    geom.parent = parent_obj
    add_armature_modifier(geom, armature_obj)

    return geom


@ensure_bones
def create_split_drawable_mesh(drawable_xml: Drawable, materials: list[bpy.types.Material], armature_obj: bpy.types.Object, parent_obj: bpy.types.Object):
    """Create skinned portion of mesh split by vertex groups."""
    grouped_geometry_data = get_split_geom_data(drawable_xml)
    bones: list[BoneItem] = drawable_xml.skeleton.bones

    geoms: list[bpy.types.Object] = []

    for name, data_by_lod in grouped_geometry_data.items():
        geom = create_drawable_geometry(name, data_by_lod, materials, bones)
        geom.parent = parent_obj
        add_armature_modifier(geom, armature_obj)

        geoms.append(geom)

    return geoms


@ensure_bones
def create_non_skinned_drawable_mesh(drawable_xml: Drawable, materials: list[bpy.types.Material], armature_obj: bpy.types.Object, parent_obj: bpy.types.Object):
    """Create the non skinned parts of the fragment mesh. These objects are separated by drawable model so they can be parented to their bone."""
    non_skinned_geometry_data = create_non_skinned_geometry_data(
        drawable_xml)
    bones: list[BoneItem] = drawable_xml.skeleton.bones

    geoms: list[bpy.types.Object] = []

    for bone_index, data_by_lod in non_skinned_geometry_data.items():
        bone_name = bones[bone_index].name
        geom = create_drawable_geometry(
            bone_name, data_by_lod, materials, bones)
        geom.parent = parent_obj
        add_armature_constraint(geom, armature_obj, bone_name)

        geoms.append(geom)

    return geoms


def create_drawable_geometry(name: str, geometry_data_by_lod: dict[LODLevel, GeometryData], materials: list[bpy.types.Material], bones: list[BoneItem]):
    geom: bpy.types.Object = create_mesh_object(SollumType.FRAG_GEOM, name)
    lod_levels: LODLevels = geom.sollumz_object_lods
    original_mesh = geom.data

    lod_levels.add_empty_lods()

    for lod_level, geometry_data in geometry_data_by_lod.items():
        mesh_name = f"{name}_{SOLLUMZ_UI_NAMES[lod_level].lower().replace(' ', '_')}"
        lod_mesh = geometry_data.create_geometry_mesh(mesh_name, materials)

        lod_levels.set_lod_mesh(lod_level, lod_mesh)
        lod_levels.set_active_lod(lod_level)

        geometry_data.create_vertex_groups(geom, bones)

    lod_levels.set_active_lod(LODLevel.HIGH)

    if geom.data != original_mesh:
        bpy.data.meshes.remove(original_mesh)

    return geom


def group_geometries_by_lod(drawable: Drawable, only_skinned=False):
    geometries_by_lod: dict[LODLevel, list[GeometryItem]] = defaultdict(list)

    for lod_level, models in zip(LODLevel, drawable.model_groups):
        for model in models:
            if model.has_skin == 0 and only_skinned:
                continue
            geometries_by_lod[lod_level].extend(model.geometries)

    return geometries_by_lod


def get_joined_geometry_data(drawable: Drawable, only_skinned=False):
    """Joins all drawable geometries into one GeometryData object"""
    grouped_geometry_data: dict[LODLevel, GeometryData] = {}
    geometries_by_lod = group_geometries_by_lod(drawable, only_skinned)

    for lod_level, geometries in geometries_by_lod.items():
        geom_data = join_geometries(geometries)
        grouped_geometry_data[lod_level] = geom_data

    return grouped_geometry_data


def join_geometries(geometries: list[GeometryItem]):
    """Joins all geometries into one GeometryData object."""
    verts_by_shader, ind_by_shader = get_vertex_data_by_shader_index(
        geometries)
    geom_data = GeometryData()

    for shader_index, indices in ind_by_shader.items():
        num_verts = len(geom_data.vertices)

        for face in split_indices(indices):
            geom_data.faces.append([i + num_verts for i in face])
            geom_data.material_indices.append(shader_index)

        for vertex in verts_by_shader[shader_index]:
            geom_data.add_vertex(VertexAttributes.from_vertex(vertex))

    return geom_data


def get_split_geom_data(drawable: Drawable):
    """Returns a map of group names to the LOD meshes of each group."""
    lods_by_group: LODsByGroup = defaultdict(dict)
    geometries_by_lod = group_geometries_by_lod(drawable, only_skinned=True)
    bones: list[BoneItem] = drawable.skeleton.bones

    if not bones:
        return {}

    group_parent_map = get_group_parent_map(
        geometries_by_lod[LODLevel.HIGH], drawable.skeleton.bones)

    for lod_level, geometries in geometries_by_lod.items():
        geometry_data_by_group = create_grouped_geometry_data(
            geometries, bones, group_parent_map)

        for group_name, geometry_data in geometry_data_by_group.items():
            lods_by_group[group_name][lod_level] = geometry_data

    return lods_by_group


def create_non_skinned_geometry_data(drawable: Drawable):
    """Create geometry data for all non-skinned geometries. Returns a mapping of bone_index: lod_level: geometry_data"""
    geom_data_by_model: GeomsByBone = defaultdict(dict)
    geoms_by_bone_ind = get_geometries_by_bone_ind(drawable)

    for bone_index, lods in geoms_by_bone_ind.items():
        for lod_level, geometries in lods.items():
            geom_data = join_geometries(geometries)
            geom_data_by_model[bone_index][lod_level] = geom_data

    return geom_data_by_model


def get_geometries_by_bone_ind(drawable: Drawable):
    """Maps non-skinned geometries to corresponding bone indices."""
    geoms_by_bone_ind: GeomsByBone = defaultdict(
        lambda: defaultdict(list))

    if not drawable.skeleton.bones:
        return {}

    for lod_level, models in zip(LODLevel, drawable.model_groups):
        for model in models:
            if model.has_skin == 1:
                continue
            geoms_by_bone_ind[model.bone_index][lod_level].extend(
                model.geometries)

    return geoms_by_bone_ind


def create_grouped_geometry_data(geometries: list[GeometryItem], bones: list[BoneItem], group_parent_map: dict[int, int]):
    """Maps geometry data from a list of geometries by vertex group."""
    verts_by_shader, ind_by_shader = get_vertex_data_by_shader_index(
        geometries)
    geom_data_by_group: dict[str, GeometryData] = defaultdict(GeometryData)

    for shader_index, indices in ind_by_shader.items():
        verts_by_group, ind_by_group = get_vertex_data_by_group(
            indices, verts_by_shader[shader_index], bones, group_parent_map)

        for group_name, verts in verts_by_group.items():
            geom_data = geom_data_by_group[group_name]
            num_verts = len(geom_data.vertices)

            for face in split_indices(ind_by_group[group_name]):
                geom_data.faces.append([i + num_verts for i in face])
                geom_data.material_indices.append(shader_index)

            for vert_attrs in verts:
                geom_data.add_vertex(vert_attrs)

    return geom_data_by_group


def get_vertex_data_by_shader_index(geometries: list[GeometryItem]):
    """Returns the vertices and indices of the given geometries mapped by shader index."""
    verts_by_shader: dict[int, list[tuple]] = defaultdict(list)
    ind_by_shader: dict[int, list[int]] = defaultdict(list)

    for i, geometry in enumerate(geometries):
        vertex_data = geometry.vertex_buffer.get_data()
        index_data = geometry.index_buffer.data
        shader_index = geometry.shader_index

        if i > 0:
            index_data = [
                vert_index + len(verts_by_shader[shader_index]) for vert_index in index_data]

        verts_by_shader[shader_index].extend(vertex_data)
        ind_by_shader[shader_index].extend(index_data)

    return verts_by_shader, ind_by_shader


def get_joined_vertex_data(geometries: list[GeometryItem]):
    """Returns list of vertices and indices. (vertices, indices)"""
    vertices: list[VertexAttributes] = []
    indices: list[int] = []

    for geometry in geometries:
        for vert_index in geometry.index_buffer.data:
            indices.append(vert_index + len(vertices))

        for vert in geometry.vertex_buffer.get_data():
            vertices.append(VertexAttributes.from_vertex(vert))

    return vertices, indices


def get_group_parent_map(geometries: list[GeometryItem], bones: list[BoneItem]):
    """Get the vertex group indices that share the same vertices."""
    vertices, indices = get_joined_vertex_data(geometries)
    faces = split_indices(indices)

    group_by_face: dict[GeometryData.Face, int] = {}
    parent_map: dict[int, int] = {}

    # Map groups to all groups sharing faces
    group_relations: dict[int, list[int]] = defaultdict(list)

    for face in faces:
        for i in face:
            vert_attrs = vertices[i]

            for bone_index in vert_attrs.weights:
                if face not in group_by_face:
                    group_by_face[face] = bone_index
                    continue

                if group_by_face[face] == bone_index:
                    continue

                if group_by_face[face] in group_relations[bone_index]:
                    continue

                group_relations[bone_index].append(group_by_face[face])

    # Find common parents of all related bones
    for bone_index, related_bones in group_relations.items():
        parent_map[bone_index] = find_common_root_bone_parent(
            related_bones, bones)

    return parent_map


def find_common_root_bone_parent(bone_indices: list[int], bones: list[BoneItem]):
    """Find common bone parent of specified bones that is a child of the root bone. If none is found, the root bone is returned."""
    last_root_parent_index = -1

    for bone_index in bone_indices:
        root_parent_index = get_root_bone_parent_index(bone_index, bones)

        if last_root_parent_index == -1:
            last_root_parent_index = root_parent_index
            continue

        if last_root_parent_index != root_parent_index:
            return 0

    return root_parent_index


def get_root_bone_parent_index(bone_index: int, bones: list[BoneItem]) -> int:
    """Get parent of bone that is directly under the root bone."""
    i = bone_index

    while bones[i].parent_index > 0:
        i = bones[i].parent_index

    return i


def get_vertex_data_by_group(indices: list[int], vertices: list[NamedTuple], bones: list[BoneItem], group_parent_map: dict[int, int] = None):
    """Returns the given indices and vertices mapped by vertex group."""
    ind_by_group: dict[str, list[int]] = defaultdict(list)
    verts_by_group: dict[str, list[VertexAttributes]] = defaultdict(list)

    # Maps old vertex indices to new vertex indices
    vert_indices: dict[str, dict[int, int]] = defaultdict(dict)

    group_parent_map = group_parent_map or {}

    for i in indices:
        vert_attrs = VertexAttributes.from_vertex(vertices[i])

        group_name = get_object_group_name(
            vert_attrs, bones, group_parent_map)

        if i not in vert_indices[group_name]:
            group_verts = verts_by_group[group_name]

            group_verts.append(vert_attrs)
            new_vert_index = len(group_verts) - 1

            vert_indices[group_name][i] = new_vert_index

        ind_by_group[group_name].append(vert_indices[group_name][i])

    return verts_by_group, ind_by_group


def get_object_group_name(vert_attrs: VertexAttributes, bones: list[BoneItem], group_parent_map: dict[int, int]):
    """Get the name of the object group that the vertex belongs to. This will just be the vertex group name unless
    the vertex is used in multiple vertex groups in which case the parent vertex group is used."""
    if group_parent_map:
        for bone_index in vert_attrs.weights:
            if bone_index not in group_parent_map:
                continue

            parent_index = group_parent_map[bone_index]

            return bones[parent_index].name

    first_bone_index = list(vert_attrs.weights.keys())[0]

    return bones[first_bone_index].name


def add_armature_modifier(obj: bpy.types.Object, armature_obj: bpy.types.Object):
    mod: bpy.types.ArmatureModifier = obj.modifiers.new("skel", "ARMATURE")
    mod.object = armature_obj

    return mod


def add_armature_constraint(obj: bpy.types.Object, armature_obj: bpy.types.Object, target_bone: str, set_transforms=True):
    """Add armature constraint that is used for bone parenting on non-skinned objects."""
    constraint: bpy.types.ArmatureConstraint = obj.constraints.new("ARMATURE")
    target = constraint.targets.new()
    target.target = armature_obj
    target.subtarget = target_bone

    if not set_transforms:
        return

    bone = armature_obj.data.bones[target_bone]
    obj.matrix_local = bone.matrix_local


def split_indices(indices: list[int]) -> list[tuple[int, int, int]]:
    """Split list of indices into groups of 3."""
    return (tuple(indices[i:i + 3]) for i in range(0, len(indices), 3))
