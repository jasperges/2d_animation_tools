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


# icons: "IMAGE_DATA", "MATERIAL_DATA", "ARROW_LEFTRIGHT", "FILTER"

import os
import time
import math
from collections import OrderedDict
import random
import string
import psd_tools
import bpy
from bpy.props import (BoolProperty,
                       StringProperty,
                       FloatProperty,
                       CollectionProperty)
from bpy_extras.io_utils import ImportHelper


def parse_psd(self, psd_file):
    """
    parse_psd(string psd_file) -> dict layer_info

        Reads psd_file and exports all layers to png's.
        Returns a dictionary with the positions and order of the layers and
        the size of the image.

        string psd_file - the filepath of the psd file
    """

    hidden_layers = self.hidden_layers

    # def parse_layer(layer, prefix=None):
    #     if isinstance(layer, psd_tools.Layer):
    #         if prefix:
    #             layer_name = "-".join((prefix, bpy.path.clean_name(layer.name)))
    #         else:
    #             layer_name = bpy.path.clean_name(layer.name)
    #         png_file = os.path.join(png_dir, "".join((layer_name, ".png")))
    #         layer_image = layer.as_PIL()
    #         layer_image.save(png_file)
    #         width = layer.bbox.width
    #         height = layer.bbox.height
    #         x = layer.bbox.x1
    #         y = layer.bbox.y1
    #         layer_info[layer_name] = {"prefix": prefix,
    #                                   "width": width,
    #                                   "height": height,
    #                                   "x": x,
    #                                   "y": y}
    #     else:
    #         if prefix:
    #             prefix = "-".join((prefix, bpy.path.clean_name(layer.name)))
    #         else:
    #             prefix = bpy.path.clean_name(layer.name)
    #         for layer in layer.layers:
    #             parse_layer(layer, prefix=prefix)

    # def parse_layers(layers, prefix=None):
    #     for i, layer in enumerate(layers):
    #         if not hidden_layers and not layer.visible_global:
    #             continue
    #         parse_layer(layer, prefix=prefix)

    def generate_random_id(length=8):
        chars = ''.join((string.digits,
                         string.ascii_lowercase,
                         string.ascii_uppercase))
        return ''.join(random.choice(chars) for _ in range(length))

    def parse_layer(layer, parent='', layer_list=[]):
        if not isinstance(layer, psd_tools.user_api.psd_image.PSDImage):
            if ((not hidden_layers and not layer.visible_global) or
                    (not hasattr(layer, 'layers') or not layer.layers)):
                return
            layer_name = bpy.path.clean_name(layer.name)
            parent = '_'.join((layer_name, generate_random_id()))
        else:
            parent = 'root'
        for sub_layer in layer.layers:
            sub_layer_name = bpy.path.clean_name(sub_layer.name)
            name = '_'.join((sub_layer_name, generate_random_id()))
            if isinstance(sub_layer, psd_tools.Layer):
                # This is a normal layer we sould export it as a png
                png_file = os.path.join(png_dir, ''.join((name, ".png")))
                layer_image = layer.as_PIL()
                layer_image.save(png_file)
                width = layer.bbox.width
                height = layer.bbox.height
                x = layer.bbox.x1
                y = layer.bbox.y1
                layer_list.append({name: {'width': width,
                                          'height': height,
                                          'x': x,
                                          'y': y,
                                          'layer_type': 'layer',
                                          'parent': parent}})
            else:
                # This is a layer group
                layer_list.append({name: {'layer_type': 'group',
                                          'parent': parent}})
            parse_layer(sub_layer, parent=name, layer_list=layer_list)
        return layer_list

        # if isinstance(layer, psd_tools.Layer):
        #     # This is a normal layer we sould import as a textured plane
        #     width = layer.bbox.width
        #     height = layer.bbox.height
        #     x = layer.bbox.x1
        #     y = layer.bbox.y1
        #     layer_list.append({layer.name: {"width": width,
        #                                     "height": height,
        #                                     "x": x,
        #                                     "y": y}})
        #     # Export png
        #     # Add plane (correct size, texture and location)
        #     # Add plane to groups (if option checked)
        #     # Parent plane to empty (if option checked)
        #     # Put plane on correct layer (if option checked)
        # else:
        #     # This is the whole psd file or a layer group
        #     sub_list = [layer.name]
        #     layer_list.append(sub_list)
        #     # Add empty (if option checked)
        #     # Add empty to groups (if option checked)
        #     # Parent empty to empty (if option checked and not whole psd file)
        #     # Put empty on correct layer (if option checked)
        #     parse_layer(layer, sub_list)

    print("parsing: {}".format(psd_file))
    psd_dir, psd_name = os.path.split(psd_file)
    psd_name = os.path.splitext(psd_name)[0]
    png_dir = os.path.join(psd_dir, '_'.join((psd_name, "pngs")))
    if not os.path.isdir(png_dir):
        os.mkdir(png_dir)
    psd = psd_tools.PSDImage.load(psd_file)
    # layer_info = {"image_size": (psd.bbox.width, psd.bbox.height)}
    # layer_list = []
    layer_info = parse_layer(psd)
    # layer_info["layers"] = layer_list

    # print(layer_info)
    for l in layer_info:
        print(l)

    return (layer_info, png_dir)


def import_images(self, layer_info, img_dir, psd_name, layers):
    """
    import_images(class self, dict layer_info, string img_dir)

        Imports all png images that are in layer_info from img_dir
        into Blender as planes and places these planes correctly.

        class self        - the import operator class
        dict layer_info   - info about the layer like position and index
        string img_dir    - the path to the png images
        listOfBool layers - the layer to put the objects on
    """
    print()
    group_empty = self.group_empty
    group_group = self.group_group
    # group_layers = self.group_layers
    offset = self.offset
    scale_fac = self.scale_fac
    use_mipmap = self.use_mipmap
    use_shadeless = True
    use_transparency = True

    image_width = layer_info["image_size"][0]
    image_height = layer_info["image_size"][1]

    group_name = os.path.splitext(psd_name)[0]
    if group_group:
        group = bpy.data.groups.new(group_name)
    if group_empty:
        empty = bpy.data.objects.new(group_name, None)
        bpy.context.scene.objects.link(empty)
        empty.layers = layers
        try:
            group.objects.link(empty)
        except NameError:
            pass

    for i, k in enumerate(layer_info.keys()):
        if k == "image_size":
            continue
        else:
            layer = k
        print("  - processing: {}".format(layer))
        l = layer_info[layer]
        # Create plane
        loc_x = (-image_width / 2 + l["width"] / 2 + l["x"]) / scale_fac
        loc_y = offset * (i - 1)
        loc_z = (image_height - l["height"] / 2 - l["y"]) / scale_fac
        bpy.ops.mesh.primitive_plane_add(location=(loc_x, loc_y, loc_z),
                                         rotation=(0.5 * math.pi, 0, 0))
        plane = bpy.context.object
        plane.layers = layers
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
        tex.use_mipmap = use_mipmap
        tex.image = img
        mat = bpy.data.materials.new(layer)
        mat.use_shadeless = use_shadeless
        mat.use_transparency = use_transparency
        if use_transparency:
            mat.alpha = 0.0
        mat.texture_slots.create(0)
        mat.texture_slots[0].texture = tex
        if use_transparency:
            mat.texture_slots[0].use_map_alpha = True
        plane.data.materials.append(mat)

        # Group the layers/images
        if group_group:
            group.objects.link(plane)
            if l["prefix"]:
                if l["prefix"] in bpy.data.groups:
                    layer_group = bpy.data.groups[l["prefix"]]
                else:
                    layer_group = bpy.data.groups.new(l["prefix"])
                layer_group.objects.link(plane)
        if group_empty:
            if l["prefix"]:
                if (l["prefix"] in bpy.data.objects and
                        bpy.data.objects[l["prefix"]].type == 'EMPTY'):
                    group_empty = bpy.data.objects[l["prefix"]]
                else:
                    group_empty = bpy.data.objects.new(l["prefix"], None)
                    bpy.context.scene.objects.link(group_empty)
                    group_empty.layers = layers
                try:
                    group.objects.link(group_empty)
                except (NameError, RuntimeError):
                    pass
                plane.parent = group_empty
                group_empty.parent = empty
            else:
                plane.parent = empty


def get_current_layer():
    """
    Return the first layer that is active.
    """

    for i, l in enumerate(bpy.context.scene.layers):
        if l:
            return i


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
    use_mipmap = BoolProperty(
        name="MIP Map",
        description="Use auto-generated MIP maps for the images. Turning this off leads to sharper rendered images",
        default=False)
    group_group = BoolProperty(
        name="Group",
        description="Put the images in groups",
        default=True)
    group_empty = BoolProperty(
        name="Empty",
        description="Parent the images to an empty",
        default=True)
    group_layers = BoolProperty(
        name="Layers",
        description="Put the images on separate layers per PSD",
        default=True)

    def draw(self, context):
        layout = self.layout

        # Import options
        box = layout.box()
        box.label("Import options", icon="FILTER")
        col = box.column()
        col.prop(self, "hidden_layers", icon="GHOST_ENABLED")
        col.prop(self, "offset")
        col.prop(self, "scale_fac")
        # Grouping options
        box = layout.box()
        box.label("Grouping", icon="GROUP")
        row = box.row(align=True)
        row.prop(self, "group_group", toggle=True)
        row.prop(self, "group_empty", toggle=True)
        row.prop(self, "group_layers", toggle=True)
        # Material options (not much for now)
        box = layout.box()
        box.label("Material options", icon="MATERIAL_DATA")
        col = box.column()
        if self.use_mipmap:
            mipmap_icon = "ANTIALIASED"
        else:
            mipmap_icon = "ALIASED"
        col.prop(self, "use_mipmap", icon=mipmap_icon, toggle=True)

    def execute(self, context):
        editmode = context.user_preferences.edit.use_enter_edit_mode
        context.user_preferences.edit.use_enter_edit_mode = False
        if context.active_object and context.active_object.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')

        start_time = time.time()
        print()
        d = self.properties.directory
        fils = self.properties.files
        layer_list = 20 * [False]
        cur_layer = get_current_layer()

        for i, f in enumerate(fils):
            layers = layer_list[:]
            if self.group_layers:
                layernum = (cur_layer + i) % 20
                layers[layernum] = True
            psd_file = os.path.join(d, f.name)
            try:
                layer_info, png_dir = parse_psd(self, psd_file)
            except TypeError:   # None is returned, so something went wrong.
                msg = "Something went wrong. '{f}' is not imported!".format(f=f.name)
                self.report({'ERROR'}, msg)
                print("*** {}".format(msg))
                continue
            # layer_info, png_dir = parse_psd(self, psd_file)
            # import_images(self, layer_info, png_dir, f.name, layers)
        print("\nFiles imported in {s:.2f} seconds".format(
            s=time.time() - start_time))

        context.user_preferences.edit.use_enter_edit_mode = editmode

        return {'FINISHED'}
