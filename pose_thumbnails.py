'''This module does the actual work for the pose thumbnails addon.'''

import os
import logging
import re
import difflib
import copy
if 'bpy' in locals():
    import importlib
    if 'prefs' in locals():
        importlib.reload(prefs)
else:
    from . import prefs
import bpy
import bpy.utils.previews
from bpy_extras.io_utils import ImportHelper


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
preview_collections = {}


def get_pose_suffix_from_prefs():
    '''Get the pose suffix from the addon preferences.'''
    user_prefs = bpy.context.user_preferences
    addon_prefs = user_prefs.addons[__package__].preferences
    if addon_prefs:
        return addon_prefs.pose_suffix
    else:
        return prefs.DEFAULT_POSE_SUFFIX


def clean_pose_name(pose_name):
    '''Return the clean pose name, that is without thumbnail suffix.'''
    pose_suffix = get_pose_suffix_from_prefs()
    if pose_name.endswith(pose_suffix):
        return pose_name[:-len(pose_suffix)]
    else:
        return pose_name


def suffix_pose_name(pose_name):
    '''Return the pose name with the thumbnail suffix.'''
    user_prefs = bpy.context.user_preferences
    addon_prefs = user_prefs.addons[__package__].preferences
    pose_suffix = addon_prefs.pose_suffix
    if pose_name.endswith(pose_suffix) or not pose_suffix.strip():
        return pose_name
    else:
        return ' '.join((pose_name, pose_suffix))


def get_images_from_dir(directory, sort=True):
    '''Get all image files in the directory.'''
    valid_images = []
    image_extensions = ['.png', '.jpg', '.jpeg']
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
    for thumbnail in poselib.pose_thumbnails.collection:
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
    for i, pose in enumerate(poselib.pose_markers):
        if pose.frame == thumbnail.frame:
            return (i, pose)


def get_pose_index(pose):
    '''Get the index of the pose.'''
    poselib = pose.id_data
    return poselib.pose_markers.find(pose.name)


def get_thumbnail_index(thumbnail):
    '''Return the index of the pose of the thumbnail.'''
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
    '''Return the 'no thumbnail' preview icon.'''
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
    no_thumbnail = poselib.pose_thumbnails.collection.add()
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
    '''Return the enum items for the thumbnail previews.'''
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
        _, pose = get_pose_from_thumbnail(thumbnail)
        thumbnail_name = clean_pose_name(pose.name)
        yield ((
            str(thumbnail.frame),
            thumbnail_name,
            '',
            image.icon_id,
            thumbnail.index
            ))


def get_pose_thumbnails(self, context):
    '''Get the pose thumbnails and add them to the preview collection.'''
    poselib = context.object.pose_library
    if (context is None or
        not poselib.pose_markers or
        not poselib.pose_thumbnails.collection):
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
    pose_frame = int(self.previews_ui)
    poselib = self.id_data
    for i, pose_marker in enumerate(poselib.pose_markers):
        if pose_marker.frame == pose_frame:
            bpy.ops.poselib.apply_pose(pose_index=i)
            logger.debug("Applying pose from pose marker '%s' (frame %s)" % (pose_marker.name, pose_frame))
            break


def pose_thumbnails_draw(self, context):
    '''Draw the thumbnail enum in the Pose Library panel.'''
    obj = context.object
    poselib = obj.pose_library
    if poselib is None or not poselib.pose_markers:
        return
    thumbnail_ui_settings = poselib.pose_thumbnails.ui_settings
    show_labels = thumbnail_ui_settings.show_labels
    layout = self.layout
    col = layout.column(align=True)
    col.template_icon_view(
        poselib.pose_thumbnails,
        'previews_ui',
        show_labels=show_labels,
        )
    col.prop(thumbnail_ui_settings, 'show_labels', toggle=True)
    col.separator()
    box = col.box()
    if thumbnail_ui_settings.creation_group:
        expand_icon = 'TRIA_DOWN'
    else:
        expand_icon = 'TRIA_RIGHT'
    box.prop(
        thumbnail_ui_settings,
        'creation_group',
        icon=expand_icon,
        toggle=True,
        )
    if thumbnail_ui_settings.creation_group:
        sub_col = box.column(align=True)
        if not poselib.pose_markers.active:
            return
        thumbnail = get_thumbnail_from_pose(poselib.pose_markers.active)
        if thumbnail and thumbnail.filepath != get_no_thumbnail_path():
            text = 'Replace'
        else:
            text = 'Add'
        row = sub_col.row(align=True)
        row.operator(AddPoseThumbnail.bl_idname, text=text)
        row.operator(AddPoseThumbnailsFromDir.bl_idname, text='Batch Add/Change')
        row = sub_col.row(align=True)
        row_col = row.column(align=True)
        row_col.operator(RemovePoseThumbnail.bl_idname, text='Remove')
        if get_thumbnail_from_pose(poselib.pose_markers.active):
            row_col.enabled = True
        else:
            row_col.enabled = False
        row_col = row.column(align=True)
        row_col.operator(RemoveAllThumbnails.bl_idname, text='Remove All')
        if poselib.pose_thumbnails.collection:
            row_col.enabled = True
        else:
            row_col.enabled = False
        sub_col.separator()
        sub_col.operator(
            RefreshThumbnails.bl_idname,
            icon='FILE_REFRESH',
            text='Refresh',
            )


def pose_thumbnails_options_draw(self, context):
    '''Draw the thumbnail 'advanced' options in the Pose Library panel.'''
    if not context.object.pose_library.pose_markers:
        return
    user_prefs = context.user_preferences
    addon_prefs = user_prefs.addons[__package__].preferences
    poselib = context.object.pose_library
    layout = self.layout
    col = layout.column(align=True)
    # box = layout.box()
    # col = box.column(align=True)
    thumbnail_ui_settings = poselib.pose_thumbnails.ui_settings
    if thumbnail_ui_settings.creation_group:
        expand_icon = 'TRIA_DOWN'
    else:
        expand_icon = 'TRIA_RIGHT'
    col.prop(
        thumbnail_ui_settings,
        'creation_group',
        icon=expand_icon,
        toggle=True,
        )
    if thumbnail_ui_settings.creation_group:
        col.label(text='Advanced Settings')
        # col.label(text="General:")
        # row = col.row(align=True)
        # row = col.split(.5, align=True)


class AddPoseThumbnail(bpy.types.Operator, ImportHelper):
    '''Add a thumbnail to a pose.'''
    bl_idname = 'poselib.add_thumbnail'
    bl_label = 'Add thumbnail'
    bl_options = {'PRESET', 'UNDO'}

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
        pose_name = active_posemarker.name
        name = clean_pose_name(pose_name)
        active_posemarker.name = suffix_pose_name(pose_name)
        thumbnail = (get_thumbnail_from_pose(active_posemarker) or
                     poselib.pose_thumbnails.collection.add())
        thumbnail.name = name
        thumbnail.index = active_posemarker_index
        thumbnail.frame = active_posemarker.frame
        thumbnail.filepath = filepath
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'use_relative_path')


class AddPoseThumbnailsFromDir(bpy.types.Operator, ImportHelper):
    '''Add thumbnails from a directory to poses from a pose library.'''
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
    filename_ext = '.jpg;.jpeg;.png'
    filter_glob = bpy.props.StringProperty(
        default='*.jpg;*.jpeg;*.png',
        options={'HIDDEN'},
        )
    map_method_items = (
            ('NAME', 'Name', 'Match the file names with the pose names.'),
            ('INDEX', 'Index', 'Map the files to the order of the poses (the files are sorted by name, so numbering them makes sense).'),
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
        '''Get all image files from a directory.'''
        directory = self.directory
        files = [f.name for f in self.files]
        image_paths = []
        if files and not files[0]:
            image_files = os.listdir(directory)
        else:
            image_files = files
        for image_file in sorted(image_files):
            ext = os.path.splitext(image_file)[-1].lower()
            if ext and ext in self.filename_ext:
                image_path = os.path.join(directory, image_file)
                if self.use_relative_path:
                    # yield bpy.path.relpath(image_path)
                    image_paths.append(bpy.path.relpath(image_path))
                else:
                    # yield image_path
                    image_paths.append(image_path)
        return image_paths

    def create_thumbnail(self, index, pose, image):
        '''Create or update the thumbnail for a pose.'''
        if not self.overwrite_existing and get_thumbnail_from_pose(pose):
            return
        poselib = self.poselib
        name = clean_pose_name(pose.name)
        pose.name = suffix_pose_name(pose.name)
        thumbnail = (get_thumbnail_from_pose(pose) or
                     poselib.pose_thumbnails.collection.add())
        thumbnail.name = name
        thumbnail.index = index
        thumbnail.frame = pose.frame
        thumbnail.filepath = image

    def get_image_by_number(self, number):
        '''Return a the image file if it contains the number.

        Check if the filename contains the number. It matches the first number
        found in the filename (starting from the left).
        '''
        for image in self.image_files:
            basename = os.path.basename(image)
            match = re.match(r'^.*?([0-9]+)', basename)
            if match:
                image_number = int(match.groups()[0])
                if number == image_number:
                    return image

    def match_thumbnails_by_name(self):
        '''Assign the thumbnail by trying to match the pose name with a file name.'''
        poselib = self.poselib
        thumbnails_collection = poselib.pose_thumbnails.collection
        image_files = self.image_files
        match_map = {os.path.splitext(os.path.basename(f))[0]: f for f in image_files}
        for i, pose in enumerate(poselib.pose_markers):
            match = difflib.get_close_matches(
                clean_pose_name(pose.name),
                match_map.keys(),
                n=1,
                cutoff=1.0 - self.match_fuzzyness,
                )
            if match:
                thumbnail_image = match_map[match[0]]
                self.create_thumbnail(i, pose, thumbnail_image)

    def match_thumbnails_by_index(self):
        '''Map the thumbnail images to the index of the poses.'''
        poselib = self.poselib
        thumbnails_collection = poselib.pose_thumbnails.collection
        if self.match_by_number:
            start_number = self.start_number
            for i, pose in enumerate(poselib.pose_markers):
                image = self.get_image_by_number(i + start_number)
                if image:
                    self.create_thumbnail(i, pose, image)
        else:
            image_files = self.image_files
            for i, (pose, image) in enumerate(zip(poselib.pose_markers, image_files)):
                self.create_thumbnail(i, pose, image)

    def match_thumbnails_by_frame(self):
        '''Map the thumbnail images to the frame of the poses.'''
        poselib = self.poselib
        thumbnails_collection = poselib.pose_thumbnails.collection
        if self.match_by_number:
            for i, pose in enumerate(poselib.pose_markers):
                image = self.get_image_by_number(pose.frame)
                if image:
                    self.create_thumbnail(i, pose, image)
        else:
            frame_sorted = sorted(poselib.pose_markers, key=lambda p: p.frame)
            image_files = self.image_files
            for i, (pose, image) in enumerate(zip(frame_sorted, image_files)):
                self.create_thumbnail(i, pose, image)

    def match_thumbnails(self):
        '''Try to match the image files to the poses.'''
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


class RemovePoseThumbnail(bpy.types.Operator):
    '''Remove a thumbnail from a pose.'''
    bl_idname = 'poselib.remove_thumbnail'
    bl_label = 'Remove Thumbnail'
    bl_options = {'PRESET', 'UNDO'}

    def execute(self, context):
        poselib = context.object.pose_library
        pose = poselib.pose_markers.active
        pose.name = clean_pose_name(pose.name)
        for i, thumbnail in enumerate(poselib.pose_thumbnails.collection):
            if pose.frame == thumbnail.frame:
                poselib.pose_thumbnails.collection.remove(i)
                break
        return {'FINISHED'}


class RemoveAllThumbnails(bpy.types.Operator):
    '''Remove all thumbnails.'''
    bl_idname = 'poselib.remove_all_thumbnails'
    bl_label = 'Remove All Thumbnails'
    bl_options = {'PRESET', 'UNDO'}

    def execute(self, context):
        poselib = context.object.pose_library
        poselib.pose_thumbnails.collection.clear()
        for pose in poselib.pose_markers:
            pose.name = clean_pose_name(pose.name)
        return {'FINISHED'}


class RefreshThumbnails(bpy.types.Operator):
    '''Reloads and cleans the thumbnails and poses.'''
    bl_idname = 'poselib.refresh_thumbnails'
    bl_label = 'Refresh Thumbnails'
    bl_options = {'PRESET', 'UNDO'}

    def remove_thumbnail(self, thumbnail):
        '''Remove the thumbnail from the poselib thumbnail info.'''
        thumbnail_collection = self.poselib.pose_thumbnails.collection
        for i, existing_thumbnail in enumerate(thumbnail_collection):
            if thumbnail == existing_thumbnail:
                thumbnail_collection.remove(i)

    def remove_unused_thumbnails(self):
        '''Remove unused thumbnails.'''

        def get_unused_thumbnails():
            for thumbnail in self.poselib.pose_thumbnails.collection:
                if not get_pose_from_thumbnail(thumbnail):
                    yield thumbnail

        unused_thumbnails = get_unused_thumbnails()
        for thumbnail in unused_thumbnails:
            self.remove_thumbnail(thumbnail)

    def remove_double_thumbnails(self):
        '''Remove extraneous thumbnails from a pose.'''
        thumbnail_map = {}
        for thumbnail in self.poselib.pose_thumbnails.collection:
            if str(thumbnail.frame) not in thumbnail_map:
                thumbnail_map[str(thumbnail.frame)] = [thumbnail]
            else:
                thumbnail_map[str(thumbnail.frame)].append(thumbnail)
        for frame, thumbnail_list in thumbnail_map.items():
            for thumbnail in thumbnail_list[:-1]:
                self.remove_thumbnail(thumbnail)

    def clean_pose_names(self):
        '''Remove suffixes from poses without a thumbnail.'''
        for pose in self.poselib.pose_markers:
            if not get_thumbnail_from_pose(pose):
                pose.name = clean_pose_name(pose.name)
            else:
                pose.name = suffix_pose_name(pose.name)

    def update_thumbnails(self):
        '''Update the info of the thumbnails.'''
        for thumbnail in self.poselib.pose_thumbnails.collection:
            index, pose = get_pose_from_thumbnail(thumbnail)
            thumbnail.name = clean_pose_name(pose.name)
            thumbnail.index = index

    def execute(self, context):
        self.poselib = context.object.pose_library
        self.clean_pose_names()
        self.remove_unused_thumbnails()
        self.remove_double_thumbnails()
        self.update_thumbnails()
        pcoll = preview_collections['pose_library']
        pcoll.clear()
        return {'FINISHED'}


class PoselibThumbnail(bpy.types.PropertyGroup):
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


class PoselibThumbnailsOptions(bpy.types.PropertyGroup):
    '''A property to hold the option info for the thumbnail UI.'''
    creation_group = bpy.props.BoolProperty(
        name='Thumbnail Creation',
        default=False,
        )
    show_labels = bpy.props.BoolProperty(
        name='Show Labels',
        default=True,
        )


class PoselibThumbnailsInfo(bpy.types.PropertyGroup):
    '''A collection property for all thumbnail related properties.'''
    collection = bpy.props.CollectionProperty(
        type=PoselibThumbnail)
    previews_ui = bpy.props.EnumProperty(
        items=get_pose_thumbnails,
        update=update_pose,
        )
    ui_settings = bpy.props.PointerProperty(
        type=PoselibThumbnailsOptions,
        )
    suffix = bpy.props.StringProperty(
        name='Pose Suffix',
        description=('Add this suffix to the name of a pose when it has a'
                     ' thumbnail. Leave empty to add nothing.'),
        default=get_pose_suffix_from_prefs(),
        )


class PoselibThumbnailsPropertiesPanel(bpy.types.Panel):
    '''Creates a pose thumbnail panel in the 3D View Properties panel'''
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
        return (obj and obj.type == 'ARMATURE' and
                addon_prefs.add_3dview_prop_panel)

    def draw(self, context):
        obj = context.object
        poselib = obj.pose_library
        layout = self.layout
        col = layout.column(align=True)
        # layout.template_ID(obj, "pose_library", new="poselib.new", unlink="poselib.unlink")
        col.template_ID(obj, "pose_library", unlink="poselib.unlink")
        if poselib is not None:
            thumbnail_ui_settings = poselib.pose_thumbnails.ui_settings
            show_labels = thumbnail_ui_settings.show_labels
            col.template_icon_view(
                poselib.pose_thumbnails,
                'previews_ui',
                show_labels=show_labels,
                )
            col.prop(thumbnail_ui_settings, 'show_labels', toggle=True)


def register():
    '''Register all pose thumbnail related things.'''
    bpy.types.Action.pose_thumbnails = bpy.props.PointerProperty(
        type=PoselibThumbnailsInfo)
    bpy.types.DATA_PT_pose_library.prepend(pose_thumbnails_draw)
    # bpy.types.DATA_PT_pose_library.append(pose_thumbnails_options_draw)

    pcoll = bpy.utils.previews.new()
    pcoll.pose_thumbnails = ()
    preview_collections['pose_library'] = pcoll


def unregister():
    '''Unregister all pose thumbnails related things.'''
    bpy.types.DATA_PT_pose_library.remove(pose_thumbnails_draw)
    # bpy.types.DATA_PT_pose_library.remove(pose_thumbnails_options_draw)
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

    del bpy.types.Action.pose_thumbnails
