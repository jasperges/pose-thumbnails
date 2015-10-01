# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


bl_info = {
    "name": "Pose Library Previews",
    "author": "Jasper van Nieuwenhuizen (jasperge), Pratik Solanki (draguu)",
    "version": (0, 1),
    "blender": (2, 7, 5),
    "location": "Properties > Armature > Pose Library Previews "
                "and 3D View > Properties > Pose Library",
    "description": "Add preview images for a pose Library",
    "warning": "wip",
    "wiki_url": "https://github.com/jasperges/pose_lib_preview/blob/master/README.md",
    "tracker_url": "https://github.com/jasperges/pose_lib_preview/issues",
    "support": 'COMMUNITY',
    "category": "Animation"}


if "bpy" in locals():
    import importlib
    if "pose_lib_previews" in locals():
        importlib.reload(pose_lib_previews)
else:
    from . import pose_lib_previews

import bpy


# Register
def register():
    bpy.utils.register_module(__name__)
    pose_lib_previews.register()


def unregister():
    bpy.utils.unregister_module(__name__)
    pose_lib_previews.unregister()


if __name__ == "__main__":
    register()
