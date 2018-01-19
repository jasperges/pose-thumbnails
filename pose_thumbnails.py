"""This module does the actual work for the pose thumbnails addon."""

import logging
import os
import typing

if 'bpy' in locals():
    import importlib

    if 'prefs' in locals():
        importlib.reload(prefs)
        cache = importlib.reload(cache)
        flip = importlib.reload(flip)
        creation = importlib.reload(creation)
        common = importlib.reload(common)
else:
    from . import prefs, cache, flip, creation, common
import bpy
import bpy.utils.previews

logger = logging.getLogger(__name__)
preview_collections = {}


def get_pose_index_from_frame(poselib, frame):
    """Get the pose index of the pose with the specified frame."""
    for i, pose in enumerate(poselib.pose_markers):
        if pose.frame == frame:
            return i


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


@cache.lru_cache_1arg
def get_enum_items(poselib: bpy.types.Action,
                   pcoll: bpy.utils.previews.ImagePreviewCollection):
    """Return the enum items for the thumbnail previews."""

    enum_items = []
    wm = bpy.context.window_manager
    pose_thumbnail_options = wm.pose_thumbnails.options
    show_all_poses = pose_thumbnail_options.show_all_poses
    for i, pose in enumerate(poselib.pose_markers):
        thumbnail = common.get_thumbnail_from_pose(pose)
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

    image = pcoll.load(abspath, abspath, 'IMAGE')

    pose_thumbnail_options = bpy.context.window_manager.pose_thumbnails.options
    if pose_thumbnail_options.flipped:
        flip.pixels(image.image_pixels, *image.image_size)

    return image


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
        draw_thumbnails(context, col, pose_thumbnail_options)
        creation.draw_creation(col, pose_thumbnail_options, poselib)


def draw_thumbnails(context, layout, pose_thumbnail_options):
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


def on_flipped_updated(self, context):
    common.clear_cached_pose_thumbnails()

    for img in preview_collections['pose_library'].values():
        flip.pixels(img.image_pixels, *img.image_size)


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
        update=on_flipped_updated,
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
