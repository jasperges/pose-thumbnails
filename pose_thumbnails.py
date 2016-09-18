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
logging.basicConfig(level=logging.DEBUG)
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
    pose_thumbnail_collection = preview_collections['pose_lib']
    if previews_dir == pose_thumbnail_collection.pose_previews_dir:
        return pose_thumbnail_collection.pose_previews
    if previews_dir and os.path.isdir(previews_dir):
        logger.info("Scanning directory %s..." % (previews_dir))
        if pose_thumbnail_collection:
            pose_thumbnail_collection.clear()
        image_paths = get_images_from_dir(previews_dir)
        for i, name in enumerate(image_paths):
            filepath = os.path.join(previews_dir, name)
            thumbnail = pose_thumbnail_collection.load(filepath, filepath, 'IMAGE')
            enum_items.append((name, name, '', thumbnail.icon_id, i))
    pose_thumbnail_collection.previews = enum_items
    pose_thumbnail_collection.pose_previes_dir = previews_dir
    return pose_thumbnail_collection.previews


def get_pose_thumbnails(self, context):
    '''Return the items for the pose thumbnails EnumProperty.

    Args:
        self (EnumProperty class)
        context (blender context = bpy.context)

    Returns:
        list: sequence of string tuples for the enum items
            The first three elements of the tuples are mandatory.
            identifier: The identifier is used for Python access.
            name: Name for the interace.
            description: Used for documentation and tooltips.
            icon: An icon string identifier or integer icon value.
            number: Unique value used as the identifier for this item (stored
                in file data). Use when the identifier may need to change.
    '''
    def sort_thumbnails(thumbnail):
        pose_markers = context.object.pose_library.pose_markers
        frame_sorted_pose_markers = sorted(pose_marker, key=lambda pose_marker: pose_marker.frame)


    enum_items = []
    if context is None or not context.object.pose_library.pose_markers:
        return enum_items
    thumbnail_dir = '/Users/jasperge/projects/prive/blender/scripting/pose_previews_docs/pose_thumbnails/krab_clean/'
    pose_thumbnail_collection = preview_collections['pose_lib']
    if thumbnail_dir == pose_thumbnail_collection.thumbnail_dir:
        return pose_thumbnail_collection.pose_thumbnails
    logger.info("Scanning directory %s..." % (thumbnail_dir))
    image_paths = get_images_from_dir(thumbnail_dir)
    pose_markers = context.object.pose_library.pose_markers
    frame_sorted_pose_markers = sorted(pose_markers, key=lambda pose_marker: pose_marker.frame)
    zipper = zip(frame_sorted_pose_markers, image_paths)
    sorted_image_paths = sorted(zipper, key=lambda p: pose_markers.find(p[0].name))
    # sorted_image_paths = sorted(image_paths, key=sort_thumbnails)
    sorted_image_paths = [img[1] for img in sorted_image_paths]
    logger.debug(sorted_image_paths)
    for i, name in enumerate(sorted_image_paths):
        filepath = os.path.join(thumbnail_dir, name)
        # frame = context.object.pose_library.pose_markers[i].frame
        display_name = os.path.splitext(name)[0].split('_', 1)[-1]
        thumbnail = pose_thumbnail_collection.load(filepath, filepath, 'IMAGE')
        enum_items.append((str(i), display_name, '', thumbnail.icon_id, i))
    pose_thumbnail_collection.pose_thumbnails = enum_items
    pose_thumbnail_collection.thumbnail_dir = thumbnail_dir
    return pose_thumbnail_collection.pose_thumbnails


def update_pose(self, context):
    '''Callback when the enum property is updated (e.g. the index of the active
       item is changed).

    Args:
        self (EnumProperty class)
        context (blender context = bpy.context)

    Returns:
        None
    '''
    # pose_frame = int(self.pose_thumbnails)
    # for i, pose_marker in enumerate(self.pose_markers):
    #     if pose_marker.frame == pose_frame:
    #         bpy.ops.poselib.apply_pose(pose_index=i)
    #         logger.debug("Applying pose from pose marker '%s' (frame %s)" % (pose_marker.name, pose_frame))
    pose_index = int(self.pose_thumbnails)
    bpy.ops.poselib.apply_pose(pose_index=pose_index)
    pose_marker = context.object.pose_library.pose_markers[pose_index]
    logger.debug("Applying pose from pose marker '%s' (frame %s)" % (pose_marker.name, pose_marker.frame))


# class PoseLibPreviewPanel(bpy.types.Panel):
#     """Creates a Panel in the armature context of the properties editor"""
#     bl_label = "Pose Library Thumbnails"
#     bl_idname = "DATA_PT_pose_thumbnails"
#     bl_space_type = 'PROPERTIES'
#     bl_region_type = 'WINDOW'
#     bl_context = "data"
#     bl_options = {'DEFAULT_CLOSED'}

#     @classmethod
#     def poll(cls, context):
#         user_prefs = context.user_preferences
#         addon_prefs = user_prefs.addons[__package__].preferences
#         obj = context.object

#         return (obj and
#                 obj.type == 'ARMATURE' and
#                 obj.pose and
#                 addon_prefs.add_3dview_prop_panel)

#     def draw(self, context):
#         user_prefs = context.user_preferences
#         addon_prefs = user_prefs.addons[__package__].preferences
#         show_labels = addon_prefs.show_labels
#         obj = context.object
#         pose = obj.pose
#         pose_lib = obj.pose_library

#         layout = self.layout
#         layout.template_icon_view(
#             obj.pose_library,
#             "pose_thumbnails",
#             show_labels=show_labels,
#             )


def pose_thumbnails_draw(self, context):
    if not context.object.pose_library.pose_markers:
        return
    user_prefs = context.user_preferences
    addon_prefs = user_prefs.addons[__package__].preferences
    show_labels = addon_prefs.show_labels
    obj = context.object
    layout = self.layout
    row = layout.row()
    row.template_icon_view(
        obj.pose_library,
        "pose_thumbnails",
        show_labels=show_labels,
        )


def register():
    bpy.types.Action.pose_thumbnails = EnumProperty(
        items=get_pose_thumbnails,
        update=update_pose,
        )
    bpy.types.DATA_PT_pose_library.prepend(pose_thumbnails_draw)
    # bpy.types.Scene.pose_search = bpy.props.CollectionProperty(
    #     type=PoseLibSearch)
    # bpy.types.Object.pose_previews = EnumProperty(
    #     items=previews_from_dir,
    #     update=update_pose,
    #     )
    # bpy.types.Object.pose_previews_refresh = BoolProperty(
    #     name="Refresh thumbnails",
    #     default=False)
    # bpy.types.Object.pose_apply_options = EnumProperty(
    #     name="Apply pose to",
    #     items=[('ALL', 'All', 'Apply the pose to all bones'),
    #            ('SELECTED', 'Selected', 'Apply the pose to the selected bones'),
    #            ('BONEGROUP', 'Bone Group', 'Apply the pose to the bones in a bone group')],
    #     default='ALL')
    # bpy.types.Object.pose_bone_groups = EnumProperty(
    #     name="Bone Group",
    #     items=get_pose_bone_groups)
    # bpy.types.Action.pose_previews_dir = StringProperty(
    #     name="Thumbnail Path",
    #     subtype='DIR_PATH',
    #     default="",
    #     # update=filepath_update,
    #     )

    pose_thumbnail_collection = bpy.utils.previews.new()
    pose_thumbnail_collection.thumbnail_dir = ''
    pose_thumbnail_collection.pose_thumbnails = ()
    preview_collections["pose_lib"] = pose_thumbnail_collection


def unregister():
    bpy.types.DATA_PT_pose_library.remove(pose_thumbnails_draw)
    for pose_thumbnail_collection in preview_collections.values():
        bpy.utils.previews.remove(pose_thumbnail_collection)
    preview_collections.clear()

    del bpy.types.Action.pose_thumbnails
    # del bpy.types.Object.pose_previews
    # del bpy.types.Action.pose_previews_dir
