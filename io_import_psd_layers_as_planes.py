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


import os
import time
import math
from psd_tools import PSDImage
import bpy
from bpy.props import (BoolProperty,
                       StringProperty,
                       FloatProperty,
                       CollectionProperty)
from bpy_extras.io_utils import ImportHelper


def parse_psd(psd_file):
    """
    parse_psd(string psd_file) -> dict layer_info

        Reads psd_file and exports all layers to png's.
        Returns a dictionary with the positions and order of the layers and
        the size of the image.

        string psd_file - the filepath of the psd file
    """

    print("parsing: {}".format(psd_file))
    psd_dir, psd_name = os.path.split(psd_file)
    psd_name = os.path.splitext(psd_name)[0]
    png_dir = os.path.join(psd_dir, psd_name)
    if not os.path.isdir(png_dir):
        try:
            os.mkdir(png_dir)
        except IOError:
            # !!!
            pass
    psd = PSDImage.load(psd_file)
    layer_info = {"image_size": (psd.bbox.width, psd.bbox.height)}
    for i, layer in enumerate(psd.layers):
        if not layer.visible_global or (layer.bbox.width < 2 and layer.bbox.height < 2):
            continue
        png_file = os.path.join(png_dir, "".join((layer.name, ".png")))
        layer_image = layer.as_PIL()
        layer_image.save(png_file)
        width = layer.bbox.width
        height = layer.bbox.height
        x = layer.bbox.x1
        y = layer.bbox.y1
        layer_info[layer.name] = {"index": i,
                                  "width": width,
                                  "height": height,
                                  "x": x,
                                  "y": y}

    return (layer_info, png_dir)


def import_images(layer_info, img_dir):
    """
    import_images(dict layer_info, string img_dir)

        Imports all png images that are in layer_info from img_dir
        into Blender as planes and places these planes correctly.

        dict layer_info - info about the layer like position and index
        string img_dir  - the path to the png images
    """

    offset = 0.1
    scale_fac = 100
    image_width = layer_info["image_size"][0]
    image_height = layer_info["image_size"][1]

    for k in layer_info:
        if k == "image_size":
            continue
        else:
            layer = k
        print("  - processing: {}".format(layer))
        l = layer_info[layer]
        # Create plane
        loc_x = (-image_width / 2 + l["width"] / 2 + l["x"]) / scale_fac
        loc_y = offset * l["index"]
        loc_z = (image_height - l["height"] / 2 - l["y"]) / scale_fac
        bpy.ops.mesh.primitive_plane_add(location=(loc_x, loc_y, loc_z),
                                         rotation=(0.5 * math.pi, 0, 0))
        plane = bpy.context.object
        plane.name = layer
        # Add UV's and add image to UV's
        img_path = os.path.join(img_dir, "".join((layer, ".png")))
        img = bpy.data.images.load(img_path)
        plane.data.uv_textures.new()
        plane.data.uv_textures[0].data[0].image = img
        # Scale plane according to image size
        scale_x = l["width"] / scale_fac / 2
        scale_y = l["height"] / scale_fac / 2
        plane.scale = (scale_x, scale_y, 1)
        # Apply rotation and scale
        bpy.ops.object.transform_apply(rotation=True, scale=True)
        # Create material
        tex = bpy.data.textures.new(layer, 'IMAGE')
        tex.use_mipmap = False
        tex.image = img
        mat = bpy.data.materials.new(layer)
        mat.use_shadeless = True
        mat.use_transparency = True
        mat.alpha = 0.0
        mat.texture_slots.create(0)
        mat.texture_slots[0].texture = tex
        mat.texture_slots[0].use_map_alpha = True
        plane.data.materials.append(mat)


# Actual import operator.
class ImportPsdAsPlanes(bpy.types.Operator, ImportHelper):

    '''Import PSD as planes'''
    bl_idname = "import_scene.psd"
    bl_label = "Import PSD as planes"
    bl_options = {'PRESET', 'UNDO'}

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    directory = StringProperty(
        maxlen=1024,
        subtype='DIR_PATH',
        options={'HIDDEN', 'SKIP_SAVE'})
    files = CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'})

    filename_ext = ".psd"
    filter_glob = StringProperty(default="*.psd", options={'HIDDEN'})
    offset = FloatProperty(
        name="Offset",
        description="Offset planes by this amount on the Y axis",
        default=0.1)
    hidden_layers = BoolProperty(
        name="Import hidden layers",
        description="Also import hidden layers",
        default=False)
    scale_fac = FloatProperty(
        name="Scale",
        description="Scale of the planes (how many pixels make up 1 Blender unit)",
        default=100)

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "hidden_layers")
        col.prop(self, "scale_fac")
        col.prop(self, "offset")

    def execute(self, context):
        start_time = time.time()
        print()
        d = self.properties.directory
        fils = self.properties.files
        for f in fils:
            psd_file = os.path.join(d, f.name)
            layer_info, png_dir = parse_psd(psd_file)
            import_images(layer_info, png_dir)
        print("\nFiles imported in {s:.2f} seconds".format(
            s=time.time() - start_time))
        return {'FINISHED'}
