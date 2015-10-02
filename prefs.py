import bpy


class PoseLibPreviewPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    add_3dview_prop_panel = bpy.props.BoolProperty(
        name="Add 3D View Properties Panel",
        description="Also add a panel to the Properties Panel of the 3D View",
        default=True)

    show_labels = bpy.props.BoolProperty(
        name="Show the labels of the preview thumbnails",
        description="Show the labels of the preview thumbnails",
        default=False)

    remove_standard_panel = bpy.props.BoolProperty(
        name="Remove the standard Pose Library Panel",
        description="Remove the standard Pose Library Panel",
        default=True)

    auto_generate_thumbnails = bpy.props.BoolProperty(
        name="Automatically generate thumbnail",
        description="Automatically generate a new thumbnail when you add a pose",
        default=True)

    auto_remove_thumbnails = bpy.props.BoolProperty(
        name="Automatically remove thumbnail",
        description="Automatically remove a thumbnail when you remove a pose",
        default=True)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "add_3dview_prop_panel")
        # layout.prop(self, "remove_standard_panel")
        layout.prop(self, "show_labels")
        layout.prop(self, "auto_generate_thumbnails")
        layout.prop(self, "auto_remove_thumbnails")
