import functools
import re

import bpy

DEFAULT_POSE_SUFFIX = '[T]'


def change_suffix(pose, old_suffix, new_suffix):
    """Change the old suffix to the new one."""
    clean_name = pose.name[:-len(old_suffix)]
    pose.name = ' '.join((clean_name, new_suffix))


def update_pose_suffixes(self, context):
    """Update the pose suffixes when the user pref is changed."""
    for poselib in bpy.data.actions:
        if not poselib.pose_markers:
            continue
        if poselib.pose_thumbnails.suffix == self.pose_suffix:
            continue

        for pose in poselib.pose_markers:
            old_suffix = poselib.pose_thumbnails.suffix
            new_suffix = self.pose_suffix
            change_suffix(pose, old_suffix, new_suffix)
        poselib.pose_thumbnails.suffix = self.pose_suffix


def clear_charnamere_cache(self: 'PoseThumbnailsPreferences', context):
    self.character_name_re.cache_clear()


class PoseThumbnailsPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    add_3dview_prop_panel = bpy.props.BoolProperty(
        name='Add 3D View Properties Panel',
        description='Also add a panel to the Properties Panel of the 3D View',
        default=True,
    )
    pose_suffix = bpy.props.StringProperty(
        name='Pose Suffix',
        description=('Add this suffix to the name of a pose when it has a'
                     ' thumbnail. Leave empty to add nothing'),
        default=DEFAULT_POSE_SUFFIX,
        update=update_pose_suffixes,
    )
    thumbnail_size = bpy.props.FloatProperty(
        name='Thumbnail Size',
        description='How large to draw the pose thumbnails',
        default=1.0,
        min=0.1,
        max=5.0,
    )
    character_name_regexp = bpy.props.StringProperty(
        name='Character Name Regexp',
        description='Regular Expression that obtains the character name from the object name',
        default='[A-Za-z0-9_]+',
        update=clear_charnamere_cache,
    )
    pose_lib_name_prefix = bpy.props.StringProperty(
        name='Pose Library Name Prefix',
        description='Only Actions whose name start with this prefix are considered Pose Libraries',
        default='PLB-',
    )

    @functools.lru_cache(maxsize=1)
    def character_name_re(self):
        """Compile the character name regexp.

        Cached for fast reuse.
        """
        return re.compile(self.character_name_regexp)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'thumbnail_size')
        layout.prop(self, 'add_3dview_prop_panel')
        layout.prop(self, 'pose_suffix')

        layout.separator()
        col = layout.box()
        col.label('Character Name and Pose Library recognition:', icon='TRIA_RIGHT')
        col.prop(self, 'character_name_regexp')
        col.prop(self, 'pose_lib_name_prefix')
        try:
            re.compile(self.character_name_regexp)
        except re.error as ex:
            col.label('Error in regular expression: %s at position %s' % (ex.msg, ex.pos),
                      icon='ERROR')
        else:
            from . import pose_thumbnails
            char = 'Alpha_monster-blenrig.001'
            pl = pose_thumbnails.pose_library_name_prefix(char, context)
            col.label('Object %r will use Pose Libraries %r' % (char, pl + '…'))
