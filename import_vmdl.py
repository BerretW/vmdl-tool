# vmdl_plugin/import_vmdl.py

import bpy
import os
import json
import zipfile
import tempfile
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector, Quaternion

class VMDL_OT_import_package(bpy.types.Operator, ImportHelper):
    bl_idname = "vmdl.import_package"
    bl_label = "Import VMDL Package"
    filename_ext = ".vmdl.pkg"
    filter_glob: bpy.props.StringProperty(default="*.vmdl.pkg", options={'HIDDEN'})

    def execute(self, context):
        if not os.path.isfile(self.filepath):
            self.report({'ERROR'}, "Soubor neexistuje.")
            return {'CANCELLED'}

        temp_dir = tempfile.mkdtemp(prefix="vmdl_import_")
        with zipfile.ZipFile(self.filepath, 'r') as zf:
            zf.extractall(temp_dir)

        base_name = os.path.splitext(os.path.basename(self.filepath))[0]
        json_path = os.path.join(temp_dir, f"{base_name}.vmdl.json")
        if not os.path.exists(json_path):
            self.report({'ERROR'}, "Chybí .vmdl.json v balíku.")
            return {'CANCELLED'}

        with open(json_path, 'r') as f:
            vmdl_data = json.load(f)

        root_obj = bpy.data.objects.new(vmdl_data['name'] + "_VMDL", None)
        root_obj.empty_display_type = 'PLAIN_AXES'
        root_obj["vmdl_type"] = "ROOT"
        context.collection.objects.link(root_obj)

        def import_glb(filename):
            full_path = os.path.join(temp_dir, filename)
            bpy.ops.import_scene.gltf(filepath=full_path)
            return context.selected_objects[0] if context.selected_objects else None

        mesh_obj = import_glb(vmdl_data['model_file'])
        if mesh_obj:
            mesh_obj["vmdl_type"] = "MESH"
            mesh_obj.parent = root_obj

        if 'collider_file' in vmdl_data:
            collider_obj = import_glb(vmdl_data['collider_file'])
            if collider_obj:
                collider_obj["vmdl_type"] = "COLLIDER"
                collider_obj.parent = root_obj
                collider_obj.vmdl_collider.collider_type = vmdl_data.get('collider_type', '')

        for anim in vmdl_data.get('animations', []):
            import_glb(anim['file'])

        for mnt in vmdl_data.get("mountpoints", []):
            bpy.ops.object.empty_add(type='ARROWS', location=Vector(mnt['position']))
            mount_obj = context.active_object
            mount_obj.name = mnt['name']
            mount_obj["vmdl_type"] = "MOUNTPOINT"
            mount_obj.parent = root_obj
            mount_obj.vmdl_mountpoint.forward_vector = Vector(mnt['forward'])
            mount_obj.vmdl_mountpoint.up_vector = Vector(mnt['up'])
            quat = Quaternion(mnt['rotation'])
            mount_obj.rotation_mode = 'QUATERNION'
            mount_obj.rotation_quaternion = quat

        self.report({'INFO'}, f"Import dokončen: {vmdl_data['name']}")
        return {'FINISHED'}
