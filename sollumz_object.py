"""Abstract classes for cwxml-bpy converters."""
from typing import TYPE_CHECKING, Union, Type, Generic, TypeVar

# Get type hinting for import/export ops without circular import
if TYPE_CHECKING:
    from .sollumz_operators import SOLLUMZ_OT_import, SOLLUMZ_OT_export

from abc import ABC as AbstractClass, abstractmethod
from enum import Enum

from .cwxml.element import Element
from .sollumz_properties import SollumType
from .tools.utils import get_file_name

import bpy

CwxmlType = TypeVar('CwxmlType', bound=Element)


class SollumzObject(AbstractClass, Generic[CwxmlType]):
    """Generic class for all Sollumz objects. Handles conversion between cwxml and bpy objects."""

    def __init__(self, cwxml: Union[CwxmlType, None] = None, bpy_object: Union[bpy.types.Object, None] = None):
        super().__init__()
        self.cwxml = cwxml
        self.bpy_object = bpy_object
        self.filepath: str = ""


class CWXMLConverter(SollumzObject[CwxmlType], AbstractClass):
    """Handles converting cwxml objects to bpy objects."""

    IMPORT_CWXML_TYPE: Type[Element]
    import_operator: Union[bpy.types.Operator, None]

    def __init__(self, cwxml: CwxmlType):
        super().__init__(cwxml=cwxml)

    @classmethod
    def bpy_from_xml_file(
        cls,
        filepath: str,
        import_operator: "SOLLUMZ_OT_import"
    ):
        """Create a bpy object from an xml file."""
        if not hasattr(cls, "IMPORT_CWXML_TYPE"):
            raise AttributeError(
                f'IMPORT_CWXML_TYPE must be defined in converter {cls.__name__} in order to load a xml file!')
        CWXMLConverter.import_operator = import_operator
        cwxml = cls.IMPORT_CWXML_TYPE.from_xml_file(filepath)
        converter = cls(cwxml)
        converter.filepath = filepath

        return converter.create_bpy_object(name=get_file_name(filepath))

    @abstractmethod
    def create_bpy_object(self, name: str = None) -> bpy.types.Object:
        """Create bpy object from self.cwxml."""
        raise NotImplementedError


class BPYConverter(SollumzObject):
    """Handles converting bpy objects to cwxml."""

    export_operator: Union[bpy.types.Operator, None] = None

    def __init__(self, bpy_object: bpy.types.Object):
        super().__init__(bpy_object=bpy_object)

    @classmethod
    def bpy_to_xml_file(
        cls, filepath: str, bpy_object: bpy.types.Object,
        export_operator: "SOLLUMZ_OT_export"
    ):
        """Write a bpy object as a cwxml file to filepath."""
        BPYConverter.export_operator = export_operator

        converter = cls(bpy_object)
        converter.filepath = filepath
        cwxml = converter.create_cwxml()
        cwxml.write_xml(filepath)

    @abstractmethod
    def create_cwxml(self) -> Element:
        """Create cwxml object from self.bpy_object."""
        raise NotImplementedError
