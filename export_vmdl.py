# ================= export_vmdl.py =================
import bpy
import json
import os
import zipfile
import shutil
from bpy_extras.io_utils import ExportHelper

try:
    from io_scene_gltf2 import export_main
except ImportError:
    export_main = None

class VMDLExportProperties(bpy.types.PropertyGroup):
    export_directory: bpy.props.StringProperty(
        name="Export Directory",
        subtype='DIR_PATH',
        default="//"
    )
    version: bpy.props.FloatProperty(
        name="VMDL Version",
        default=2.6,
        description="Version number for VMDL JSON"
    )

class VMDL_OT_export_package(bpy.types.Operator, ExportHelper):
    bl_idname = "vmdl.export_package"
    bl_label = "Export VMDL Package"
    filename_ext = ".vmdl.pkg"
    filter_glob: bpy.props.StringProperty(default="*.vmdl.pkg", options={'HIDDEN'})

    def invoke(self, context, event):
        props = context.scene.vmdl_export
        # default filepath to scene name in chosen directory
        directory = bpy.path.abspath(props.export_directory)
        self.filepath = os.path.join(directory, context.scene.name + self.filename_ext)
        return super().invoke(context, event)

    def execute(self, context):
        root_obj = context.active_object
        # auto-find root if selection inside hierarchy
        if not root_obj or root_obj.get("vmdl_type") != "ROOT":
            node = root_obj
            while node and node.parent:
                node = node.parent
                if node.get("vmdl_type") == "ROOT":
                    root_obj = node
                    break
            else:
                self.report({'ERROR'}, "Musíte vybrat VMDL Root objekt pro export.")
                return {'CANCELLED'}

        base_name = os.path.splitext(os.path.basename(self.filepath))[0]
        temp_dir = os.path.join(bpy.app.tempdir, f"vmdl_export_{base_name}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)

        vmdl_data = {'name': base_name, 'version': context.scene.vmdl_export.version}
        mat_files = []
        texture_files = set()

        all_objs = []
        def gather(o):
            all_objs.append(o)
            for c in o.children:
                gather(c)
        gather(root_obj)

        mesh_objs = [o for o in all_objs if o.type=='MESH' and o.get("vmdl_type")=="MESH"]
        if not mesh_objs:
            self.report({'ERROR'}, "VMDL Root neobsahuje žádný MESH objekt.")
            shutil.rmtree(temp_dir)
            return {'CANCELLED'}

        arm = next((o for o in all_objs if o.type=='ARMATURE'), None)
        vmdl_hierarchy = []
        for o in all_objs:
            if o!=root_obj and o.parent:
                vmdl_hierarchy.append({'child': o.name, 'parent': o.parent.name})

        vmdl_data['hierarchy'] = vmdl_hierarchy
        vmdl_data['model_file'] = f"{base_name}.glb"

        # export glb
        bpy.ops.object.select_all(action='DESELECT')
        for o in mesh_objs: o.select_set(True)
        if arm: arm.select_set(True)
        export_path = os.path.join(temp_dir, vmdl_data['model_file'])
        export_settings = {
            'filepath': export_path,
            'use_selection': True,
            'export_format': 'GLB',
            'export_attributes': True,
            'export_image_format': 'AUTO'
        }
        try:
            if export_main and hasattr(export_main, 'save'):
                export_main.save(context, export_settings)
            else:
                bpy.ops.export_scene.gltf(**export_settings)
        except Exception as e:
            self.report({'ERROR'}, f"Export glTF selhal: {e}")
            shutil.rmtree(temp_dir)
            return {'CANCELLED'}

        # export materials and textures
        mats = set(m for o in mesh_objs for m in o.data.materials if m)
        for i, mat in enumerate(mats):
            props = getattr(mat, 'vmdl_shader', None)
            if not props: continue
            fname = f"{base_name}_mat_{i}_{mat.name}.mat.json"
            mat_files.append(fname)
            data = {'shader': props.shader_name, 'parameters':{}, 'textures':{}}
            for p in props.parameters:
                val = getattr(p, p.type+'_value') if hasattr(p, p.type+'_value') else None
                data['parameters'][p.name] = list(val) if isinstance(val, (list, tuple)) else val
            for t in props.textures:
                img = getattr(t, 'image', None)
                if img and img.filepath:
                    path = bpy.path.abspath(img.filepath)
                    if os.path.exists(path):
                        data['textures'][t.name] = os.path.basename(path)
                        texture_files.add(path)
            with open(os.path.join(temp_dir, fname), 'w') as f:
                json.dump(data, f, indent=2)
        vmdl_data['materials'] = mat_files

        # write main JSON
        with open(os.path.join(temp_dir, f"{base_name}.vmdl.json"), 'w') as f:
            json.dump(vmdl_data, f, indent=2)

        # copy textures
        for path in texture_files:
            shutil.copy(path, os.path.join(temp_dir, os.path.basename(path)))

        # package
        try:
            with zipfile.ZipFile(self.filepath, 'w') as zf:
                for root, dirs, files in os.walk(temp_dir):
                    for fn in files:
                        zf.write(os.path.join(root, fn), arcname=fn)
        finally:
            shutil.rmtree(temp_dir)

        self.report({'INFO'}, f"Export úspěšný: {self.filepath}")
        return {'FINISHED'}
