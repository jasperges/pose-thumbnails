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
    def sort_poses(pose_enum):
        for i, pose_marker in enumerate(context.object.pose_library.pose_markers):
            if pose_marker.frame == int(pose_enum[0]):
                return i

    enum_items = []
    if context is None or not context.object.pose_library.pose_markers:
        return enum_items
    thumbnail_dir = '/Users/jasperge/projects/prive/blender/scripting/pose_previews_docs/pose_thumbnails/krab_clean/'
    pose_thumbnail_collection = preview_collections['pose_lib']
    logger.debug(pose_thumbnail_collection.pose_thumbnails)
    if pose_thumbnail_collection.pose_thumbnails:
        sorted_thumbnails = sorted(pose_thumbnail_collection.pose_thumbnails, key=sort_poses)
        logger.debug(sorted_thumbnails)
        st = []
        for i, t in enumerate(sorted_thumbnails):
            st.append(list(t))
            st[i][4] = i
        sorted_thumbnails = [tuple(t) for t in st]
        logger.debug(sorted_thumbnails)
        pose_thumbnail_collection.pose_thumbnails = sorted_thumbnails
        logger.debug('Returning old thumbnails, but sorted.')
        return pose_thumbnail_collection.pose_thumbnails
    if thumbnail_dir == pose_thumbnail_collection.thumbnail_dir:
        logger.debug('Thumbnail dir is still the same')
        return pose_thumbnail_collection.pose_thumbnails
    logger.info("Scanning directory %s..." % (thumbnail_dir))
    image_paths = get_images_from_dir(thumbnail_dir)
    pose_markers = context.object.pose_library.pose_markers
    frame_sorted_pose_markers = sorted(pose_markers, key=lambda pose_marker: pose_marker.frame)
    zipper = zip(frame_sorted_pose_markers, image_paths)
    sorted_image_paths = sorted(zipper, key=lambda p: pose_markers.find(p[0].name))
    sorted_image_paths = [img[1] for img in sorted_image_paths]
    logger.debug(sorted_image_paths)
    for i, name in enumerate(sorted_image_paths):
        filepath = os.path.join(thumbnail_dir, name)
        frame = context.object.pose_library.pose_markers[i].frame
        display_name = os.path.splitext(name)[0].split('_', 1)[-1]
        thumbnail = pose_thumbnail_collection.load(filepath, filepath, 'IMAGE')
        enum_items.append((str(frame), display_name, '', thumbnail.icon_id, i))
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
    pose_frame = int(self.pose_thumbnails)
    for i, pose_marker in enumerate(self.pose_markers):
        if pose_marker.frame == pose_frame:
            bpy.ops.poselib.apply_pose(pose_index=i)
            logger.debug("Applying pose from pose marker '%s' (frame %s)" % (pose_marker.name, pose_frame))


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
