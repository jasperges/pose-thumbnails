import os
import logging
import re

if "bpy" in locals():
    import importlib
    if "prefs" in locals():
        importlib.reload(prefs)
else:
    from . import prefs

import bpy
from bpy.props import (StringProperty,
                       BoolProperty,
                       EnumProperty)
import bpy.utils.previews


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
preview_collections = {}


def get_images_from_dir(directory, sort=True):
    """Get all image files in the directory."""
    valid_images = []
    image_extensions = ['.png', '.jpg', '.jpeg']   # !!!
    for filename in os.listdir(directory):
        if os.path.splitext(filename)[-1].lower() in image_extensions:
            valid_images.append(filename)
    return sorted(valid_images)


def previews_from_dir(self, context):
    """EnumProperty callback."""
    enum_items = []
    if context is None:
        return enum_items
    obj = context.object
    pose_lib = obj.pose_library
    previews_dir = pose_lib.pose_previews_dir
    pcoll = preview_collections['pose_lib']
    if previews_dir == pcoll.pose_previews_dir:
        return pcoll.pose_previews
    if previews_dir and os.path.isdir(previews_dir):
        logger.info("Scanning directory %s..." % (previews_dir))
        if pcoll:
            pcoll.clear()
        image_paths = get_images_from_dir(previews_dir)
        for i, name in enumerate(image_paths):
            filepath = os.path.join(previews_dir, name)
            thumbnail = pcoll.load(filepath, filepath, 'IMAGE')
            enum_items.append((name, name, '', thumbnail.icon_id, i))
    pcoll.previews = enum_items
    pcoll.pose_previes_dir = previews_dir
    return pcoll.previews


class PoseLibPreviewPanel(bpy.types.Panel):
    """Creates a Panel in the armature context of the properties editor"""
    bl_label = "Pose Library Previews"
    bl_idname = "DATA_PT_pose_previews"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
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
        pose = obj.pose
        rows = 4
        pose_lib = obj.pose_library

        layout = self.layout
        col = layout.column(align=False)
        col.template_ID(obj, "pose_library")
        if obj.pose_library:
            col.separator()
            sub_col = col.column(align=True)
            sub_col.template_icon_view(obj, "pose_previews",
                                       show_labels=show_labels)
            # sub_col.prop_search(obj, "pose_previews",
            #                     context.scene, "pose_search",
            #                     text="", icon='VIEWZOOM')
            col.separator()
            row = col.row()
            row.prop(obj, "pose_apply_options", expand=True)
            # col.template_list("UI_UL_list", "bone_groups", pose, "bone_groups", pose.bone_groups, "active_index", rows=rows)
            # col.prop_menu_enum(obj.pose, "bone_groups")
            row = col.row()
            # row.prop(obj, "pose_bone_groups", text="")
            if obj.pose_apply_options == 'BONEGROUP':
                row.enabled = True
            else:
                row.enabled = False
            col.separator()
            # col.operator("poselib.refresh_thumbnails", icon='FILE_REFRESH')
            col.prop(pose_lib, "pose_previews_dir")
        if not obj.mode == 'POSE':
            layout.enabled = False


# class PoseLibPreviewPropertiesPanel(bpy.types.Panel):
#     """Creates a Panel in the 3D View Properties panel"""
#     bl_label = "Pose Library"
#     bl_idname = "VIEW3D_PT_pose_previews"
#     bl_space_type = 'VIEW_3D'
#     bl_region_type = 'UI'
#     bl_context = "data"

#     @classmethod
#     def poll(cls, context):
#         user_prefs = context.user_preferences
#         addon_prefs = user_prefs.addons[__package__].preferences
#         obj = context.object

#         return (obj and obj.type == 'ARMATURE'
#                 and addon_prefs.add_3dview_prop_panel)

#     def draw(self, context):
#         user_prefs = context.user_preferences
#         addon_prefs = user_prefs.addons[__package__].preferences
#         show_labels = addon_prefs.show_labels
#         obj = context.object
#         pose = obj.pose
#         rows = 4
#         pose_lib = obj.pose_library

#         layout = self.layout
#         col = layout.column(align=False)
#         col.template_ID(obj, "pose_library")
#         if obj.pose_library:
#             col.separator()
#             sub_col = col.column(align=True)
#             sub_col.template_icon_view(obj, "pose_previews",
#                                        show_labels=show_labels)
#             # sub_col.prop_search(obj, "pose_previews",
#             #                     context.scene, "pose_search",
#             #                     text="", icon='VIEWZOOM')
#             col.separator()
#             row = col.row()
#             row.prop(obj, "pose_apply_options", expand=True)
#             # col.template_list("UI_UL_list", "bone_groups", pose, "bone_groups", pose.bone_groups, "active_index", rows=rows)
#             # col.prop_menu_enum(obj.pose, "bone_groups")
#             row = col.row()
#             row.prop(obj, "pose_bone_groups", text="")
#             if obj.pose_apply_options == 'BONEGROUP':
#                 row.enabled = True
#             else:
#                 row.enabled = False
#             col.separator()
#             col.operator("poselib.refresh_thumbnails", icon='FILE_REFRESH')
#             col.prop(pose_lib, "pose_previews_dir")
#         if not obj.mode == 'POSE':
#             layout.enabled = False


def register():
    # bpy.types.Scene.pose_search = bpy.props.CollectionProperty(
    #     type=PoseLibSearch)
    bpy.types.Object.pose_previews = EnumProperty(
        items=previews_from_dir,
        # update=update_pose,
        )
    bpy.types.Object.pose_previews_refresh = BoolProperty(
        name="Refresh thumbnails",
        default=False)
    bpy.types.Object.pose_apply_options = EnumProperty(
        name="Apply pose to",
        items=[('ALL', 'All', 'Apply the pose to all bones'),
               ('SELECTED', 'Selected', 'Apply the pose to the selected bones'),
               ('BONEGROUP', 'Bone Group', 'Apply the pose to the bones in a bone group')],
        default='ALL')
    # bpy.types.Object.pose_bone_groups = EnumProperty(
    #     name="Bone Group",
    #     items=get_pose_bone_groups)
    bpy.types.Action.pose_previews_dir = StringProperty(
        name="Thumbnail Path",
        subtype='DIR_PATH',
        default="",
        # update=filepath_update,
        )

    pcoll = bpy.utils.previews.new()
    pcoll.pose_previews_dir = ""
    pcoll.pose_previews = ()
    preview_collections["pose_lib"] = pcoll


def unregister():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

    del bpy.types.Object.pose_previews
    del bpy.types.Action.pose_previews_dir
