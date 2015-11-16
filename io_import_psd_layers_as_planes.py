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
import random
import string
from collections import defaultdict, OrderedDict
import psd_tools
import bpy
from mathutils import Vector
from bpy.props import (BoolProperty,
                       StringProperty,
                       FloatProperty,
                       CollectionProperty)
from bpy_extras.io_utils import (ImportHelper,
                                 orientation_helper_factory,
                                 axis_conversion)


def generate_random_id(length=8):
    chars = ''.join((string.digits,
                     string.ascii_lowercase,
                     string.ascii_uppercase))
    return ''.join(random.choice(chars) for _ in range(length))


def parse_psd(self, psd_file):
    '''
    parse_psd(string psd_file) -> dict layer_info

        Reads psd_file and exports all layers to png's.
        Returns a dictionary with the positions and order of the layers and
        the size of the image.

        string psd_file - the filepath of the psd file
    '''

    hidden_layers = self.hidden_layers

    def parse_layer(layer, parent='', children=defaultdict(list), layer_list=OrderedDict()):
        if isinstance(layer, psd_tools.user_api.psd_image.PSDImage):
            parent = psd_name
        else:
            if ((not hidden_layers and not layer.visible_global) or
                    (not hasattr(layer, 'layers') or not layer.layers)):
                parents.pop()
                return
        for i, sub_layer in enumerate(layer.layers):
            if not hidden_layers and not sub_layer.visible_global:
                continue
            sub_layer_name = bpy.path.clean_name(sub_layer.name)
            if not parent in parents:
                parents.append(parent)
            random.seed(''.join((psd_file, ''.join(parents), sub_layer_name, str(i))))
            sub_layer_id = generate_random_id()
            name = '{name}_{id}'.format(name=sub_layer_name, id=sub_layer_id)
            if isinstance(sub_layer, psd_tools.Layer):
                # This is a normal layer we sould export it as a png
                png_file = os.path.join(png_dir, ''.join((name, '.png')))
                layer_image = sub_layer.as_PIL()
                layer_image.save(png_file)
                width = sub_layer.bbox.width
                height = sub_layer.bbox.height
                x = sub_layer.bbox.x1
                y = sub_layer.bbox.y1
                layer_list[name] = {
                    'width': width,
                    'height': height,
                    'x': x,
                    'y': y,
                    'layer_type': 'layer',
                    'layer_id': sub_layer_id,
                    'parents': parents.copy()
                    }
            else:
                # This is a layer group
                layer_list[name] = {
                    'layer_type': 'group',
                    'layer_id': sub_layer_id,
                    'parents': parents.copy()
                    }
            children[parent].append(name)
            parse_layer(sub_layer, parent=name, children=children, layer_list=layer_list)
        for parent in children:
            p = layer_list.get(parent)
            if p:
                p['children'] = children[parent]
        return layer_list

    print('\nparsing: {}'.format(psd_file))
    psd_dir, psd_name = os.path.split(psd_file)
    psd_name = os.path.splitext(psd_name)[0]
    png_dir = os.path.join(psd_dir, '_'.join((psd_name, 'pngs')))
    if not os.path.isdir(png_dir):
        os.mkdir(png_dir)
    psd = psd_tools.PSDImage.load(psd_file)
    parents = []
    layer_info = parse_layer(psd)
    i = 0
    for info in layer_info.values():
        if info['layer_type'] == 'layer':
            info['offset'] = i
            i += 1
    image_size = (psd.bbox.width, psd.bbox.height)

    return (layer_info, image_size, png_dir)


def create_objects(self, layer_info, image_size, img_dir, psd_name, layers, import_id):
    '''
    create_objects(class self, list layer_info, tuple image_size,
                  string img_dir, string psd_name, list layers, string import_id)

        Imports all png images that are in layer_info from img_dir
        into Blender as planes and places these planes correctly.

        class self        - the import operator class
        list layer_info   - info about the layer like position and index
        tuple image_size  - the witdth and height of the image
        string img_dir    - the path to the png images
        string psd_name   - the name of the psd file
        listOfBool layers - the layer(s) to put the objects on
        string import_id  - used to identify this import
    '''

    def get_parent(parent_name, import_id):
        for obj in bpy.context.scene.objects:
            if parent_name in obj.name and obj['import_id'] == import_id:
                return obj

    def group_object(obj, parent, root_group, group_empty, group_group, import_id):
        if group_empty:
            bpy.context.scene.update()
            parent_empty = get_parent(parent, import_id)
            matrix_parent_inverse = parent_empty.matrix_world.inverted()
            obj.parent = parent_empty
            obj.matrix_parent_inverse = matrix_parent_inverse
        if group_group:
            # Only put objects in one group per psd file
            try:
                root_group.objects.link(obj)
            except RuntimeError:
                pass

    def get_transforms(layer):
        loc_x = (-image_width / 2 + layer['width'] / 2 + layer['x']) / scale_fac
        loc_y = offset * layer['offset']
        loc_z = (image_height - layer['height'] / 2 - layer['y']) / scale_fac
        scale_x = layer['width'] / scale_fac / 2
        scale_y = layer['height'] / scale_fac / 2
        scale_z = 1
        location = Vector((loc_x, loc_y, loc_z))
        scale = Vector((scale_x, scale_y, scale_z))
        return (location, scale)

    def sum_vectors(vectors):
        vector_sum = Vector()
        for v in vectors:
            vector_sum += v
        return vector_sum

    def get_children_median(obj):
        children = obj.get('children')
        if not children:
            return Vector()
        child_locations = []
        children_count = 0
        for child in children:
            if layer_info[child]['layer_type'] == 'layer':
                children_count += 1
                child_locations.append(Vector(get_transforms(layer_info[child])[0]))
        if children_count:
            return sum_vectors(child_locations) / children_count
        else:
            return Vector()

    def create_image():
        img_path = os.path.join(img_dir, ''.join((layer, '.png')))
        # Check if image already exists
        for i in bpy.data.images:
            if layer in i.name and (i.filepath == img_path or i.filepath == bpy.path.relpath(img_path)):
                i.reload()
                return i
        # Image not found, create a new one
        img = bpy.data.images.load(img_path)
        if rel_path:
            img.filepath = bpy.path.relpath(img.filepath)
        return img

    def create_texture(name, img):
        # Check if texture already exists
        for t in bpy.data.textures:
            if name in t.name and t.type == 'IMAGE' and t.image == img:
                return t
        # Texture not found, create a new one
        tex = bpy.data.textures.new(name, 'IMAGE')
        tex.use_mipmap = use_mipmap
        tex.image = img
        return tex

    def create_material(name, tex):
        # Check if material already exists
        for m in bpy.data.materials:
            if name in m.name and m.texture_slots:
                for ts in m.texture_slots:
                    if ts:
                        if ts.texture == tex:
                            return m
        # Material not found, create a new one
        mat = bpy.data.materials.new(name)
        mat.use_shadeless = use_shadeless
        mat.use_transparency = use_transparency
        if use_transparency:
            mat.alpha = 0.0
        mat.texture_slots.create(0)
        mat.texture_slots[0].texture = tex
        if use_transparency:
            mat.texture_slots[0].use_map_alpha = True
        return mat

    def create_textured_plane(name, transforms, global_matrix, import_id, img_path):
        # Create plane with 'forward: -y' and 'up: z'
        # Then use axis conversion to change to orientation specified by user
        loc, scale = transforms
        verts = [(-scale.x, 0, scale.y),
                 (scale.x, 0, scale.y),
                 (scale.x, 0, -scale.y),
                 (-scale.x, 0, -scale.y)]
        verts = [global_matrix * Vector(v) for v in verts]
        faces = [(3, 2, 1, 0)]
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], faces)
        plane = bpy.data.objects.new(name, mesh)
        bpy.context.scene.objects.link(plane)
        plane.location = global_matrix * loc
        plane.layers = layers
        plane['import_id'] = import_id
        # Add UV's and add image to UV's
        img = create_image()
        plane.data.uv_textures.new()
        plane.data.uv_textures[0].data[0].image = img
        # Create and assign material
        tex = create_texture(name, img)
        mat = create_material(name, tex)
        plane.data.materials.append(mat)
        return plane

    rel_path = self.rel_path
    group_empty = self.group_empty
    group_group = self.group_group
    axis_forward = self.axis_forward
    axis_up = self.axis_up
    offset = self.offset
    scale_fac = self.scale_fac
    use_mipmap = self.use_mipmap
    use_shadeless = True
    use_transparency = True

    image_width = image_size[0]
    image_height = image_size[1]

    global_matrix = axis_conversion(from_forward='-Y',
                                    from_up='Z',
                                    to_forward=axis_forward,
                                    to_up=axis_up).to_4x4()

    root_name = os.path.splitext(psd_name)[0]
    if group_group:
        root_group = bpy.data.groups.new(root_name)
    if group_empty:
        root_empty = bpy.data.objects.new(root_name, None)
        bpy.context.scene.objects.link(root_empty)
        root_empty.layers = layers
        root_empty['import_id'] = import_id
        try:
            root_group.objects.link(root_empty)
        except NameError:
            pass
    for layer, info in layer_info.items():
        msg = '  - processing: {layer}'.format(layer=layer)
        spaces = (80 - len(msg)) * ' '
        msg = ''.join((msg, spaces))
        print(msg, end='\r')
        name = layer
        parent = info['parents'][-1]
        if parent != root_name:
            parent = '_'.join(parent.split('_')[:-1])
        if info['layer_type'] == 'group' and group_empty:
            if name != root_name:
                name = '_'.join(name.split('_')[:-1])
            empty = bpy.data.objects.new(name, None)
            bpy.context.scene.objects.link(empty)
            empty.layers = layers
            empty['import_id'] = import_id
            # Position empty at median of children
            median = get_children_median(info)
            empty.location = global_matrix * median
            group_object(empty, parent, root_group, group_empty, group_group, import_id)
        else:
            transforms = get_transforms(info)
            img_path = os.path.join(img_dir, ''.join((layer, '.png')))
            name = '_'.join(name.split('_')[:-1])
            plane = create_textured_plane(name, transforms, global_matrix, import_id, img_path)
            group_object(plane, parent, root_group, group_empty, group_group, import_id)

    if group_empty:
        bpy.ops.object.select_all(action='DESELECT')
        root_empty.select = True
        bpy.context.scene.objects.active = root_empty
        # Move root empty to cursor position
        root_empty.location = bpy.context.scene.cursor_location


def get_current_layer():
    '''
    Return the first layer that is active.
    '''

    for i, l in enumerate(bpy.context.scene.layers):
        if l:
            return i

IOPSDOrientationHelper = orientation_helper_factory("IOPSDOrientationHelper",
                                                    axis_forward='-Y',
                                                    axis_up='Z')

# Actual import operator.
class ImportPsdAsPlanes(bpy.types.Operator, ImportHelper, IOPSDOrientationHelper):

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
    rel_path = BoolProperty(
        name='Relative Path',
        description='Select the file relative to the blend file',
        default=True)

    def draw(self, context):
        layout = self.layout

        # Import options
        layout.prop(self, 'rel_path')
        box = layout.box()
        box.label('Import options', icon='FILTER')
        col = box.column()
        col.prop(self, 'hidden_layers', icon='GHOST_ENABLED')
        col.prop(self, 'axis_forward')
        col.prop(self, 'axis_up')
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
        random.seed()
        import_id = generate_random_id()

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
                           png_dir, f.name, layers, import_id)
            print(''.join(('  Done', 74 * ' ')))
        print('\nFiles imported in {s:.2f} seconds'.format(
            s=time.time() - start_time))

        context.user_preferences.edit.use_enter_edit_mode = editmode

        return {'FINISHED'}
