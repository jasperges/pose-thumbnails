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
import bpy.utils.previews
from bpy_extras.io_utils import ImportHelper


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
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
        self (PoseLibrary)
        context (Blender context = bpy.context)

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
    # def sort_poses(pose_enum):
    #     for i, pose_marker in enumerate(context.object.pose_library.pose_markers):
    #         if pose_marker.frame == int(pose_enum[0]):
    #             return i

    # enum_items = []
    # if context is None or not context.object.pose_library.pose_markers:
    #     return enum_items
    # thumbnail_dir = '/Users/jasperge/projects/prive/blender/scripting/pose_previews_docs/pose_thumbnails/krab_clean/'
    # pose_thumbnail_collection = preview_collections['pose_lib']
    # logger.debug(pose_thumbnail_collection.pose_thumbnails)
    # if pose_thumbnail_collection.pose_thumbnails:
    #     sorted_thumbnails = sorted(pose_thumbnail_collection.pose_thumbnails, key=sort_poses)
    #     logger.debug(sorted_thumbnails)
    #     st = []
    #     for i, t in enumerate(sorted_thumbnails):
    #         st.append(list(t))
    #         st[i][4] = i
    #     sorted_thumbnails = [tuple(t) for t in st]
    #     logger.debug(sorted_thumbnails)
    #     pose_thumbnail_collection.pose_thumbnails = sorted_thumbnails
    #     logger.debug('Returning old thumbnails, but sorted.')
    #     return pose_thumbnail_collection.pose_thumbnails
    # if thumbnail_dir == pose_thumbnail_collection.thumbnail_dir:
    #     logger.debug('Thumbnail dir is still the same')
    #     return pose_thumbnail_collection.pose_thumbnails
    # logger.info("Scanning directory %s..." % (thumbnail_dir))
    # image_paths = get_images_from_dir(thumbnail_dir)
    # pose_markers = context.object.pose_library.pose_markers
    # frame_sorted_pose_markers = sorted(pose_markers, key=lambda pose_marker: pose_marker.frame)
    # zipper = zip(frame_sorted_pose_markers, image_paths)
    # sorted_image_paths = sorted(zipper, key=lambda p: pose_markers.find(p[0].name))
    # sorted_image_paths = [img[1] for img in sorted_image_paths]
    # logger.debug(sorted_image_paths)
    # for i, name in enumerate(sorted_image_paths):
    #     filepath = os.path.join(thumbnail_dir, name)
    #     frame = context.object.pose_library.pose_markers[i].frame
    #     display_name = os.path.splitext(name)[0].split('_', 1)[-1]
    #     thumbnail = pose_thumbnail_collection.load(filepath, filepath, 'IMAGE')
    #     enum_items.append((str(frame), display_name, '', thumbnail.icon_id, i))
    # pose_thumbnail_collection.pose_thumbnails = enum_items
    # pose_thumbnail_collection.thumbnail_dir = thumbnail_dir
    # return pose_thumbnail_collection.pose_thumbnails
    enum_items = []
    if context = None or not context.object.pose_library.pose_markers:
        return enum_items
    pose_thumbnail_collection = preview_collections['pose_library']
    logger.debug(pose_thumbnail_collection.pose_thumbnails)
    # upadate thumbnail indices
    # sort thumbnails by indices
    # create thumbnails


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
    row.operator(AddPoseThumbnail.bl_idname)
    # row.template_icon_view(
    #     obj.pose_library.pose_thumbnails,
    #     'thumbnails',
    #     show_labels=show_labels,
    #     )


class AddPoseThumbnail(bpy.types.Operator, ImportHelper):
    '''Add a thumbnail to a pose from a pose library.'''
    bl_idname = 'poselib.add_thumbnail'
    bl_label = 'Add thumbnail'
    # bl_options = {'PRESET', 'UNDO'}

    filename_ext = '.jpg;.jpeg;.png'
    filter_glob = bpy.props.StringProperty(
        default='*.jpg;*.jpeg;*.png',
        options={'HIDDEN'},
        )

    use_relative_path = bpy.props.BoolProperty(
        name='Relative Path',
        description='Select the file relative to the blend file',
        default=True,
        )

    def execute(self, context):
        if not self.use_relative_path:
            filepath = self.filepath
        else:
            filepath = bpy.path.relpath(self.filepath)
        poselib = context.object.pose_library
        active_posemarker = poselib.pose_markers.active
        active_posemarker_index = poselib.pose_markers.active_index
        for thumbnail in poselib.pose_thumbnails.info:
            if thumbnail.frame == active_posemarker.frame:
                thumbnail.name = active_posemarker.name
                thumbnail.index = active_posemarker_index
                thumbnail.filepath = filepath
                break
        else:
            thumbnail = poselib.pose_thumbnails.info.add()
            thumbnail.name = active_posemarker.name
            thumbnail.index = active_posemarker_index
            thumbnail.frame = active_posemarker.frame
            thumbnail.filepath = filepath
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "use_relative_path")


class PoselibThumbnails(bpy.types.PropertyGroup):
    '''A property to hold the thumbnail info for a pose.'''
    name = bpy.props.StringProperty(
        name='Pose name',
        description='The name of the pose marker.',
        default='',
        )
    index = bpy.props.IntProperty(
        name='Pose index',
        description='The index of the pose marker.',
        default=-1,
        )
    frame = bpy.props.IntProperty(
        name='Pose frame',
        description='The frame of the pose marker.',
        default=-1,
        )
    filepath = bpy.props.StringProperty(
        name='Thumbnail path',
        description='The file path of the thumbnail image.',
        default='',
        subtype='FILE_PATH',
        )


class PoselibThumbnailsInfo(bpy.types.PropertyGroup):
    info = bpy.props.CollectionProperty(
        type=PoselibThumbnails)
    # thumbnails = bpy.props.EnumProperty(
    #     items=get_pose_thumbnails,
    #     update=update_pose,
    #     )


def register():
    # bpy.utils.register_class(PoselibThumbnails)
    bpy.types.Action.pose_thumbnails = bpy.props.PointerProperty(
        type=PoselibThumbnailsInfo)
    # bpy.types.Action.pose_thumbnails = EnumProperty(
    #     items=get_pose_thumbnails,
    #     update=update_pose,
    #     )
    # bpy.types.Action.pose_info = bpy.props.CollectionProperty(
    #     type=PoselibThumbnails)

    bpy.types.DATA_PT_pose_library.prepend(pose_thumbnails_draw)

    pose_thumbnail_collection = bpy.utils.previews.new()
    # pose_thumbnail_collection.thumbnail_dir = ''
    pose_thumbnail_collection.pose_thumbnails = ()
    preview_collections['pose_library'] = pose_thumbnail_collection


def unregister():
    bpy.types.DATA_PT_pose_library.remove(pose_thumbnails_draw)
    for pose_thumbnail_collection in preview_collections.values():
        bpy.utils.previews.remove(pose_thumbnail_collection)
    preview_collections.clear()

    # del bpy.types.Action.pose_info
    del bpy.types.Action.pose_thumbnails
