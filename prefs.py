import bpy


class PoseLibPreviewPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    add_3dview_prop_panel = bpy.props.BoolProperty(
        name='Add 3D View Properties Panel',
        description=('Also add a panel to the Properties Panel of the 3D View.'
                     ' (Not functional yet.)'),
        default=True,
        )
    # show_labels = bpy.props.BoolProperty(
    #     name='Show the labels of the preview thumbnails',
    #     description='Show the labels of the preview thumbnails',
    #     default=False,
    #     )
    pose_thumbnail_suffix = bpy.props.StringProperty(
        name='Pose Thumbnail Suffix',
        description=('Add this suffix to the name of a pose when it has a'
                     ' thumbnail. Leave empty to add nothing.'),
        default=' [T]',
        )


    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'add_3dview_prop_panel')
        # layout.prop(self, 'show_labels')
        layout.prop(self, 'pose_thumbnail_suffix')
