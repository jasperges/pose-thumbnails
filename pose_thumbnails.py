"""This module does the actual work for the pose thumbnails addon."""

import collections
import difflib
import functools
import logging
import os
import re
import typing

if 'bpy' in locals():
    import importlib

    if 'prefs' in locals():
        importlib.reload(prefs)
        cache = importlib.reload(cache)
else:
    from . import prefs, cache
import bpy
import bpy.utils.previews
from bpy_extras.io_utils import ImportHelper

logger = logging.getLogger(__name__)
preview_collections = {}

IMAGE_EXTENSIONS = {
    '.jpeg', '.jpg', '.jpe',
    '.png',
    '.tga', '.tpic',
    '.tiff', '.tif',
    '.bmp', '.dib',
    '.cin',
    '.dpx',
    '.psd',
    '.exr',
    '.hdr', '.pic',
}


def is_image_file(filepath):
    """Check if the file is an image file."""
    file_extension = os.path.splitext(filepath)[-1]
    return file_extension.lower() in IMAGE_EXTENSIONS


def get_thumbnail_from_pose(pose: bpy.types.TimelineMarker) -> typing.Optional['PoselibThumbnail']:
    """Get the thumbnail that belongs to the pose.

    Args:
        pose (pose_marker): a pose in the pose library

    Returns:
        thumbnail PropertyGroup
    """
    if pose is None:
        return
    poselib = pose.id_data
    for thumbnail in poselib.pose_thumbnails:
        if thumbnail.frame == pose.frame:
            return thumbnail


def get_pose_from_thumbnail(thumbnail):
    """Get the pose that belongs to the thumbnail.

    Args:
        thumbnail (PropertyGroup): thumbnail info of a pose

    Returns:
        pose_marker
    """
    if thumbnail is None:
        return
    poselib = bpy.context.object.pose_library
    for pose in poselib.pose_markers:
        if pose.frame == thumbnail.frame:
            return pose


def get_pose_index_from_frame(poselib, frame):
    """Get the pose index of the pose with the specified frame."""
    for i, pose in enumerate(poselib.pose_markers):
        if pose.frame == frame:
            return i


def get_no_thumbnail_path():
    """Get the path to the 'no thumbnail' image."""
    no_thumbnail_path = os.path.join(
        os.path.dirname(__file__),
        'thumbnails',
        'no_thumbnail.png',
    )
    return no_thumbnail_path


def get_no_thumbnail_image(pcoll):
    """Return the 'no thumbnail' preview icon."""
    no_thumbnail_path = get_no_thumbnail_path()
    no_thumbnail = pcoll.get('No Thumbnail') or pcoll.load(
        'No Thumbnail',
        no_thumbnail_path,
        'IMAGE',
    )
    return no_thumbnail


def get_placeholder_path():
    """Get the path to the placeholder image."""
    placeholder_path = os.path.join(
        os.path.dirname(__file__),
        'thumbnails',
        'placeholder.png',
    )
    return placeholder_path


def get_placeholder_image(pcoll):
    """Return the placeholder preview icon."""
    placeholder_path = get_placeholder_path()
    placeholder = pcoll.get('Placeholder') or pcoll.load(
        'Placeholder',
        placeholder_path,
        'IMAGE',
    )
    return placeholder


def clear_cached_pose_thumbnails():
    """Clear the cache of get_enum_items()"""
    get_enum_items.cache_clear()


@cache.lru_cache_1arg
def get_enum_items(poselib: bpy.types.Action,
                   pcoll: bpy.utils.previews.ImagePreviewCollection):
    """Return the enum items for the thumbnail previews."""

    enum_items = []
    wm = bpy.context.window_manager
    pose_thumbnail_options = wm.pose_thumbnails.options
    show_all_poses = pose_thumbnail_options.show_all_poses
    for i, pose in enumerate(poselib.pose_markers):
        thumbnail = get_thumbnail_from_pose(pose)
        if thumbnail:
            image = _load_image(poselib, pcoll, thumbnail.filepath)
        elif show_all_poses:
            image = get_placeholder_image(pcoll)
        else:
            image = None
        if image is not None:
            enum_items.append((
                str(pose.frame),
                pose.name,
                '',
                image.icon_id,
                i,
            ))
    return enum_items


def _load_image(poselib: bpy.types.Action,
                pcoll: bpy.utils.previews.ImagePreviewCollection,
                filepath: str):
    abspath = os.path.normpath(bpy.path.abspath(filepath, library=poselib.library))

    log = logger.getChild('get_enum_items')
    log.debug("Thumbnail path: %s", filepath)
    log.debug(" absolute path: %s", abspath)

    image = pcoll.get(abspath)
    if image is not None:
        return image

    if not os.path.isfile(abspath):
        return get_no_thumbnail_image(pcoll)

    return pcoll.load(abspath, abspath, 'IMAGE')


@cache.pyside_cache('active')
def get_pose_thumbnails(self, context):
    """Get the pose thumbnails and add them to the preview collection."""
    poselib = context.object.pose_library
    if (context is None or
            not poselib.pose_markers or
            not poselib.pose_thumbnails):
        return []
    pcoll = preview_collections['pose_library']
    pcoll.pose_thumbnails = get_enum_items(poselib, pcoll)
    return pcoll.pose_thumbnails


def get_current_pose(*, flipped=False) -> dict:
    """Copies all pose bone matrices (matrix_basis) and custom props.

    Returns a dictionary {bone: {'matrix_basis': m44, …}, …}
    """
    from . import flip

    armature = bpy.context.object
    pose_bones = bpy.context.selected_pose_bones or armature.pose.bones
    pose = {}

    def store_bone(pb, mat):
        pose[pb] = {k: v for k, v in pb.items() if k != '_RNA_UI'}
        pose[pb]['matrix_basis'] = mat

    # The selected bones are assumed to be the bones that should move,
    # and not the bones we should obtain the matrix from and flip.
    for target_pb in pose_bones:
        if flipped:
            name = flip.name(target_pb.name)
            source_pb = armature.pose.bones[name]
            store_bone(target_pb, flip.matrix(source_pb.matrix_basis))
        else:
            store_bone(target_pb, target_pb.matrix_basis.copy())

    return pose


def flip_selection():
    """Flip selection, so if bone_L was selected, now bone_R is selected."""
    from . import flip

    pose_bones = bpy.context.object.pose.bones
    selections = {
        flip.name(pb.name): pb.bone.select
        for pb in pose_bones
    }
    for name, select in selections.items():
        pose_bones[name].bone.select = select


def select_all_pose_bones(armature, deselect=False):
    """Select all the pose bones of the armature."""
    for pose_bone in armature.pose.bones:
        pose_bone.bone.select = not deselect


def auto_keyframe():
    """Set automatic keyframes (for the current armature)."""
    auto_insert = bpy.context.scene.tool_settings.use_keyframe_insert_auto
    if not auto_insert:
        return
    selected_pose_bones = bpy.context.selected_pose_bones
    if not selected_pose_bones:
        select_all_pose_bones(bpy.context.object)
    scene = bpy.context.scene
    user_preferences = bpy.context.user_preferences
    use_active_keying_set = scene.tool_settings.use_keyframe_insert_keyingset
    only_insert_available = user_preferences.edit.use_keyframe_insert_available
    active_keying_set = scene.keying_sets_all.active
    if use_active_keying_set and active_keying_set is not None:
        bpy.ops.anim.keyframe_insert_menu(type=active_keying_set.bl_idname)
    elif only_insert_available:
        bpy.ops.anim.keyframe_insert_menu(type='Available')
    else:
        bpy.ops.anim.keyframe_insert_menu(type='WholeCharacterSelected')
    if not selected_pose_bones:
        select_all_pose_bones(bpy.context.object, deselect=True)


def set_pose(pose_a):
    """Set the pose, same as mixing with factor=0."""

    log = logger.getChild('set_pose')
    log.debug('setting pose')
    log_all = len(pose_a) < 10

    for pose_bone, pose_a_props in pose_a.items():
        if log_all:
            log.debug('    - %s', pose_bone.name)
        for prop, pose_a_value in pose_a_props.items():
            if prop == 'matrix_basis':
                pose_bone.matrix_basis = pose_a_value
            else:
                pose_bone[prop] = pose_a_value


def mix_to_pose(pose_a, pose_b, factor):
    """Mixes pose_b over pose_a with the given factor."""

    for pose_bone, pose_a_props in pose_a.items():
        for prop, pose_a_value in pose_a_props.items():
            pose_b_value = pose_b[pose_bone][prop]
            if prop == 'matrix_basis':
                pose_bone.matrix_basis = pose_a_value.lerp(pose_b_value, factor)
            else:
                if isinstance(pose_a_value, float):
                    pose_bone[prop] = pose_a_value * (1 - factor) + pose_b_value * factor
                elif factor < 0.5:
                    pose_bone[prop] = pose_a_value
                else:
                    pose_bone[prop] = pose_b_value
    auto_keyframe()


def update_pose(self, context):
    """Callback when the enum property is updated (e.g. the index of the active
       item is changed).

    Args:
        self (pose library)
        context (blender context = bpy.context)

    Returns:
        None
    """
    pose_frame = int(self.active)
    poselib = context.object.pose_library
    pose_index = get_pose_index_from_frame(poselib, pose_frame)
    pose_thumbnail_options = context.window_manager.pose_thumbnails.options

    bpy.ops.poselib.mix_pose('INVOKE_DEFAULT', pose_index=pose_index,
                             flipped=pose_thumbnail_options.flipped)


def character_name(ob_name: str, context) -> str:
    """Determine character name for the given object name."""
    if not ob_name:
        return ''

    addon_prefs = context.user_preferences.addons[__package__].preferences
    character_name_re = addon_prefs.character_name_re()

    m = character_name_re.match(ob_name)
    if not m:
        return ob_name
    return m.group(0)


def pose_library_name_prefix(ob_name: str, context) -> str:
    """Determine the pose library prefix name for the given object name.

    >>> pose_library_name_prefix('Sintel-heavy-haired')
    'PLB_Sintel'
    >>> pose_library_name_prefix('spring_blenrig')
    'PLB_spring_blenrig'
    >>> pose_library_name_prefix('Spring-blenrig')
    'PLB_Spring'
    """
    char_name = character_name(ob_name, context)
    if not char_name:
        return ''

    addon_prefs = context.user_preferences.addons[__package__].preferences
    return addon_prefs.pose_lib_name_prefix + char_name


# Cache for the pose_lib_for_char EnumProperty items.
# Also used for mapping from the chosen index to an action.
pose_libs_for_current_char = []


def pose_lib_for_char_items(self, context) -> list:
    """Dynamic list of items for Object.pose_libs_for_char."""

    if not context or not context.object:
        return []

    prefix = pose_library_name_prefix(context.object.name, context).lower()
    pose_libs_for_current_char[:] = [
        a for a in bpy.data.actions
        if a.pose_markers and a.name.lower().startswith(prefix)
    ]
    return [
        (a.name, a.name, 'Pose library', '', idx)
        for idx, a in enumerate(pose_libs_for_current_char)
    ]


def pose_lib_for_char_get(self) -> int:
    if not self.pose_library:
        return -1
    try:
        return pose_libs_for_current_char.index(self.pose_library)
    except ValueError:
        return -1


def pose_lib_for_char_set(self, index):
    action = pose_libs_for_current_char[index]
    self.pose_library = action


def pose_thumbnails_draw(self, context):
    """Draw the thumbnail enum in the Pose Library panel."""
    if not context.object:
        return

    layout = self.layout
    col = layout.column(align=True)

    col.prop(context.object, 'pose_lib_for_char',
             text='Libraries for %s' % character_name(context.object.name, context))

    poselib = context.object.pose_library
    if poselib and poselib.pose_markers:
        pose_thumbnail_options = context.window_manager.pose_thumbnails.options
        _draw_thumbnails(context, col, pose_thumbnail_options)
        _draw_creation(col, pose_thumbnail_options, poselib)


def _draw_thumbnails(context, layout, pose_thumbnail_options):
    if context.object.mode != 'POSE':
        layout.enabled = False

    user_prefs = context.user_preferences
    addon_prefs = user_prefs.addons[__package__].preferences
    thumbnail_size = addon_prefs.thumbnail_size * 5
    show_labels = pose_thumbnail_options.show_labels

    layout.template_icon_view(
        context.window_manager.pose_thumbnails,
        'active',
        show_labels=show_labels,
        scale=thumbnail_size,
    )
    if POSELIB_OT_apply_mix_pose.poll(context):
        container = layout.box()
        split = container.row(align=True).split(0.8, align=True)
        split.prop(context.window_manager, 'pose_mix_factor')
        split.operator(POSELIB_OT_apply_mix_pose.bl_idname, icon='FILE_TICK')
        split = container.row(align=True).split(0.8, align=True)
        split.label('Left-click/ENTER to apply, Right-click/ESCAPE to cancel')
        split.operator(POSELIB_OT_cancel_mix_pose.bl_idname, icon='PANEL_CLOSE')
    row = layout.row(align=True)
    row.prop(pose_thumbnail_options, 'flipped')
    row.prop(pose_thumbnail_options, 'show_labels')
    row.prop(pose_thumbnail_options, 'show_all_poses', text='All Poses')


def _draw_creation(layout, pose_thumbnail_options, poselib):
    if poselib.library:
        layout.label('Not showing creation options for linked pose libraries')
        layout.operator(
            POSELIB_OT_refresh_thumbnails.bl_idname,
            icon='FILE_REFRESH',
            text='Refresh',
        )
        return
    layout.separator()
    box = layout.box()
    if pose_thumbnail_options.show_creation_options:
        expand_icon = 'TRIA_DOWN'
    else:
        expand_icon = 'TRIA_RIGHT'
    box.prop(
        pose_thumbnail_options,
        'show_creation_options',
        icon=expand_icon,
        toggle=True,
    )
    if pose_thumbnail_options.show_creation_options:
        sub_col = box.column(align=True)
        if not poselib.pose_markers.active:
            logger.debug('No active pose markers, aborting')
            return
        thumbnail = get_thumbnail_from_pose(poselib.pose_markers.active)
        if thumbnail and thumbnail.filepath != get_no_thumbnail_path():
            text = 'Replace'
        else:
            text = 'Add'
        row = sub_col.row(align=True)
        row.operator(POSELIB_OT_add_thumbnail.bl_idname, text=text)
        row.operator(POSELIB_OT_add_thumbnails_from_dir.bl_idname, text='Batch Add/Change')
        row = sub_col.row(align=True)
        row_col = row.column(align=True)
        row_col.operator(POSELIB_OT_remove_pose_thumbnail.bl_idname, text='Remove')
        if get_thumbnail_from_pose(poselib.pose_markers.active):
            row_col.enabled = True
        else:
            row_col.enabled = False
        row_col = row.column(align=True)
        row_col.operator(POSELIB_OT_remove_all_thumbnails.bl_idname, text='Remove All')
        if poselib.pose_thumbnails:
            row_col.enabled = True
        else:
            row_col.enabled = False
        sub_col.separator()
        sub_col.operator(
            POSELIB_OT_refresh_thumbnails.bl_idname,
            icon='FILE_REFRESH',
            text='Refresh',
        )


def apply_mix_factor(_, context):
    """Apply mix factor from WindowManager property update."""
    if not POSELIB_OT_mix_pose.is_running:
        return
    POSELIB_OT_mix_pose.is_running.execute(context)


class POSELIB_OT_apply_mix_pose(bpy.types.Operator):
    """Apply the currently mixed-in pose"""
    bl_idname = 'poselib.apply_mix_pose'
    bl_label = 'Apply'

    @classmethod
    def poll(cls, context):
        return POSELIB_OT_mix_pose.poll(context) and POSELIB_OT_mix_pose.is_running is not None

    def execute(self, context):
        if not POSELIB_OT_mix_pose.is_running:
            return
        POSELIB_OT_mix_pose.is_running.apply_and_finish()
        return {'FINISHED'}


class POSELIB_OT_cancel_mix_pose(bpy.types.Operator):
    """Cancels the currently mixed-in pose"""
    bl_idname = 'poselib.cancel_mix_pose'
    bl_label = 'Cancel'

    @classmethod
    def poll(cls, context):
        return POSELIB_OT_mix_pose.poll(context) and POSELIB_OT_mix_pose.is_running is not None

    def execute(self, context):
        if not POSELIB_OT_mix_pose.is_running:
            return
        POSELIB_OT_mix_pose.is_running.cancel_and_finish()
        return {'FINISHED'}


class POSELIB_OT_mix_pose(bpy.types.Operator):
    """Mix-apply the selected library pose on to the current pose"""
    bl_idname = 'poselib.mix_pose'
    bl_label = 'Mix the pose with the current pose.'

    is_running = None
    """The instance of the running modal operator, if any."""

    pose_index = bpy.props.IntProperty(
        name='Pose Index',
        default=0,
        min=0,
        description='The index of the pose to mix.',
    )
    flipped = bpy.props.BoolProperty(
        name='Apply Flipped',
        description='Apply the pose mirrored over the YZ-plane',
        default=False,
    )

    # Default values for instance variables.
    mouse_x_ref = 0
    mouse_x = 0
    just_clicked = False
    current_pose = {}
    target_pose = {}
    _target_state = ''

    @classmethod
    def poll(cls, context):
        return (context is not None and
                context.object and
                context.object.type == 'ARMATURE' and
                context.object.mode == 'POSE')

    def _finish(self, context):
        """Perform pre-exit cleanup
        :param context:
        """
        POSELIB_OT_mix_pose.is_running = None
        context.area.tag_redraw()

    def apply_and_finish(self):
        """Apply the currently mixed pose and finish running the operator."""
        self._target_state = 'FINISHED'

    def cancel_and_finish(self):
        """Revert the currently mixed pose and aborts the operator."""
        self._target_state = 'CANCELLED'

    def execute(self, context):
        mix_factor = context.window_manager.pose_mix_factor / 100
        mix_to_pose(self.current_pose, self.target_pose, mix_factor)
        return {'FINISHED'}

    def modal(self, context, event):
        if ((event.type == 'LEFTMOUSE' and event.value == 'CLICK')
                or event.type == 'RET' or self._target_state == 'FINISHED'):
            logger.debug('Finishing modal application')
            self._finish(context)
            return {'FINISHED'}

        if event.type in {'RIGHTMOUSE', 'ESC'} or self._target_state == 'CANCELLED':
            # "mix" with factor 0 to reset the pose.
            logger.debug('Cancelling modal application')
            mix_to_pose(self.current_pose, self.target_pose, 0.0)
            self._finish(context)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        self._determine_poses()
        if not event.shift:
            logger.debug('Applying pose at 100%')
            set_pose(self.target_pose)
            self._finish(context)
            return {'FINISHED'}

        logger.debug('Running modal')
        POSELIB_OT_mix_pose.is_running = self
        context.window_manager.pose_mix_factor = 0

        wm = context.window_manager
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def _determine_poses(self):
        """Set self.current_pose and self.target_pose.

        These are the two poses we have to mix between.
        """
        if self.flipped:
            self.current_pose = get_current_pose(flipped=False)

            # To get the target pose, we have to look at the opposite bones.
            flip_selection()
            orig_nonflipped = get_current_pose(flipped=False)
            bpy.ops.poselib.apply_pose(pose_index=self.pose_index)
            flip_selection()

            self.target_pose = get_current_pose(flipped=True)
            set_pose(orig_nonflipped)
            return

        # Non-flipped is much simpler.
        self.current_pose = get_current_pose(flipped=False)
        bpy.ops.poselib.apply_pose(pose_index=self.pose_index)
        self.target_pose = get_current_pose(flipped=False)


class POSELIB_OT_add_thumbnail(bpy.types.Operator, ImportHelper):
    """Add a thumbnail to a pose"""
    bl_idname = 'poselib.add_thumbnail'
    bl_label = 'Add thumbnail'
    bl_options = {'PRESET', 'UNDO'}

    display_type = bpy.props.EnumProperty(
        items=(('LIST_SHORT', 'Short List', '', 1),
               ('LIST_LONG', 'Long List', '', 2),
               ('THUMBNAIL', 'Thumbnail', '', 3)),
        options={'HIDDEN', 'SKIP_SAVE'},
        default='THUMBNAIL',
    )
    filter_image = bpy.props.BoolProperty(
        default=True,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    filter_folder = bpy.props.BoolProperty(
        default=True,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    filter_glob = bpy.props.StringProperty(
        default='',
        options={'HIDDEN', 'SKIP_SAVE'},
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
        if not is_image_file(filepath):
            self.report({'ERROR_INVALID_INPUT'},
                        'The selected file is not an image.')
            logger.error(' File {0} is not an image.'.format(
                os.path.basename(filepath)))
        poselib = context.object.pose_library
        pose = poselib.pose_markers.active
        thumbnail = (get_thumbnail_from_pose(pose) or
                     poselib.pose_thumbnails.add())
        thumbnail.frame = pose.frame
        thumbnail.filepath = filepath
        clear_cached_pose_thumbnails()
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'use_relative_path')


class POSELIB_OT_add_thumbnails_from_dir(bpy.types.Operator, ImportHelper):
    """Add thumbnails from a directory to poses from a pose library"""
    bl_idname = 'poselib.add_thumbnails_from_dir'
    bl_label = 'Add Thumbnails from Directory'
    bl_options = {'PRESET', 'UNDO'}
    directory = bpy.props.StringProperty(
        maxlen=1024,
        subtype='DIR_PATH',
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    files = bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    display_type = bpy.props.EnumProperty(
        items=(('LIST_SHORT', 'Short List', '', 1),
               ('LIST_LONG', 'Long List', '', 2),
               ('THUMBNAIL', 'Thumbnail', '', 3)),
        options={'HIDDEN', 'SKIP_SAVE'},
        default='THUMBNAIL',
    )
    filter_image = bpy.props.BoolProperty(
        default=True,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    filter_folder = bpy.props.BoolProperty(
        default=True,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    filter_glob = bpy.props.StringProperty(
        default='',
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    map_method_items = (
        ('NAME', 'Name', 'Match the file names with the pose names.'),
        ('INDEX', 'Index', 'Map the files to the order of the poses (the files are sorted by name, '
                           'so numbering them makes sense).'),
        ('FRAME', 'Frame', 'Map the files to the order of the frame number of the poses.'),
    )
    mapping_method = bpy.props.EnumProperty(
        name='Match by',
        description='Match the thumbnail images to the poses by using this method',
        items=map_method_items,
    )
    overwrite_existing = bpy.props.BoolProperty(
        name='Overwrite existing',
        description='Overwrite existing thumbnails of the poses.',
        default=True,
    )
    match_fuzzyness = bpy.props.FloatProperty(
        name='Fuzzyness',
        description='Fuzzyness of the matching (0 = exact match, 1 = everything).',
        min=0.0,
        max=1.0,
        default=0.4,
    )
    match_by_number = bpy.props.BoolProperty(
        name='Match by number',
        description='If the filenames start with a number, match the number to the pose index/frame.',
        default=False,
    )
    start_number = bpy.props.IntProperty(
        name='Start number',
        description='The image number to map to the first pose.',
        default=1,
    )
    use_relative_path = bpy.props.BoolProperty(
        name='Relative Path',
        description='Select the file relative to the blend file',
        default=True,
    )

    def get_images_from_dir(self):
        """Get all image files from a directory."""
        directory = self.directory
        logger.debug('reading thumbs from %s', directory)
        files = [f.name for f in self.files]
        image_paths = []
        if files and not files[0]:
            image_files = os.listdir(directory)
            report = False
        else:
            image_files = files
            report = True
        for image_file in sorted(image_files):
            # ext = os.path.splitext(image_file)[-1].lower()
            # if ext and ext in self.filename_ext:
            image_path = os.path.join(directory, image_file)
            if not is_image_file(image_path):
                if not image_file.startswith('.') and report:
                    logger.warning(
                        ' Skipping file {0} because it\'s not an image.'.format(image_file))
                continue
            if self.use_relative_path:
                image_paths.append(bpy.path.relpath(image_path))
            else:
                image_paths.append(image_path)
        return image_paths

    def create_thumbnail(self, pose, image):
        """Create or update the thumbnail for a pose."""
        if not self.overwrite_existing and get_thumbnail_from_pose(pose):
            return
        poselib = self.poselib
        thumbnail = (get_thumbnail_from_pose(pose) or
                     poselib.pose_thumbnails.add())
        thumbnail.frame = pose.frame
        thumbnail.filepath = image

    def get_image_by_number(self, number):
        """Return a the image file if it contains the number.

        Check if the filename contains the number. It matches the first number
        found in the filename (starting from the left).
        """
        for image in self.image_files:
            basename = os.path.basename(image)
            match = re.match(r'^.*?([0-9]+)', basename)
            if match:
                image_number = int(match.groups()[0])
                if number == image_number:
                    return image

    def match_thumbnails_by_name(self):
        """Assign the thumbnail by trying to match the pose name with a file name."""
        poselib = self.poselib
        image_files = self.image_files
        match_map = {os.path.splitext(os.path.basename(f))[0]: f for f in image_files}
        for pose in poselib.pose_markers:
            match = difflib.get_close_matches(
                pose.name,
                match_map.keys(),
                n=1,
                cutoff=1.0 - self.match_fuzzyness,
            )
            if match:
                thumbnail_image = match_map[match[0]]
                self.create_thumbnail(pose, thumbnail_image)

    def match_thumbnails_by_index(self):
        """Map the thumbnail images to the index of the poses."""
        poselib = self.poselib
        if self.match_by_number:
            start_number = self.start_number
            for i, pose in enumerate(poselib.pose_markers):
                image = self.get_image_by_number(i + start_number)
                if image:
                    self.create_thumbnail(pose, image)
        else:
            image_files = self.image_files
            for pose, image in zip(poselib.pose_markers, image_files):
                self.create_thumbnail(pose, image)

    def match_thumbnails_by_frame(self):
        """Map the thumbnail images to the frame of the poses."""
        poselib = self.poselib
        if self.match_by_number:
            for i, pose in enumerate(poselib.pose_markers):
                image = self.get_image_by_number(pose.frame)
                if image:
                    self.create_thumbnail(pose, image)
        else:
            frame_sorted = sorted(poselib.pose_markers, key=lambda p: p.frame)
            image_files = self.image_files
            for pose, image in zip(frame_sorted, image_files):
                self.create_thumbnail(pose, image)

    def match_thumbnails(self):
        """Try to match the image files to the poses."""
        mapping_method = self.mapping_method
        if mapping_method == 'NAME':
            self.match_thumbnails_by_name()
        elif mapping_method == 'INDEX':
            self.match_thumbnails_by_index()
        else:
            self.match_thumbnails_by_frame()

    def execute(self, context):
        self.poselib = context.object.pose_library
        self.image_files = self.get_images_from_dir()
        self.match_thumbnails()
        clear_cached_pose_thumbnails()
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        box = col.box()
        box.label(text='Mapping Method')
        row = box.row()
        row.prop(self, 'mapping_method', expand=True)
        box.prop(self, 'overwrite_existing')
        if self.mapping_method == 'NAME':
            box.prop(self, 'match_fuzzyness')
        if self.mapping_method == 'INDEX':
            box.prop(self, 'match_by_number')
            if self.match_by_number:
                box.prop(self, 'start_number')
        if self.mapping_method == 'FRAME':
            box.prop(self, 'match_by_number')
        col.separator()
        col.prop(self, 'use_relative_path')


class POSELIB_OT_remove_pose_thumbnail(bpy.types.Operator):
    """Remove a thumbnail from a pose"""
    bl_idname = 'poselib.remove_thumbnail'
    bl_label = 'Remove Thumbnail'
    bl_options = {'PRESET', 'UNDO'}

    def execute(self, context):
        poselib = context.object.pose_library
        pose = poselib.pose_markers.active
        clear_cached_pose_thumbnails()
        for i, thumbnail in enumerate(poselib.pose_thumbnails):
            if pose.frame == thumbnail.frame:
                poselib.pose_thumbnails.remove(i)
                break
        return {'FINISHED'}


class POSELIB_OT_remove_all_thumbnails(bpy.types.Operator):
    """Remove all thumbnails"""
    bl_idname = 'poselib.remove_all_thumbnails'
    bl_label = 'Remove All Thumbnails'
    bl_options = {'PRESET', 'UNDO'}

    def execute(self, context):
        poselib = context.object.pose_library
        poselib.pose_thumbnails.clear()
        clear_cached_pose_thumbnails()
        return {'FINISHED'}


class POSELIB_OT_refresh_thumbnails(bpy.types.Operator):
    """Reloads and cleans the thumbnails and poses"""
    bl_idname = 'poselib.refresh_thumbnails'
    bl_label = 'Refresh Thumbnails'
    bl_options = {'PRESET', 'UNDO'}

    def remove_thumbnail(self, thumbnail):
        """Remove the thumbnail from the poselib thumbnail info."""
        pose_thumbnails = self.poselib.pose_thumbnails
        for i, existing_thumbnail in enumerate(pose_thumbnails):
            if thumbnail == existing_thumbnail:
                logger.debug('removing thumbnail %r at index %d', thumbnail, i)
                pose_thumbnails.remove(i)

    def remove_unused_thumbnails(self):
        """Remove unused thumbnails."""

        thumbs = self.poselib.pose_thumbnails
        count = len(thumbs)
        for i, thumbnail in enumerate(reversed(thumbs)):
            if not get_pose_from_thumbnail(thumbnail):
                thumbs.remove(count - i - 1)

    def remove_double_thumbnails(self):
        """Remove extraneous thumbnails from a pose."""
        thumbnail_map = collections.defaultdict(list)
        for thumbnail in self.poselib.pose_thumbnails:
            thumbnail_map[str(thumbnail.frame)].append(thumbnail)

        for thumbnail_list in thumbnail_map.values():
            for thumbnail in thumbnail_list[:-1]:
                self.remove_thumbnail(thumbnail)

    def execute(self, context):
        clear_cached_pose_thumbnails()
        self.poselib = context.object.pose_library
        self.remove_unused_thumbnails()
        self.remove_double_thumbnails()
        pcoll = preview_collections['pose_library']
        pcoll.clear()
        return {'FINISHED'}


class PoselibThumbnail(bpy.types.PropertyGroup):
    """A property to hold the thumbnail info for a pose"""
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


class PoselibThumbnailsOptions(bpy.types.PropertyGroup):
    """A property to hold the option info for the thumbnail UI"""
    show_creation_options = bpy.props.BoolProperty(
        name='Thumbnail Creation',
        description='Show or hide the thumbnail creation options.',
        default=False,
    )
    show_labels = bpy.props.BoolProperty(
        name='Show Labels',
        description='Show the labels (pose names) underneath the thumbnails.',
        default=True,
    )
    show_all_poses = bpy.props.BoolProperty(
        name='Show All Poses',
        description='Also show poses that don\'t have a thumbnail.',
        default=False,
    )
    flipped = bpy.props.BoolProperty(
        name='Apply Flipped',
        description='Apply the pose mirrored over the YZ-plane',
        default=False,
    )


class PoselibUiSettings(bpy.types.PropertyGroup):
    """A collection property for all the UI related settings"""
    active = bpy.props.EnumProperty(
        items=get_pose_thumbnails,
        update=update_pose,
    )
    options = bpy.props.PointerProperty(
        type=PoselibThumbnailsOptions,
    )


class POSELIB_PT_pose_previews(bpy.types.Panel):
    """Creates a pose thumbnail panel in the 3D View Properties panel"""
    bl_label = "Pose Library"
    bl_idname = "POSELIB_PT_pose_previews"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        user_prefs = context.user_preferences
        addon_prefs = user_prefs.addons[__package__].preferences
        obj = context.object
        return (obj and obj.type == 'ARMATURE' and
                addon_prefs.add_3dview_prop_panel)

    def draw(self, context):
        user_prefs = context.user_preferences
        addon_prefs = user_prefs.addons[__package__].preferences
        wm = context.window_manager
        obj = context.object
        poselib = obj.pose_library
        layout = self.layout
        col = layout.column(align=True)
        col.template_ID(obj, "pose_library", unlink="poselib.unlink")
        if poselib is not None:
            pose_thumbnail_options = wm.pose_thumbnails.options
            show_labels = pose_thumbnail_options.show_labels
            thumbnail_size = addon_prefs.thumbnail_size * 5
            col.template_icon_view(
                wm.pose_thumbnails,
                'active',
                show_labels=show_labels,
                scale=thumbnail_size,
            )
            row = col.row(align=True)
            row.prop(
                pose_thumbnail_options,
                'show_labels',
                toggle=True,
                text='Labels',
            )
            row.prop(
                pose_thumbnail_options,
                'show_all_poses',
                toggle=True,
                text='All Poses',
            )


def register():
    """Register all pose thumbnail related things."""
    bpy.types.WindowManager.pose_mix_factor = bpy.props.FloatProperty(
        name='Mix Factor',
        default=100,
        subtype='PERCENTAGE',
        unit='NONE',
        min=0,
        max=100,
        description='Mix Factor',
        update=apply_mix_factor,
    )
    bpy.types.Object.pose_lib_for_char = bpy.props.EnumProperty(
        items=pose_lib_for_char_items,
        name='Pose Libraries',
        description='Only lists Pose Libraries for the current character, i.e. PLB_{charname}*',
        get=pose_lib_for_char_get,
        set=pose_lib_for_char_set,
    )
    bpy.types.Action.pose_thumbnails = bpy.props.CollectionProperty(
        type=PoselibThumbnail)
    bpy.types.WindowManager.pose_thumbnails = bpy.props.PointerProperty(
        type=PoselibUiSettings)
    bpy.types.DATA_PT_pose_library.prepend(pose_thumbnails_draw)
    pcoll = bpy.utils.previews.new()
    pcoll.pose_thumbnails = ()
    preview_collections['pose_library'] = pcoll


def unregister():
    """Unregister all pose thumbnails related things."""
    bpy.types.DATA_PT_pose_library.remove(pose_thumbnails_draw)
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
    del bpy.types.Action.pose_thumbnails
    del bpy.types.WindowManager.pose_thumbnails
    del bpy.types.WindowManager.pose_mix_factor
