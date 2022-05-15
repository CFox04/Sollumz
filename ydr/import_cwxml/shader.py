import os
from typing import Union
import bpy

from ...cwxml import drawable as ydrxml
from ...cwxml.shader import ShaderManager
from ...sollumz_object import CWXMLConverter
from ...sollumz_properties import MaterialType, TextureFormat, TextureUsage
from .. import shader_materials as shader_nodes
from ...tools.utils import get_file_name


class ShaderCWXMLConverter(CWXMLConverter):
    """Coverts CWXML shaders into bpy materials."""
    XML_TYPE = ydrxml.ShaderItem
    SOLLUM_TYPE = MaterialType.SHADER
    BPY_TYPE = bpy.types.Material

    def __init__(
        self, cwxml: ydrxml.ShaderItem,
        import_operator, filepath: str,
        texture_dictionary: list[ydrxml.TextureItem]
    ):
        self.cwxml: ydrxml.ShaderItem
        self.bpy_object: bpy.types.Material

        super().__init__(cwxml, import_operator)

        self.filepath = filepath
        self.texture_dictionary = texture_dictionary

    def create_bpy_object(self) -> bpy.types.Material:
        filename = self.cwxml.filename

        material = bpy.data.materials.new(self.cwxml.name)
        self.bpy_object = material
        self.set_material_properties()

        if self.cwxml.filename in ShaderManager.terrains:
            shader_nodes.create_terrain_shader(material, self.cwxml, filename)
        else:
            shader_nodes.create_basic_shader_nodes(
                material, self.cwxml, filename)

        shader_nodes.organize_node_tree(material.node_tree)

        param: ydrxml.ShaderParameter
        for param in self.cwxml.parameters:
            for node in material.node_tree.nodes:
                if isinstance(node, bpy.types.ShaderNodeTexImage) and param.name == node.name:
                    self.load_image_texture(node, param)
                    self.set_embedded_texture_properties(node)
                elif isinstance(node, bpy.types.ShaderNodeValue):
                    # Check if param name is equal to the node name without the _xyz suffix
                    if param.name == node.name[:-2]:
                        ShaderCWXMLConverter.set_value_node_properties(
                            node, param)

        self.assign_extra_detail_node()

        return material

    def set_material_properties(self):
        """Set the properties of this shader to that of the cwxml shader."""
        material = self.bpy_object
        shader = self.cwxml

        material.use_nodes = True
        material.sollum_type = MaterialType.SHADER

        material.shader_properties.name = shader.name
        material.shader_properties.filename = shader.filename
        material.shader_properties.renderbucket = shader.render_bucket

    def load_image_texture(self, node: bpy.types.ShaderNodeTexImage, param: ydrxml.TextureShaderParameter):
        """Load image texture for node based on the cwxml texture shader parameter given."""
        image = bpy.data.images.get(param.texture_name)

        if image is None:
            image = self.load_image(param.texture_name)

        if image is None:
            image = ShaderCWXMLConverter.create_blank_image(param.texture_name)

        node.image = image

        # Normal maps need non-color colorspace
        # https://docs.blender.org/manual/en/latest/render/color_management.html#image-color-spaces
        if "Bump" in param.name:
            node.image.colorspace_settings.name = "Non-Color"

    def load_image(self, texture_name: str) -> Union[bpy.types.Image, None]:
        """Attempt to load a .dds image with texture_name from this shader group's texture
        folder. If a .dds file is found a bpy image will be returned, otherwise None will be
        returned."""
        texture_folder = self.get_texture_folder()

        if not texture_folder:
            return

        texture_path = os.path.join(
            texture_folder, texture_name + ".dds")

        if os.path.isfile(texture_path):
            bpy_image = bpy.data.images.load(
                texture_path, check_existing=True)
            bpy_image.name = texture_name
            return bpy_image

        return None

    def get_texture_folder(self):
        """Get texture folder path from the filepath of this shader group's drawable."""
        file_name = get_file_name(self.filepath)
        texture_folder = f"{os.path.dirname(self.filepath)}\\{file_name}"

        if os.path.exists(texture_folder):
            return texture_folder

    def set_embedded_texture_properties(self, node: bpy.types.ShaderNodeTexImage):
        """Set embedded texture properties for node based on self.texture_dictionary."""
        for texture in self.texture_dictionary:
            if texture.name == node.name:
                node.texture_properties.embedded = True
                try:
                    format = TextureFormat[texture.format.replace(
                        "D3DFMT_", "")]
                    node.texture_properties.format = format
                except AttributeError:
                    self.import_operator.report(
                        {"WARNING"}, f"Failed to set texture format for texture '{texture.name}': format '{texture.format}' unknown.")

                try:
                    usage = TextureUsage[texture.usage]
                    node.texture_properties.usage = usage
                except AttributeError:
                    self.import_operator.report(
                        {"WARNING"}, f"Failed to set texture usage for texture '{texture.name}': usage '{texture.usage}' unknown.")

                node.texture_properties.extra_flags = texture.extra_flags
                ShaderCWXMLConverter.set_texture_usage_flags(node, texture)

        if not node.texture_properties.embedded:
            # Set external texture name for non-embedded textures
            node.image.source = "FILE"
            node.image.filepath = "//" + node.image.name + ".dds"

    def assign_extra_detail_node(self):
        """Assign extra detail node sampler image for viewing."""
        dtl_ext = shader_nodes.get_detail_extra_sampler(self.bpy_object)
        if dtl_ext:
            dtl = self.bpy_object.node_tree.nodes["DetailSampler"]
            dtl_ext.image = dtl.image

    @staticmethod
    def find_existing_image(texture_name: str) -> Union[bpy.types.Image, None]:
        """Attempts to find existing image with texture_name in the blend file.
        If found, the image will be returned, otherwise None will be returned."""
        existing_texture = bpy.data.images.get(texture_name)

        for image in bpy.data.images:
            if image.name == texture_name:
                existing_texture = image

        return existing_texture

    @staticmethod
    def create_blank_image(name: str) -> bpy.types.Image:
        """Create a blank 512x512 bpy image with the given name."""
        return bpy.data.images.new(name=name, width=512, height=512)

    @staticmethod
    def set_value_node_properties(node: bpy.types.ShaderNodeValue, param: ydrxml.VectorShaderParameter):
        axis = node.name[-1]
        node.outputs[0].default_value = getattr(param, axis)

    @staticmethod
    def set_texture_usage_flags(node: bpy.types.ShaderNodeTexImage, texture: ydrxml.TextureItem):
        """Set usage flags for embedded texture."""
        for flag_bpy in dir(node.texture_flags):
            for flag_cwxml in texture.usage_flags:
                if flag_cwxml.lower() == flag_bpy:
                    setattr(
                        node.texture_flags, flag_bpy, True)
