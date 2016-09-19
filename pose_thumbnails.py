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


def sort_thumbnails(thumbnail):
    poselib = thumbnail.id_data
    for i, posemarker in enumerate(poselib.pose_markers):
        if thumbnail.frame == posemarker.frame:
            return i


def get_no_thumbnail_image(pcoll):
    no_thumbnail_path = os.path.join(
        os.path.dirname(__file__),
        'thumbnails',
        'no_thumbnail.png',
        )
    no_thumbnail = pcoll.get('No Thumbnail') or pcoll.load(
        'No Thumbnail',
        no_thumbnail_path,
        'IMAGE',
        )
    return no_thumbnail


def get_enum_items(thumbnails, pcoll, no_thumbnail):
    for thumbnail in thumbnails:
        image = pcoll.get(thumbnail.filepath)
        if not image:
            image_path = os.path.normpath(bpy.path.abspath(thumbnail.filepath))
            if not os.path.isfile(image_path):
                image = no_thumbnail
            else:
                image = pcoll.load(
                    thumbnail.filepath,
                    image_path,
                    'IMAGE',
                    )
        yield ((
            str(thumbnail.frame),
            thumbnail.name,
            '',
            image.icon_id,
            thumbnail.index
            ))

def get_pose_thumbnails(self, context):
    poselib = context.object.pose_library
    if (context is None or
        not poselib.pose_markers or
        not poselib.pose_thumbnails.info):
            return []
    pose_thumbnail_collection = preview_collections['pose_library']
    logger.debug(pose_thumbnail_collection.pose_thumbnails)
    no_thumbnail = get_no_thumbnail_image(pose_thumbnail_collection)
    sorted_thumbnails = sorted(poselib.pose_thumbnails.info, key=sort_thumbnails)
    enum_items = get_enum_items(
        sorted_thumbnails,
        pose_thumbnail_collection,
        no_thumbnail,
        )
    pose_thumbnail_collection.pose_thumbnails = enum_items
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
    return
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
    poselib = context.object.pose_library
    layout = self.layout
    col = layout.column()
    col.template_icon_view(
        poselib.pose_thumbnails,
        'thumbnails',
        show_labels=show_labels,
        )
    for thumbnail in poselib.pose_thumbnails.info:
        if thumbnail.frame == poselib.pose_markers.active.frame:
            text = 'Update Thumbnail'
            break
    else:
        text = 'Add Thumbnail'
    col.operator(AddPoseThumbnail.bl_idname, text=text)


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
                thumbnail.name = active_posemarker.name[:-4]
                thumbnail.index = active_posemarker_index
                thumbnail.filepath = filepath
                break
        else:
            thumbnail = poselib.pose_thumbnails.info.add()
            thumbnail.name = active_posemarker.name
            thumbnail.index = active_posemarker_index
            thumbnail.frame = active_posemarker.frame
            thumbnail.filepath = filepath
            active_posemarker.name = ' '.join((active_posemarker.name, '[T]'))
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
    thumbnails = bpy.props.EnumProperty(
        items=get_pose_thumbnails,
        update=update_pose,
        )


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
