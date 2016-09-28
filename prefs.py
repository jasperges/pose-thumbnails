import bpy


class PoseThumbnailsPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    add_3dview_prop_panel = bpy.props.BoolProperty(
        name='Add 3D View Properties Panel',
        description=('Also add a panel to the Properties Panel of the 3D View.'),
        default=True,
        )
    pose_suffix = bpy.props.StringProperty(
        name='Pose Suffix',
        description=('Add this suffix to the name of a pose when it has a'
                     ' thumbnail. Leave empty to add nothing.'),
        default=' [T]',
        )

    def draw(self, context):
        layout = self.layout
        # layout.prop(self, 'add_3dview_prop_panel')
        layout.prop(self, 'pose_suffix')
