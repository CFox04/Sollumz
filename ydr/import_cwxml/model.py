from itertools import chain
import bpy
from typing import NamedTuple, Union

from ...cwxml.drawable import DrawableModelItem, GeometryItem, BoneItem
from ...sollumz_converter import CWXMLConverter
from ...sollumz_properties import LODLevel, SollumType, SOLLUMZ_UI_NAMES
from ...tools.meshhelper import create_uv_layer, create_vertexcolor_layer
from ...tools.blenderhelper import create_sollumz_object
from ..shader_materials import create_tinted_shader_graph


class VertexComponents(NamedTuple):
    positions: list[tuple]
    normals: list[tuple]
    uv_map: dict[str, list[tuple[float, float]]]
    color_map: dict[str, list[tuple[float, float]]]
    vertex_groups: dict[int, list[tuple[float, float]]]

    @classmethod
    def from_vertices(cls, vertices: list[tuple]):
        """Split vertex buffer into separate componenets."""
        positions = []
        normals = []
        uv_map = {}
        color_map = {}
        vertex_groups = {}

        for vertex_index, vertex in enumerate(vertices):
            positions.append(vertex.position)

            # Vertex layouts differ, so we have to check if a given vertex has the desired attribute
            if hasattr(vertex, "normal"):
                normals.append(vertex.normal)

            if hasattr(vertex, "blendweights"):
                for i in range(0, 4):
                    weight = vertex.blendweights[i] / 255

                    bone_index = vertex.blendindices[i]
                    if bone_index not in vertex_groups:
                        vertex_groups[bone_index] = []

                    vertex_groups[bone_index].append((vertex_index, weight))

            for key, value in vertex._asdict().items():
                if "texcoord" in key:
                    if not key in uv_map.keys():
                        uv_map[key] = []
                    uv_map[key].append(tuple(value))
                if "colour" in key:
                    if not key in color_map.keys():
                        color_map[key] = []
                    color_map[key].append(tuple(value))

        return cls(positions, normals, uv_map, color_map, vertex_groups)


class ModelMeshCWXMLConverter(CWXMLConverter[DrawableModelItem]):
    """Converts Drawable Model CWXML objects to bpy objects."""

    def __init__(self, cwxml: DrawableModelItem, lod_level: LODLevel, materials: list[bpy.types.Material], bones: Union[list[BoneItem], None] = None):
        super().__init__(cwxml)
        self.lod_level = lod_level
        self.vertex_components: VertexComponents = {}
        self.vertices: list[tuple] = {}
        self.polygons: list[tuple] = []
        self.poly_materials: dict[int, list[int]] = {}
        self.mesh: Union[bpy.types.Mesh, None] = None
        self.materials = materials
        self.bones = bones

    @classmethod
    def create_model_object(cls, drawable_name: str, models: list[DrawableModelItem], materials: list[bpy.types.Material], bones: Union[list[BoneItem], None] = None):
        """Create a single Drawable Model object from a list of Drawable Model cwxmls"""
        model_object = None

        for lod_level, model_cwxml in models.items():
            mesh = cls(model_cwxml, lod_level, materials,
                       bones).create_bpy_object(drawable_name)

            if model_object is None:
                model_object = create_sollumz_object(
                    SollumType.DRAWABLE_MODEL, mesh, name=f"{drawable_name}_model")
                model_object.sollumz_active_lod = lod_level
                model_object.drawable_model_properties.render_mask = model_cwxml.render_mask
                model_object.drawable_model_properties.unknown_1 = model_cwxml.unknown_1
                model_object.drawable_model_properties.flags = model_cwxml.flags

            model_object.sollumz_lod_meshes[lod_level] = mesh

        create_tinted_shader_graph(model_object)

        return model_object

    def create_bpy_object(self, drawable_name: str) -> bpy.types.Object:
        """Create a mesh data-block for this drawable model."""
        lod_name = SOLLUMZ_UI_NAMES[self.lod_level]
        mesh_name = f"{drawable_name}_{lod_name}".lower()

        if not self.cwxml.geometries:
            self.import_operator.report(
                {"WARNING"}, f"Failed to create mesh for Drawable Model {mesh_name}: Model has no geometries!")
            return

        self.get_vertices_polygons()
        self.vertex_components = VertexComponents.from_vertices(self.vertices)

        # Editing mesh data-block before assigning it to an object is a lot quicker for some reason
        mesh = self.create_mesh(mesh_name)

        # Create a temporary object in which the vertex groups and
        temp_object = bpy.data.objects.new("temp", mesh)
        self.bpy_object = temp_object

        if self.bones:
            self.create_vertex_groups()
            self.set_geometry_weights()

        # if self.materials:
        #     create_tinted_shader_graph(temp_object)

        self.bpy_object = temp_object.data
        bpy.data.objects.remove(temp_object)

        return self.bpy_object

    def get_vertices_polygons(self):
        """Get all self.vertices, self.polygons, and self.poly_materials
        for this Drawable Model."""
        all_vertices = []
        all_polygons = []
        # Map polygon indices by shader index
        poly_materials = {}

        for i, geometry_cwxml in enumerate(self.cwxml.geometries):
            vertices = geometry_cwxml.vertex_buffer.get_data()
            indices = geometry_cwxml.index_buffer.data
            shader_index = geometry_cwxml.shader_index

            if i > 0:
                indices = [
                    vert_index + len(all_vertices) for vert_index in indices]

            if shader_index not in poly_materials:
                poly_materials[shader_index] = []

            polygons = [indices[i:i + 3] for i in range(0, len(indices), 3)]
            poly_indices = [i for i in range(
                len(all_polygons), len(polygons) + len(all_polygons))]

            poly_materials[shader_index].extend(poly_indices)

            all_vertices.extend(vertices)
            all_polygons.extend(polygons)

        self.vertices = all_vertices
        self.polygons = all_polygons
        self.poly_materials = poly_materials

        return all_vertices, all_polygons

    def create_mesh(self, name: str) -> bpy.types.Mesh:
        """Create the mesh data-block for this geometry."""

        mesh: bpy.types.Mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertex_components.positions, [], self.polygons)
        mesh.validate()

        self.mesh = mesh

        self.create_materials()
        self.set_smooth_normals()

        self.create_uv_layers()
        self.create_vertex_color_layers()

        return mesh

    def create_materials(self):
        """Create materials and set material indices accordingly."""
        if not self.materials:
            return

        for shader_index, polygons in self.poly_materials.items():

            if not 0 <= shader_index < len(self.materials):
                self.import_operator.report(
                    {"WARNING"}, f"Material not set for {self.mesh}. Shader index of {shader_index} not found!")
                continue

            self.mesh.materials.append(self.materials[shader_index])

            new_shader_index = len(self.mesh.materials) - 1

            for poly_index in polygons:
                poly = self.mesh.polygons[poly_index]
                poly.material_index = new_shader_index

    def set_smooth_normals(self):
        """Set the normals of this geometry and smooth them."""
        self.mesh.polygons.foreach_set(
            "use_smooth", [True] * len(self.mesh.polygons))
        self.mesh.normals_split_custom_set_from_vertices(
            self.vertex_components.normals)
        self.mesh.use_auto_smooth = True

    def create_uv_layers(self):
        """Create all uv layers for this geometry."""
        for i, (name, coords) in enumerate(self.vertex_components.uv_map.items()):
            create_uv_layer(self.mesh, i, name, coords)
            # print(i, len(self.mesh.uv_layers[i].data), len(coords))

    def create_vertex_color_layers(self):
        """Create all vertex color layers for this geometry."""
        for i, (name, coords) in enumerate(self.vertex_components.color_map.items()):
            create_vertexcolor_layer(self.mesh, i, name, coords)

    def create_vertex_groups(self):
        """Create vertex groups for this geometry based on the number
        of bones present in the drawable skeleton."""

        # Some drawables have weights defined, but no associated bones (just the bone indices).
        # This is common in mp clothing, where the weights are defined, but the bone
        # indices index the bones on the mp skeleton (which has to be acquired externally).
        # These weights will still be imported, but under the name "EXTERNAL_BONE". This will
        # allow the remaining bones to be acquired later if need be.
        bones = self.bones
        bone_ids = self.cwxml.geometries[0].bone_ids
        bpy_vertex_groups = self.bpy_object.vertex_groups

        for bone_index in self.vertex_components.vertex_groups.keys():
            bone_name = "UNKNOWN_BONE"

            if bones and bone_index < len(bones):
                bone_name = bones[bone_index].name
            elif bone_ids and bone_index < len(bone_ids):
                bone_name = f"EXTERNAL_BONE.{bone_index}"

            bpy_vertex_groups.new(name=bone_name)

    def set_geometry_weights(self):
        """Set weights for this geometry."""
        for i, vertex_group in enumerate(self.vertex_components.vertex_groups.values()):
            for vertex_index, weight in vertex_group:
                self.bpy_object.vertex_groups[i].add(
                    [vertex_index], weight, "ADD")
