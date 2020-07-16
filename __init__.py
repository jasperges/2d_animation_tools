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
    "name": "Import PSD layers as planes",
    "author": "Jasper van Nieuwenhuizen",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "File > Import > Import PSD as planes",
    "description": "Import the layers of a PSD file as planes.",
    "warning": "wip",
    "wiki_url": "https://github.com/jasperges/2d_animation_tools",
    "tracker_url": "https://github.com/jasperges/2d_animation_tools/issues",
    "support": 'COMMUNITY',
    "category": "Import-Export"}


if "bpy" in locals():
    import importlib
    if "io_import_psd_layers_as_planes" in locals():
        importlib.reload(io_import_psd_layers_as_planes)


import bpy
from . import io_import_psd_layers_as_planes


def menu_func_import(self, context):
    self.layout.operator(
        io_import_psd_layers_as_planes.ImportPsdAsPlanes.bl_idname,
        text="Import PSD as planes", icon='IMAGE_DATA')


def register():
    bpy.utils.register_class(io_import_psd_layers_as_planes.ImportPsdAsPlanes)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.VIEW3D_MT_image_add.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(io_import_psd_layers_as_planes.ImportPsdAsPlanes)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.VIEW3D_MT_image_add.remove(menu_func_import)


if __name__ == "__main__":
    register()
