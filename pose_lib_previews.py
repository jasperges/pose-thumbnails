if "bpy" in locals():
    import importlib
    if "prefs" in locals():
        importlib.reload(prefs)
else:
    from . import prefs


import os
import re
import copy
import bpy
from bpy.props import (StringProperty,
                       BoolProperty,
                       EnumProperty)
import bpy.utils.previews


# Dict to hold the ui previews collection
preview_collections = {}


# create the previews and an enum with label,
# tooltip and preview as custom icon
def generate_previews(self, context):
    enum_items = []

    if context is None:
        return enum_items

    obj = self
    pose_lib = obj.pose_library
    directory = pose_lib.pose_previews_dir

    pcoll = preview_collections["pose_previews"]

    if not obj.pose_previews_refresh:
        if directory == pcoll.pose_previews_dir:
            return pcoll.pose_previews

    num_pose_markers = len(pose_lib.pose_markers)

    if directory and os.path.isdir(bpy.path.abspath(directory)):
        if pcoll:
            pcoll.clear()
        image_paths = []
        for fn in os.listdir(bpy.path.abspath(directory)):
            if os.path.splitext(fn)[-1].lower() == ".png":
                image_paths.append(fn)

        # Only show as much thumbnails as there are poses
        if len(image_paths) >= num_pose_markers:
            image_paths = image_paths[:num_pose_markers]
        # If there are more poses then thumbnails, add placeholder
        if len(image_paths) < num_pose_markers:
            no_thumbnail = os.path.join(os.path.dirname(__file__),
                                        "thumbnails",
                                        "no_thumbnail.png")
            image_paths.append(no_thumbnail)

        # Determine how many extra placeholders are needed
        len_diff = num_pose_markers - len(image_paths)

        for i, name in enumerate(image_paths):
            filepath = os.path.join(bpy.path.abspath(directory), name)
            thumb = pcoll.load(filepath, filepath, 'IMAGE')

            label = os.path.splitext(name)[0]
            match = re.match(r"([0-9]+)[-_\.]?(.*)?", label)
            # try:
            #     num = int(match.groups()[0])
            # except (ValueError, TypeError, IndexError, AttributeError):
            num = i + 1
            try:
                pose_name = match.groups()[1]
            except (TypeError, IndexError, AttributeError):
                pose_name = "(no thumbnail)"
            if pose_name:
                pose_name = re.sub(r"[_\.]", " ", pose_name)
            label = "{num} {pose_name}".format(num=num, pose_name=pose_name)

            enum_items.append((label, label, label, thumb.icon_id, i))
            # Add extra placeholder thumbnails if needed
            if name == image_paths[-1]:
                for j in range(len_diff):
                    label = "{num} (no thumbnail)".format(num=i + j + 2)
                    enum_items.append((label, label, label,
                                       thumb.icon_id,
                                       i + j + 1))

    pcoll.pose_previews = enum_items
    pcoll.pose_previews_dir = directory
    return pcoll.pose_previews


def get_pose_bone_groups(self, context):
    enum_items = []

    if context is None:
        return enum_items

    obj = self
    bone_groups = obj.pose.bone_groups
    if bone_groups:
        for bg in bone_groups:
            enum_items.append((bg.name, bg.name, ""))

    return enum_items


def filepath_update(self, context):
    bpy.ops.poselib.refresh_thumbnails()


def update_pose(self, context):
    value = self['pose_previews']
    obj = self

    if obj.pose_apply_options in ('ALL', 'BONEGROUP'):
        selected_bones = [pb.name for pb in context.selected_pose_bones]

    if obj.pose_apply_options == 'ALL':
        for bone in obj.data.bones:
            bone.select = True
    elif obj.pose_apply_options == 'BONEGROUP':
        for bone in obj.data.bones:
            bone.select = False
        bone_group = obj.pose_bone_groups
        for bone in obj.pose.bones:
            try:
                if bone.bone_group.name.lower() == bone_group.lower():
                    obj.data.bones[bone.name].select = True
            except AttributeError:
                pass

    if self.pose_library.pose_markers:
        bpy.ops.poselib.apply_pose(pose_index=value)

    if obj.pose_apply_options in ('ALL', 'BONEGROUP'):
        for bone in obj.data.bones:
            if bone.name in selected_bones:
                bone.select = True
            else:
                bone.select = False


class PoseLibSearch(bpy.types.PropertyGroup):
    pose = bpy.props.StringProperty(name="previews search", default="")


class PoseLibPreviewRefresh(bpy.types.Operator):

    """Refresh Pose Library thumbnails of active Pose Library"""

    bl_description = "Refresh Pose Library thumbnails"
    bl_idname = "poselib.refresh_thumbnails"
    bl_label = "Refresh"
    bl_space_type = 'PROPERTIES'

    def execute(self, context):
        obj = context.object
        obj.pose_previews_refresh = True
        enum_items = generate_previews(context.object, context)
        obj.pose_previews_refresh = False
        scene = context.scene
        scene.pose_search.clear()
        for i in enum_items:
            item = scene.pose_search.add()
            item.name = i[0]

        return {'FINISHED'}


class PoseLibAddPose(bpy.types.Operator):

    """Add a pose to the Pose Library"""

    bl_description = "Add a pose to the Pose Library"
    bl_idname = "poselib.add_pose"
    bl_label = "Add Pose"
    bl_space_type = 'PROPERTIES'

    def execute(self, context):
        scene = context.scene
        obj = context.object
        # frame = len(obj.pose_library.pose_markers) + 1
        frame = obj.pose_library.pose_markers[-1].frame + 1
        bpy.ops.poselib.pose_add(frame=frame)

        if not obj.auto_generate_thumbnails:
            return {'FINISHED'}

        # Render and save thumbnail and update previews
        resolution_x = scene.render.resolution_x
        resolution_y = scene.render.resolution_y
        resolution_percentage = scene.render.resolution_percentage
        scene.render.resolution_x = 256
        scene.render.resolution_y = 256
        scene.render.resolution_percentage = 100
        
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        show_only_render = space.show_only_render
                        space.show_only_render = True

        bpy.ops.render.opengl()

        for window in context.window_manager.windows:
            for area in window.screen.areas:
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.show_only_render = show_only_render

        thumbnail = bpy.data.images['Render Result']
        for marker in obj.pose_library.pose_markers:
            if marker.frame == frame:
                basename = marker.name
            else:
                basename = ""
        # basename = obj.pose_library.pose_markers[frame - 1].name
        basename = "_".join(("{frame:03d}".format(frame=frame), basename))
        filepath = os.path.join(obj.pose_library['pose_previews_dir'], ".".join((basename, "png")))
        filepath = bpy.path.abspath(filepath)
        thumbnail.save_render(filepath)

        scene.render.resolution_x = resolution_x
        scene.render.resolution_y = resolution_y
        scene.render.resolution_percentage = resolution_percentage

        bpy.ops.poselib.refresh_thumbnails()

        return {'FINISHED'}


class PoseLibRemovePose(bpy.types.Operator):

    """Remove a pose to the Pose Library"""

    bl_description = "Remove a pose to the Pose Library"
    bl_idname = "poselib.remove_pose"
    bl_label = "Remove Pose"
    bl_space_type = 'PROPERTIES'

    def execute(self, context):
        obj = context.object
        pose = obj.pose_library.pose_markers.active
        pose_frame = copy.copy(pose.frame)
        bpy.ops.poselib.pose_remove(pose=pose.name)

        if not obj.auto_remove_thumbnails:
            return {'FINISHED'}

        thumb_dir = bpy.path.abspath(obj.pose_library['pose_previews_dir'])
        for _, _, files in os.walk(thumb_dir):
            for f in files:
                match = re.match(r"([0-9]+).*?", f)
                if match and int(match.groups()[0]) == pose_frame:
                    os.remove(os.path.join(thumb_dir, f))

        bpy.ops.poselib.refresh_thumbnails()

        return {'FINISHED'}


class PoseLibTestOperator(bpy.types.Operator):

    """Test Operator for Pose Library Previews"""

    bl_description = "TEST"
    bl_idname = "poselib.test"
    bl_label = "TEST"
    bl_space_type = 'PROPERTIES'

    def execute(self, context):
        obj = context.object
        print(obj.pose_library.pose_markers.active.name)

        return {'FINISHED'}


class PoseLibPreviewPanel(bpy.types.Panel):

    """Creates a Panel in the armature context of the properties editor"""
    bl_label = "Pose Library Previews"
    bl_idname = "DATA_PT_pose_previews"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        user_prefs = context.user_preferences
        addon_prefs = user_prefs.addons[__package__].preferences
        obj = context.object

        return (obj and obj.type == 'ARMATURE'
                and addon_prefs.add_3dview_prop_panel)

    def draw(self, context):
        user_prefs = context.user_preferences
        addon_prefs = user_prefs.addons[__package__].preferences
        show_labels = addon_prefs.show_labels
        obj = context.object
        pose_lib = obj.pose_library

        layout = self.layout
        col = layout.column(align=False)
        col.template_ID(obj, "pose_library")
        if obj.pose_library:
            col.separator()
            sub_col = col.column(align=True)
            sub_col.template_icon_view(obj, "pose_previews",
                                       show_labels=show_labels)
            sub_col.prop_search(obj, "pose_previews",
                                context.scene, "pose_search",
                                text="", icon='VIEWZOOM')
            col.separator()
            row = col.row()
            row.prop(obj, "pose_apply_options", expand=True)
            row = col.row()
            row.prop(obj, "pose_bone_groups", text="")
            if obj.pose_apply_options == 'BONEGROUP':
                row.enabled = True
            else:
                row.enabled = False
            col.separator()
            col.operator("poselib.refresh_thumbnails", icon='FILE_REFRESH')
            col.prop(pose_lib, "pose_previews_dir")
        if not obj.mode == 'POSE':
            layout.enabled = False

        # Experimental - add/remove poses and auto create/remove thumbnails
        if obj.pose_library:
            col.separator()
            col.separator()
            col.label(text="----------")
            col.separator()
            col.separator()
            col.label(text="Pose Library Manager")
            # list of poses in pose library
            row = col.row()
            row.template_list("UI_UL_list", "pose_markers",
                              obj.pose_library, "pose_markers",
                              obj.pose_library.pose_markers,
                              "active_index", rows=3)

            row = col.row(align=True)
            subcol = row.column(align=True)
            subcol.operator("poselib.add_pose")
            subcol = row.column(align=True)
            subcol.operator("poselib.remove_pose")
            if obj.pose_library.pose_markers.active:
                subcol.enabled = True
            else:
                subcol.enabled = False
            row = col.row(align=True)
            row.prop(obj, "auto_generate_thumbnails", toggle=True)
            row.prop(obj, "auto_remove_thumbnails", toggle=True)
            # col.operator("poselib.test")


class PoseLibPreviewPropertiesPanel(bpy.types.Panel):

    """Creates a Panel in the 3D View Properties panel"""
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

        return (obj and obj.type == 'ARMATURE'
                and addon_prefs.add_3dview_prop_panel)

    def draw(self, context):
        user_prefs = context.user_preferences
        addon_prefs = user_prefs.addons[__package__].preferences
        show_labels = addon_prefs.show_labels
        obj = context.object
        pose_lib = obj.pose_library

        layout = self.layout
        col = layout.column(align=False)
        col.template_ID(obj, "pose_library")
        if obj.pose_library:
            col.separator()
            sub_col = col.column(align=True)
            sub_col.template_icon_view(obj, "pose_previews",
                                       show_labels=show_labels)
            sub_col.prop_search(obj, "pose_previews",
                                context.scene, "pose_search",
                                text="", icon='VIEWZOOM')
            col.separator()
            row = col.row()
            row.prop(obj, "pose_apply_options", expand=True)
            row = col.row()
            row.prop(obj, "pose_bone_groups", text="")
            if obj.pose_apply_options == 'BONEGROUP':
                row.enabled = True
            else:
                row.enabled = False
            col.separator()
            col.operator("poselib.refresh_thumbnails", icon='FILE_REFRESH')
            col.prop(pose_lib, "pose_previews_dir")
        if not obj.mode == 'POSE':
            layout.enabled = False


def register():
    bpy.types.Scene.pose_search = bpy.props.CollectionProperty(
        type=PoseLibSearch)
    bpy.types.Object.pose_previews = EnumProperty(
        items=generate_previews,
        update=update_pose)
    bpy.types.Object.pose_previews_refresh = BoolProperty(
        name="Refresh thumbnails",
        default=False)
    bpy.types.Object.pose_apply_options = EnumProperty(
        name="Apply pose to",
        items=[('ALL', 'All', 'Apply the pose to all bones'),
               ('SELECTED', 'Selected', 'Apply the pose to the selected bones'),
               ('BONEGROUP', 'Bone Group', 'Apply the pose to the bones in a bone group')],
        default='ALL')
    bpy.types.Object.pose_bone_groups = EnumProperty(
        name="Bone Group",
        items=get_pose_bone_groups)
    bpy.types.Object.auto_generate_thumbnails = BoolProperty(
        name="Generate thumbnails",
        default=True)
    bpy.types.Object.auto_remove_thumbnails = BoolProperty(
        name="Remove thumbnails",
        default=True)
    bpy.types.Action.pose_previews_dir = StringProperty(
        name="Thumbnail Path",
        subtype='DIR_PATH',
        default="",
        update=filepath_update)

    pcoll = bpy.utils.previews.new()
    pcoll.pose_previews_dir = ""
    pcoll.pose_previews = ()
    preview_collections["pose_previews"] = pcoll


def unregister():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

    del bpy.types.Object.pose_previews
    del bpy.types.Action.pose_previews_dir
