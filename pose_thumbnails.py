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


def get_thumbnail_from_pose(pose):
    '''Get the thumbnail that belongs to the pose.

    Args:
        pose (pose_marker): a pose in the pose library

    Returns:
        thumbnail PropertyGroup
    '''
    if pose is None:
        return
    poselib = pose.id_data
    for thumbnail in poselib.pose_thumbnails.info:
        if thumbnail.frame == pose.frame:
            return thumbnail


def get_pose_from_thumbnail(thumbnail):
    '''Get the pose that belongs to the thumbnail.

    Args:
        thumbnail (PropertyGroup): thumbnail info of a pose

    Returns:
        pose_marker
    '''
    if thumbnail is None:
        return
    poselib = thumbnail.id_data
    for pose in poselib.pose_markers:
        if pose.frame == thumbnail.frame:
            return pose


def get_pose_index(pose):
    '''Get the index of the pose.'''
    poselib = pose.id_data
    return poselib.pose_markers.find(pose.name)


def get_thumbnail_index(thumbnail):
    poselib = thumbnail.id_data
    for i, posemarker in enumerate(poselib.pose_markers):
        if thumbnail.frame == posemarker.frame:
            return i


def get_no_thumbnail_path():
    '''Get the path to the 'no thumbnail' image.'''
    no_thumbnail_path = os.path.join(
        os.path.dirname(__file__),
        'thumbnails',
        'no_thumbnail.png',
        )
    return no_thumbnail_path


def get_no_thumbnail_image(pcoll):
    no_thumbnail_path = get_no_thumbnail_path()
    no_thumbnail = pcoll.get('No Thumbnail') or pcoll.load(
        'No Thumbnail',
        no_thumbnail_path,
        'IMAGE',
        )
    return no_thumbnail


def add_no_thumbnail_to_pose(pose):
    '''Add info with 'no thumbnail' image to the pose.'''
    poselib = pose.id_data
    no_thumbnail = poselib.pose_thumbnails.info.add()
    no_thumbnail.name = pose.name
    no_thumbnail.index = get_pose_index(pose)
    no_thumbnail.frame = pose.frame
    no_thumbnail.filepath = get_no_thumbnail_path()
    return no_thumbnail


def sort_thumbnails(poselib):
    '''Return the thumbnail info of a pose library sorted by pose index.

    If a pose doesn't have a thumbnail return the 'no thumbnail' image.

    Args:
        poselib (pose library): The pose library for which to get the thumbnails.

    Returns:
        list: the sorted pose thumbnail info
    '''
    pcoll = preview_collections['pose_library']
    for pose in poselib.pose_markers:
        # yield get_thumbnail_from_pose(pose) or add_no_thumbnail_to_pose(pose)
        thumbnail = get_thumbnail_from_pose(pose)
        if thumbnail:
            yield thumbnail


def get_enum_items(thumbnails, pcoll):
    for thumbnail in thumbnails:
        image = pcoll.get(thumbnail.filepath)
        if not image:
            image_path = os.path.normpath(bpy.path.abspath(thumbnail.filepath))
            if not os.path.isfile(image_path):
                image = get_no_thumbnail_image(pcoll)
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
    pcoll = preview_collections['pose_library']
    sorted_thumbnails = sort_thumbnails(poselib)
    enum_items = get_enum_items(
        sorted_thumbnails,
        pcoll,
        )
    pcoll.pose_thumbnails = enum_items
    return pcoll.pose_thumbnails


def update_pose(self, context):
    '''Callback when the enum property is updated (e.g. the index of the active
       item is changed).

    Args:
        self (pose library)
        context (blender context = bpy.context)

    Returns:
        None
    '''
    pose_frame = int(self.thumbnails)
    poselib = self.id_data
    for i, pose_marker in enumerate(poselib.pose_markers):
        if pose_marker.frame == pose_frame:
            bpy.ops.poselib.apply_pose(pose_index=i)
            logger.debug("Applying pose from pose marker '%s' (frame %s)" % (pose_marker.name, pose_frame))
            break


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
    if not poselib.pose_markers.active:
        return
    thumbnail = get_thumbnail_from_pose(poselib.pose_markers.active)
    if thumbnail and thumbnail.filepath != get_no_thumbnail_path():
        text = 'Update Thumbnail'
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
        if not active_posemarker.name.endswith('[T]'):
            name = active_posemarker.name
            active_posemarker.name = ' '.join((name, '[T]'))
        else:
            name = active_posemarker.name[:-4]
        thumbnail = (get_thumbnail_from_pose(active_posemarker) or
                     poselib.pose_thumbnails.info.add())
        thumbnail.name = name
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
    thumbnails = bpy.props.EnumProperty(
        items=get_pose_thumbnails,
        update=update_pose,
        )


def register():
    bpy.types.Action.pose_thumbnails = bpy.props.PointerProperty(
        type=PoselibThumbnailsInfo)

    bpy.types.DATA_PT_pose_library.prepend(pose_thumbnails_draw)

    pcoll = bpy.utils.previews.new()
    pcoll.pose_thumbnails = ()
    preview_collections['pose_library'] = pcoll


def unregister():
    bpy.types.DATA_PT_pose_library.remove(pose_thumbnails_draw)
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

    del bpy.types.Action.pose_thumbnails
