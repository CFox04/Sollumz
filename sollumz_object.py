"""Abstract classes for cwxml-bpy converters."""
from typing import TYPE_CHECKING

# Get type hinting for import/export ops without circular import
if TYPE_CHECKING:
    from .sollumz_operators import SOLLUMZ_OT_import, SOLLUMZ_OT_export

from abc import ABC as AbstractClass, abstractmethod
from typing import Union, Type
from enum import Enum

from .cwxml.element import Element
from .sollumz_properties import SollumType
from .tools.utils import get_file_name

import bpy


class SollumzObject(AbstractClass):
    """Generic class for all Sollumz objects. Handles conversion between cwxml and bpy objects."""
    BPY_TYPE = bpy.types.Object

    @property
    @abstractmethod
    def XML_TYPE(self) -> Type[Element]:
        raise NotImplementedError

    @property
    @abstractmethod
    def SOLLUM_TYPE(self) -> Union[SollumType, Enum]:
        raise NotImplementedError

    @property
    def cwxml(self) -> XML_TYPE:
        if self._cwxml is None:
            raise AttributeError(f"{self} has no cwxml object!")
        return self._cwxml

    @cwxml.setter
    def cwxml(self, new_cwxml):
        if not isinstance(new_cwxml, self.XML_TYPE):
            raise TypeError(
                f"Invalid cwxml type '{new_cwxml.__class__.__name__}', expected type '{self.XML_TYPE.__name__}'")

        self._cwxml = new_cwxml

    @property
    def bpy_object(self) -> bpy.types.Object:
        if self._bpy_object is None:
            raise AttributeError(f"{self} has no bpy object!")

        return self._bpy_object

    @bpy_object.setter
    def bpy_object(self, new_bpy_object):
        if not isinstance(new_bpy_object, self.BPY_TYPE):
            raise TypeError(
                f"{new_bpy_object} is not an instance of bpy.types.{self.BPY_TYPE.__name__}!")

        self._bpy_object = new_bpy_object

    def __init__(self, cwxml: Element = None, bpy_object: bpy.types.Object = None):
        super().__init__()
        if cwxml is not None:
            self.cwxml = cwxml
        else:
            self._cwxml = None
        if bpy_object is not None:
            self.bpy_object = bpy_object
        else:
            self._bpy_object = None

        self.filepath: str = ""


class CWXMLConverter(SollumzObject):
    """Handles converting cwxml to bpy objects."""
    XML_TYPE: Type[Element]

    _import_operator: Union[bpy.types.Operator, None] = None

    @property
    def import_operator(self) -> bpy.types.Operator:
        return CWXMLConverter._import_operator

    @import_operator.setter
    def import_operator(self, new_operator):
        CWXMLConverter._import_operator = new_operator

    def __init__(self, cwxml: Element):
        super().__init__(cwxml=cwxml)

    @classmethod
    def bpy_from_xml_file(
        cls,
        filepath: str,
        import_operator: "SOLLUMZ_OT_import"
    ):
        """Create a bpy object from an xml file."""
        CWXMLConverter._import_operator = import_operator

        cwxml = cls.XML_TYPE.from_xml_file(filepath)
        converter = cls(cwxml)
        converter.filepath = filepath

        return converter.create_bpy_object(name=get_file_name(filepath))

    @abstractmethod
    def create_bpy_object(self, name: str = None) -> bpy.types.Object:
        """Create bpy object from self.cwxml."""
        raise NotImplementedError


class BPYConverter(SollumzObject):
    """Handles converting bpy objects to cwxml."""
    SOLLUM_TYPE: Union[SollumType, Enum]

    _export_operator: Union[bpy.types.Operator, None] = None

    @property
    def export_operator(self) -> bpy.types.Operator:
        return BPYConverter._export_operator

    @export_operator.setter
    def export_operator(self, new_operator):
        BPYConverter._export_operator = new_operator

    def __init__(self, bpy_object: bpy.types.Object):
        super().__init__(bpy_object=bpy_object)

    @classmethod
    def bpy_to_xml_file(
        cls, filepath: str, bpy_object: bpy.types.Object,
        export_operator: "SOLLUMZ_OT_export"
    ):
        """Write a bpy object as a cwxml file to filepath."""
        BPYConverter._export_operator = export_operator

        converter = cls(bpy_object)
        converter.filepath = filepath
        cwxml = converter.create_cwxml()
        cwxml.write_xml(filepath)

    @abstractmethod
    def create_cwxml(self) -> Element:
        """Create cwxml object from self.bpy_object."""
        raise NotImplementedError
