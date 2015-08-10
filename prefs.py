import bpy


class PoseLibPreviewPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    add_3dview_prop_panel = bpy.props.BoolProperty(
        name="Add 3D View Properties Panel",
        description="Also add a panel to the Properties Panel of the 3D View",
        default=True)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "add_3dview_prop_panel")
