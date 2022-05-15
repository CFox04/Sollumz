import bpy

from ...sollumz_object import CWXMLConverter
from ...sollumz_properties import SollumType
from ...tools.blenderhelper import create_sollumz_object, get_children_recursive
from ...cwxml import drawable as ydrxml
from ...cwxml.fragment import YFT
from ...sollumz_helper import find_fragment_file
from ...ydr.import_cwxml.drawable import DrawableCWXMLConverter


class DrawableDictionaryCWXMLConverter(CWXMLConverter):
    """Converts Drawable Dictionary CWXML objects to bpy objects."""
    XML_TYPE = ydrxml.DrawableDictionary
    SOLLUM_TYPE = SollumType.DRAWABLE_DICTIONARY

    def __init__(self, cwxml: ydrxml.DrawableDictionary, import_operator):
        self.cwxml: ydrxml.DrawableDictionary
        super().__init__(cwxml, import_operator)
        self.skeleton: ydrxml.SkeletonProperty = ydrxml.SkeletonProperty()
        self.armature: bpy.types.Object = None

    def create_bpy_object(self, name: str) -> bpy.types.Object:
        self.bpy_object = create_sollumz_object(self.SOLLUM_TYPE)
        self.bpy_object.name = name

        if self.import_operator.import_settings.import_ext_skeleton:
            self.load_external_skeleton()
        else:
            self.find_and_load_skeleton()

        self.create_drawables()

        if self.armature:
            self.set_armature_modifiers()

    def load_external_skeleton(self):
        """Load external skeleton from a .yft.xml file located at this xml's filepath."""
        skel_filepath = find_fragment_file(self.filepath)

        if skel_filepath:
            yft = YFT.from_xml_file(skel_filepath)
            for drawable in self.cwxml:
                drawable.skeleton = yft.drawable.skeleton
        else:
            self.import_operator.report(
                {"WARNING", f"No external skeleton file found at path {self.filepath}."})

    def find_and_load_skeleton(self):
        """Find the first drawable with a skeleton and set it as the skeleton for this ydd."""
        drawable: ydrxml.Drawable

        for drawable in self.cwxml:
            if drawable.skeleton.bones:
                self.skeleton = drawable.skeleton
                break

    def set_armature_modifiers(self):
        """Create armature modifiers (if one does not exist) and set the linked
        object to the drawable that contains the skeleton."""
        for child in get_children_recursive(self.bpy_object):
            if child.sollum_type == SollumType.DRAWABLE_GEOMETRY:
                modifier = child.modifiers.get("Armature")
                if modifier is None:
                    modifier = child.modifiers.new("Armature", "ARMATURE")
                modifier.object = self.armature

    def create_drawables(self):
        """Create the drawable bpy objects under this ydd."""
        drawable: ydrxml.Drawable
        for drawable in self.cwxml:
            drawable_obj = DrawableCWXMLConverter(
                drawable, self.import_operator, self.skeleton.bones).create_bpy_object(drawable.name)

            if drawable.skeleton == self.skeleton:
                self.armature = drawable_obj

            drawable_obj.parent = self.bpy_object
