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
import psd_tools
import bpy
from bpy.props import (BoolProperty,
                       StringProperty,
                       FloatProperty,
                       CollectionProperty)
from bpy_extras.io_utils import ImportHelper


def parse_psd(self, psd_file):
    '''
    parse_psd(string psd_file) -> dict layer_info

        Reads psd_file and exports all layers to png's.
        Returns a dictionary with the positions and order of the layers and
        the size of the image.

        string psd_file - the filepath of the psd file
    '''

    hidden_layers = self.hidden_layers

    def parse_layer(layer, parent='', layer_list=[]):
        if not isinstance(layer, psd_tools.user_api.psd_image.PSDImage):
            if ((not hidden_layers and not layer.visible_global) or
                    (not hasattr(layer, 'layers') or not layer.layers)):
                return
            layer_name = bpy.path.clean_name(layer.name)
            parent = '{name}_{id}'.format(name=layer_name, id=layer.layer_id)
        else:
            parent = 'root'
        for sub_layer in layer.layers:
            if not hidden_layers and not sub_layer.visible_global:
                continue
            sub_layer_name = bpy.path.clean_name(sub_layer.name)
            name = '{name}_{id}'.format(name=sub_layer_name, id=sub_layer.layer_id)
            if isinstance(sub_layer, psd_tools.Layer):
                # This is a normal layer we sould export it as a png
                png_file = os.path.join(png_dir, ''.join((name, '.png')))
                layer_image = sub_layer.as_PIL()
                layer_image.save(png_file)
                width = sub_layer.bbox.width
                height = sub_layer.bbox.height
                x = sub_layer.bbox.x1
                y = sub_layer.bbox.y1
                layer_list.append((name, {'width': width,
                                          'height': height,
                                          'x': x,
                                          'y': y,
                                          'layer_type': 'layer',
                                          'parent': parent}))
            else:
                # This is a layer group
                layer_list.append((name, {'layer_type': 'group',
                                          'parent': parent}))
            parse_layer(sub_layer, parent=name, layer_list=layer_list)
        return layer_list

    print('\nparsing: {}'.format(psd_file))
    psd_dir, psd_name = os.path.split(psd_file)
    psd_name = os.path.splitext(psd_name)[0]
    png_dir = os.path.join(psd_dir, '_'.join((psd_name, 'pngs')))
    if not os.path.isdir(png_dir):
        os.mkdir(png_dir)
    psd = psd_tools.PSDImage.load(psd_file)
    layer_info = parse_layer(psd)
    image_size = (psd.bbox.width, psd.bbox.height)

    return (layer_info, image_size, png_dir)


def create_objects(self, layer_info, image_size, img_dir, psd_name, layers):
    '''
    create_objects(class self, list layer_info, tuple image_size,
                  string img_dir, string psd_name, list layers)

        Imports all png images that are in layer_info from img_dir
        into Blender as planes and places these planes correctly.

        class self        - the import operator class
        list layer_info   - info about the layer like position and index
        tuple image_size  - the witdth and height of the image
        string img_dir    - the path to the png images
        string psd_name   - the name of the psd file
        listOfBool layers - the layer(s) to put the objects on
    '''

    def group_object(obj, parent, root_name,
                     root_group, group_empty, group_group):
        if parent == 'root':
            parent = root_name
        if group_empty:
            if (parent in bpy.data.objects and
                    bpy.data.objects[parent].type == 'EMPTY'):
                parent_empty = bpy.data.objects[parent]
            else:
                parent_empty = bpy.data.objects.new(parent, None)
                bpy.context.scene.objects.link(parent_empty)
                parent_empty.layers = layers
            obj.parent = parent_empty
        if group_group:
            # Only put objects in one group per psd file
            try:
                root_group.objects.link(empty)
            except RuntimeError:
                pass

    group_empty = self.group_empty
    group_group = self.group_group
    offset = self.offset
    scale_fac = self.scale_fac
    use_mipmap = self.use_mipmap
    use_shadeless = True
    use_transparency = True

    image_width = image_size[0]
    image_height = image_size[1]

    root_name = os.path.splitext(psd_name)[0]
    if group_group:
        root_group = bpy.data.groups.new(root_name)
    if group_empty:
        empty = bpy.data.objects.new(root_name, None)
        bpy.context.scene.objects.link(empty)
        empty.layers = layers
        try:
            root_group.objects.link(empty)
        except NameError:
            pass

    i = 0
    for layer in layer_info:
        msg = '  - processing: {layer}'.format(layer=layer[0])
        spaces = (80 - len(msg)) * ' '
        msg = ''.join((msg, spaces))
        print(msg, end='\r')
        l = layer[1]
        if l['layer_type'] == 'group' and group_empty:
            empty = bpy.data.objects.new(layer[0], None)
            bpy.context.scene.objects.link(empty)
            empty.layers = layers
            parent = l['parent']
            group_object(empty, parent, root_name,
                         root_group, group_empty, group_group)
        else:
            loc_x = (-image_width / 2 + l['width'] / 2 + l['x']) / scale_fac
            loc_y = offset * i
            loc_z = (image_height - l['height'] / 2 - l['y']) / scale_fac
            bpy.ops.mesh.primitive_plane_add(location=(loc_x, loc_y, loc_z),
                                             rotation=(0.5 * math.pi, 0, 0))
            plane = bpy.context.object
            plane.layers = layers
            plane.name = layer[0]
            # Add UV's and add image to UV's
            img_path = os.path.join(img_dir, ''.join((layer[0], '.png')))
            img = bpy.data.images.load(img_path)
            plane.data.uv_textures.new()
            plane.data.uv_textures[0].data[0].image = img
            # Scale plane according to image size
            scale_x = l['width'] / scale_fac / 2
            scale_y = l['height'] / scale_fac / 2
            plane.scale = (scale_x, scale_y, 1)
            # Apply rotation and scale
            bpy.ops.object.transform_apply(rotation=True, scale=True)
            # Create material
            tex = bpy.data.textures.new(layer[0], 'IMAGE')
            tex.use_mipmap = use_mipmap
            tex.image = img
            mat = bpy.data.materials.new(layer[0])
            mat.use_shadeless = use_shadeless
            mat.use_transparency = use_transparency
            if use_transparency:
                mat.alpha = 0.0
            mat.texture_slots.create(0)
            mat.texture_slots[0].texture = tex
            if use_transparency:
                mat.texture_slots[0].use_map_alpha = True
            plane.data.materials.append(mat)
            parent = l['parent']
            group_object(plane, parent, root_name,
                         root_group, group_empty, group_group)
            i += 1


def get_current_layer():
    '''
    Return the first layer that is active.
    '''

    for i, l in enumerate(bpy.context.scene.layers):
        if l:
            return i


# Actual import operator.
class ImportPsdAsPlanes(bpy.types.Operator, ImportHelper):

    '''Import PSD as planes'''
    bl_idname = 'import_scene.psd'
    bl_label = 'Import PSD as planes'
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

    filename_ext = '.psd'
    filter_glob = StringProperty(default='*.psd', options={'HIDDEN'})
    offset = FloatProperty(
        name='Offset',
        description='Offset planes by this amount on the Y axis',
        default=0.01)
    hidden_layers = BoolProperty(
        name='Import hidden layers',
        description='Also import hidden layers',
        default=False)
    scale_fac = FloatProperty(
        name='Scale',
        description='Scale of the planes (how many pixels make up 1 Blender unit)',
        default=100)
    use_mipmap = BoolProperty(
        name='MIP Map',
        description='Use auto-generated MIP maps for the images. Turning this off leads to sharper rendered images',
        default=False)
    group_group = BoolProperty(
        name='Group',
        description='Put the images in groups',
        default=True)
    group_empty = BoolProperty(
        name='Empty',
        description='Parent the images to an empty',
        default=True)
    group_layers = BoolProperty(
        name='Layers',
        description='Put the images on separate layers per PSD',
        default=False)

    def draw(self, context):
        layout = self.layout

        # Import options
        box = layout.box()
        box.label('Import options', icon='FILTER')
        col = box.column()
        col.prop(self, 'hidden_layers', icon='GHOST_ENABLED')
        col.prop(self, 'offset')
        col.prop(self, 'scale_fac')
        # Grouping options
        box = layout.box()
        box.label('Grouping', icon='GROUP')
        row = box.row(align=True)
        # row.prop(self, 'group_group', toggle=True)
        row.prop(self, 'group_empty', toggle=True)
        row.prop(self, 'group_layers', toggle=True)
        # Material options (not much for now)
        box = layout.box()
        box.label('Material options', icon='MATERIAL_DATA')
        col = box.column()
        if self.use_mipmap:
            mipmap_icon = 'ANTIALIASED'
        else:
            mipmap_icon = 'ALIASED'
        col.prop(self, 'use_mipmap', icon=mipmap_icon, toggle=True)

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
                layer_info, image_size, png_dir = parse_psd(self, psd_file)
            except TypeError:   # None is returned, so something went wrong.
                msg = "Something went wrong. '{f}' is not imported!".format(f=f.name)
                self.report({'ERROR'}, msg)
                print("*** {}".format(msg))
                continue
            # layer_info, image_size, png_dir = parse_psd(self, psd_file)
            create_objects(self, layer_info, image_size,
                           png_dir, f.name, layers)
            print(''.join(('  Done', 74 * ' ')))
        print('\nFiles imported in {s:.2f} seconds'.format(
            s=time.time() - start_time))

        context.user_preferences.edit.use_enter_edit_mode = editmode

        return {'FINISHED'}
