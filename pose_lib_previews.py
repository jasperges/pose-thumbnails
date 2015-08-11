if "bpy" in locals():
    import importlib
    if "prefs" in locals():
        importlib.reload(prefs)
else:
    from . import prefs


import os
import re
import bpy
from bpy.props import (StringProperty,
                       BoolProperty,
                       EnumProperty)
import bpy.utils.previews


# Dict to hold the ui previews collection
preview_collections = {}


# create th previews and an enum with label, tooltip and preview as custom icon
def generate_previews(self, context):
    enum_items = []

    if context is None:
        return enum_items

    obj = self
    pose_lib = obj.pose_library
    directory = pose_lib.pose_previews_dir

    pcoll = preview_collections["pose_previews"]

    if not obj.pose_previews_refresh:
        if directory == pcoll.pose_previews_dir:
            return pcoll.pose_previews

    num_pose_markers = len(pose_lib.pose_markers)

    if directory and os.path.isdir(bpy.path.abspath(directory)):
        if pcoll:
            pcoll.clear()
        image_paths = []
        for fn in os.listdir(bpy.path.abspath(directory)):
            if os.path.splitext(fn)[-1].lower() == ".png":
                image_paths.append(fn)

        # Only show as much thumbnails as there are poses
        if len(image_paths) >= num_pose_markers:
            image_paths = image_paths[:num_pose_markers]
        # If there are more poses then thumbnails, add placeholder
        if len(image_paths) < num_pose_markers:
            no_thumbnail = os.path.join(os.path.dirname(__file__),
                                        "thumbnails",
                                        "no_thumbnail.png")
            image_paths.append(no_thumbnail)

        # Determine how many extra placeholders are needed
        len_diff = num_pose_markers - len(image_paths)

        for i, name in enumerate(image_paths):
            filepath = os.path.join(bpy.path.abspath(directory), name)
            thumb = pcoll.load(filepath, filepath, 'IMAGE')

            label = os.path.splitext(name)[0]
            match = re.match(r"([0-9]+)[-_\.](.*)", label)
            try:
                num = int(match.groups()[0])
            except (ValueError, TypeError, IndexError, AttributeError):
                num = i
            try:
                pose_name = match.groups()[1]
            except (TypeError, IndexError, AttributeError):
                pose_name = "Pose"
            pose_name = re.sub(r"[-_\.]", " ", pose_name)
            label = "{num} {pose_name}".format(num=num, pose_name=pose_name)

            enum_items.append((name, label, label, thumb.icon_id, i))
            # Add extra placeholder thumbnails if needed
            if name == image_paths[-1]:
                for j in range(len_diff):
                    label = "{num} Pose".format(num=i + j + 1)
                    enum_items.append((name, label, label,
                                       thumb.icon_id,
                                       i + j + 1))

    pcoll.pose_previews = enum_items
    pcoll.pose_previews_dir = directory
    return pcoll.pose_previews


def update_pose(self, context):
    value = self['pose_previews']
    if self.pose_library.pose_markers:
        bpy.ops.poselib.apply_pose(pose_index=value)


class PoseLibPreviewRefresh(bpy.types.Operator):

    """Refresh Pose Library thumbnails of active Pose Library"""

    bl_description = "Refresh Pose Library thumbnails"
    bl_idname = "poselib.refresh_thumbnails"
    bl_label = "Refresh"
    bl_space_type = 'PROPERTIES'

    def execute(self, context):
        obj = context.object
        obj.pose_previews_refresh = True
        generate_previews(context.object, context)
        obj.pose_previews_refresh = False

        return {'FINISHED'}


class PoseLibPreviewPanel(bpy.types.Panel):

    """Creates a Panel in the armature context of the properties editor"""
    bl_label = "Pose Library Previews"
    bl_idname = "DATA_PT_pose_previews"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'ARMATURE' and obj.pose_library

    def draw(self, context):
        user_prefs = context.user_preferences
        addon_prefs = user_prefs.addons[__package__].preferences
        show_labels = addon_prefs.show_labels
        obj = context.object
        pose_lib = obj.pose_library

        layout = self.layout
        col = layout.column(align=False)
        col.template_icon_view(obj, "pose_previews",
                               show_labels=show_labels)
        col.separator()
        col.operator("poselib.refresh_thumbnails", icon='FILE_REFRESH')
        col.prop(pose_lib, "pose_previews_dir")

        if not pose_lib:
            layout.enabled = False


class PoseLibPreviewPropertiesPanel(bpy.types.Panel):

    """Creates a Panel in the 3D View Properties panel"""
    bl_label = "Pose Library"
    bl_idname = "VIEW3D_PT_pose_previews"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        user_prefs = context.user_preferences
        addon_prefs = user_prefs.addons[__package__].preferences
        obj = context.object

        return (obj and obj.type == 'ARMATURE'
                and addon_prefs.add_3dview_prop_panel)

    def draw(self, context):
        user_prefs = context.user_preferences
        addon_prefs = user_prefs.addons[__package__].preferences
        show_labels = addon_prefs.show_labels
        obj = context.object
        pose_lib = obj.pose_library

        layout = self.layout
        col = layout.column(align=False)
        col.template_ID(obj, "pose_library")
        if obj.pose_library:
            col.separator()
            col.template_icon_view(obj, "pose_previews",
                                   show_labels=show_labels)
            col.separator()
            col.operator("poselib.refresh_thumbnails", icon='FILE_REFRESH')
            col.prop(pose_lib, "pose_previews_dir")


def register():
    bpy.types.Object.pose_previews = EnumProperty(
        items=generate_previews,
        update=update_pose)
    bpy.types.Object.pose_previews_refresh = BoolProperty(
        name="Refresh thumbnails",
        default=False)
    bpy.types.Action.pose_previews_dir = StringProperty(
        name="Thumbnail Path",
        subtype='DIR_PATH',
        default="")

    pcoll = bpy.utils.previews.new()
    pcoll.pose_previews_dir = ""
    pcoll.pose_previews = ()
    preview_collections["pose_previews"] = pcoll


def unregister():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

    del bpy.types.Object.pose_previews
    del bpy.types.Action.pose_previews_dir
