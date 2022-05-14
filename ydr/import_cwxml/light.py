import bpy
from ...sollumz_converter import CWXMLConverter
from ...cwxml import drawable as ydrxml
from ..ydrimport import create_lights


class LightCWXMLConverter(CWXMLConverter[ydrxml.LightItem]):
    """Converts Light CWXML objects to bpy objects."""

    def create_bpy_object(self, parent: bpy.types.Object, armature_obj: bpy.types.Object = None) -> bpy.types.Object:
        # TODO: Lights rewrite
        create_lights(self.cwxml, parent, armature_obj)
