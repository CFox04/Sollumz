"""Abstract classes for cwxml-bpy converters."""
from os import PathLike
from typing import TYPE_CHECKING, Callable, Union, Generic, TypeVar

# Get type hinting for import/export ops without circular import
# https://stackoverflow.com/questions/39740632/python-type-hinting-without-cyclic-imports
if TYPE_CHECKING:
    from .sollumz_operators import SOLLUMZ_OT_import, SOLLUMZ_OT_export

from abc import ABC as AbstractClass, abstractmethod

from .sollumz_properties import SollumzExportSettings
from .cwxml.element import Element
from .tools.utils import get_file_name

import bpy

CwxmlType = TypeVar('CwxmlType', bound=Element)


class SollumzConverter(AbstractClass, Generic[CwxmlType]):
    """Generic class for all Sollumz objects. Handles conversion between cwxml and bpy objects."""

    def __init__(self, cwxml: Union[CwxmlType, None] = None, bpy_object: Union[bpy.types.Object, None] = None):
        super().__init__()
        self.cwxml = cwxml
        self.bpy_object = bpy_object
        self.filepath: str = ""


class CWXMLConverter(SollumzConverter[CwxmlType], AbstractClass):
    """Handles converting cwxml objects to bpy objects."""

    IMPORT_CWXML_FUNC: Callable[[PathLike], CwxmlType]
    import_operator: Union["SOLLUMZ_OT_import", None]

    def __init__(self, cwxml: CwxmlType):
        self.cwxml: CwxmlType
        super().__init__(cwxml=cwxml)

    @classmethod
    def bpy_from_xml_file(
        cls,
        filepath: str,
        import_operator: "SOLLUMZ_OT_import"
    ):
        """Create a bpy object from an xml file."""
        if not hasattr(cls, "IMPORT_CWXML_FUNC"):
            raise AttributeError(
                f'IMPORT_CWXML_FUNC must be defined in converter {cls.__name__} in order to load a xml file!')
        CWXMLConverter.import_operator = import_operator
        cwxml = cls.IMPORT_CWXML_FUNC(filepath)
        converter = cls(cwxml)
        converter.filepath = filepath

        return converter.create_bpy_object(name=get_file_name(filepath))

    @abstractmethod
    def create_bpy_object(self, name: str = None) -> bpy.types.Object:
        """Create bpy object from self.cwxml."""
        raise NotImplementedError


class BPYConverter(SollumzConverter[CwxmlType]):
    """Handles converting bpy objects to cwxml."""

    export_operator: Union["SOLLUMZ_OT_export", None]

    @property
    def export_settings(self) -> Union[SollumzExportSettings, None]:
        """Export settings of self.export_operator."""
        if self._export_settings is not None:
            return self._export_settings

        if self.export_operator is not None:
            self._export_settings = self.export_operator.export_settings
            return self._export_settings

    def __init__(self, bpy_object: bpy.types.Object):
        self.bpy_object: bpy.types.Object
        super().__init__(bpy_object=bpy_object)
        self._export_settings = None

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

        return cwxml

    @abstractmethod
    def create_cwxml(self) -> Element:
        """Create cwxml object from self.bpy_object."""
        raise NotImplementedError
