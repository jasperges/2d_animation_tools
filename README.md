## 2d animation tools

#### A collection of tools to speed up the 2d animation workflow in Blender

For now there is actually only 1 tool. I will add more if the need arises.

When you have any questions, suggestions or find a bug, just let me know. You're welcome to open an issue.


#### io_import_psd_layers_as_planes

This makes it easy to quickly import all (visible) layers of a Photoshop file as textured planes in Blender. It works by exporting the layers to a sub directory as png's. The positions of the layers will be preserved and they will also be properly stacked on top of each other. So if you have a 2d cutout style character you can import it very fast.
If you want a proper import, make sure you just have nice and clean layers (no adjustment layers, masks, etc.). It might work (in some cases), but I don't intend to support this.

__IMPORTANT:__ This tool has two external dependencies!

- [psd_tools](https://github.com/kmike/psd-tools)
- [Pillow](https://github.com/python-pillow/Pillow)

You can install them with pip:

- `pip install psd-tools`
- `pip install Pillow`

Make sure you install them for Python 3.4 so they will work with Blender. Also make sure Blender's Python can find them. You can add them to the path or copy the modules from your local Python's `site-packages` directory to Blender Python's `site-packages` directory.

Sometime in the future I will try to remove the dependencies if possible, but that could take some time :).


___
