# Pose Thumbnails

Pose Thumbnails is a simple addon which adds the ability to have thumbnails for the poses in a Pose Library.

## Installation

Download and put the 'pose_thumbnails' folder in your Blender addons folder or use the 'Install from File...' option within Blender.

## Usage

Just create a pose library, add poses and start adding thumbnails. You can assign thumbnails to individual poses or 'batch' assign more images at once.
By default a '[T]' suffix is added to a pose name to show it has a thumbnail. You can change this in the user preferences.
Now just click on the thumbnails to apply a pose.

Since Blender 2.78 you can re-arrange the poses. The thumbnails will match the new arrangement.

**_TIP:_** If you used the old version of this addon, you can simply add the thumbnails you created for that by clicking 'Batch Add/Change' and then choose 'Index' as mapping method.

#### Notes

When making thumbnails for your poses, consider the following:

- Blender uses a resolution of 256x256 for thumbnails. If you make the thumbnails bigger or smaller, they will be scaled.
- Give them proper names, so you know for which poses they are. :)
- At the moment only JPEG and PNG images are supported.

## Issues, bugs and suggestions

**_Known Issue:_** When using the 'Show Labels' option, sometimes the labels show weird characters. I don't know why this happens, but pressing 'Refresh' fixes it most of the times.

If you experience an issue or a bug with the addon or have ideas for improvements, please create an issue here on Github.

## Roadmap

Some things I would like to add:

- Make it simple to quickly generate thumbnails. What I have in mind at the moment is that you have to place a camera, choose the destination directory and it will render out all the thumbnails for the poses. Probably you can also add stamps to the thumbnails.
- Make the option to mix a pose with the current one. Beforehand you choose the percentage or tweak it afterwards in the tool panel. (See: [https://github.com/TheDuckCow/pose-tools](https://github.com/TheDuckCow/pose-tools))
- Pack the images into the Blend file (I'm not sure about this one yet).
