import bpy
from ...sollumz_object import CWXMLConverter
from ...sollumz_properties import SollumType
from ...cwxml import drawable as ydrxml


class LightCWXMLConverter(CWXMLConverter[ydrxml.LightItem]):
    """Converts Light CWXML objects to bpy objects."""

    def create_bpy_object(self) -> bpy.types.Object:
        pass
