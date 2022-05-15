import bpy
from ...sollumz_object import CWXMLConverter
from ...sollumz_properties import SollumType
from ...cwxml import drawable as ydrxml


class LightCWXMLConverter(CWXMLConverter):
    """Converts Light CWXML objects to bpy objects."""
    XML_TYPE = ydrxml.LightItem
    SOLLUM_TYPE = SollumType.LIGHT

    def create_bpy_object(self) -> bpy.types.Object:
        pass
