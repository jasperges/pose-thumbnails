# Pose Lib Preview

Pose Lib Preview is a simple addon which adds the ability to have preview images for a Pose Library.

**Warning: This addon is very much a work in progress. I consider it more as a proof of concept then a proper addon at this point. So use at your own risk and expect some/a lot rough corners.**

## Installation

Download and put the `pose_lib_preview` in your Blender addons folder or use the `Install from File...` option within Blender.

## Usage

Still todo (but most of it should speak for itself)

#### Notes

When making thumbnails for your poses, consider the following:

- Blender uses a resolution of 256x256 for thumbnails. If you make the thumbnails bigger or smaller, they will be scaled.
- Make sure to *number* the thumbnails. E.g. `001.png`, `002.png`, etc. That way they will be read in the proper order, so they match the poses from the Pose Library.
- You can give your thumbnails a name by giving them names like `001_first pose.png`. The number and the name should be seperated by either `-` (dash), `_` (underscore) or `.` (dot). If there is a `_` (underscore) or `.` (dot) in the 'name part' of the filename, it gets replaced by ` ` (space). (This will be refined/changed in the future.)
- If there are less thumbnails then poses, the extra poses will get a generic thumbnail.
- If there are more thumbnails then poses, only the thumbnails that match a pose will be read.

If there is some mismatch between poses and thumbnails, just press `refresh`. This will hopefully fix it. (This is an area which can certainly be improved.)

## Issues, bugs and ideas

If you experience an issue or a bug with the addon or have ideas for improvements, please create an issue here on Github.