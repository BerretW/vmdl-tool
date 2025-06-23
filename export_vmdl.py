import bpy
import json
import os
import zipfile
import shutil
from bpy_extras.io_utils import ExportHelper

try:
    # ZMĚNA: Importujeme přímo export_main, abychom měli jistotu
    from io_scene_gltf2 import export_main
except ImportError:
    export_main = None

class VMDLExportProperties(bpy.types.PropertyGroup):
    pass

class VMDL_OT_export_package(bpy.types.Operator, ExportHelper):
    bl_idname = "vmdl.export_package"
    bl_label = "Export VMDL Package"
    filename_ext = ".vmdl.pkg"
    filter_glob: bpy.props.StringProperty(default="*.vmdl.pkg", options={'HIDDEN'})

    def execute(self, context):
        if not export_main:
            self.report({'ERROR'}, "Standardní glTF 2.0 addon není aktivní.")
            return {'CANCELLED'}

        root_obj = context.active_object
        if not root_obj or root_obj.get("vmdl_type") != "ROOT":
            test_obj = context.active_object
            parent_found = False
            while test_obj and test_obj.parent:
                if test_obj.parent.get("vmdl_type") == "ROOT":
                    root_obj = test_obj.parent
                    parent_found = True
                    break
                test_obj = test_obj.parent
            if not parent_found:
                self.report({'ERROR'}, "Musíte vybrat VMDL Root objekt (nebo jeho část) pro export.")
                return {'CANCELLED'}

        base_name = os.path.splitext(os.path.basename(self.filepath))[0].replace(".vmdl", "")
        temp_dir = bpy.app.tempdir + os.sep + "vmdl_export_" + base_name

        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        vmdl_data = {'name': base_name, 'version': 2.6}
        mat_files = []
        texture_files = set()
        
        all_vmdl_objects = []
        def gather_objects(obj):
            all_vmdl_objects.append(obj)
            for child in obj.children:
                gather_objects(child)
        gather_objects(root_obj)

        mesh_objects = [obj for obj in all_vmdl_objects if obj.type == 'MESH' and obj.get("vmdl_type") == "MESH"]
        if not mesh_objects:
            self.report({'ERROR'}, "VMDL Root neobsahuje žádný MESH objekt.")
            shutil.rmtree(temp_dir); return {'CANCELLED'}

        armature_obj = next((obj for obj in all_vmdl_objects if obj.type == 'ARMATURE'), None)
        
        vmdl_data['hierarchy'] = []
        for obj in all_vmdl_objects:
            if obj != root_obj and obj.parent:
                vmdl_data['hierarchy'].append({'child': obj.name, 'parent': obj.parent.name})

        # EXPORT MESH (všech najednou)
        vmdl_data['model_file'] = f"{base_name}.glb"
        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objects:
            obj.select_set(True)
        if armature_obj:
            armature_obj.select_set(True)
        
        export_path = os.path.join(temp_dir, vmdl_data['model_file'])
        export_settings = {
            "filepath": export_path, "use_selection": True, "export_format": 'GLB',
            "export_attributes": True, "export_image_format": 'AUTO'
        }
        
        # ZMĚNA: Používáme správnou funkci 'export_main.save'
        export_main.save(context, export_settings)

        # EXPORT MATERIÁLŮ
        all_materials = set()
        for obj in mesh_objects:
            for mat_slot in obj.material_slots:
                if mat_slot.material:
                    all_materials.add(mat_slot.material)

        for i, mat in enumerate(all_materials):
            if not hasattr(mat, "vmdl_shader"): continue

            shader_props = mat.vmdl_shader
            mat_name = f"{base_name}_mat_{i}_{mat.name}.mat.json"
            mat_files.append(mat_name)
            
            mat_data = {'shader': shader_props.shader_name, 'parameters': {}, 'textures': {}}
            for param in shader_props.parameters:
                if param.type == "float": mat_data['parameters'][param.name] = param.float_value
                elif param.type == "vector4": mat_data['parameters'][param.name] = list(param.vector_value)
                elif param.type == "bool": mat_data['parameters'][param.name] = param.bool_value
            
            for tex in shader_props.textures:
                if tex.image and tex.image.filepath:
                    path = bpy.path.abspath(tex.image.filepath)
                    if os.path.exists(path):
                        tex_basename = os.path.basename(path)
                        mat_data['textures'][tex.name] = tex_basename
                        texture_files.add(path)

            with open(os.path.join(temp_dir, mat_name), 'w') as f:
                json.dump(mat_data, f, indent=2)

        vmdl_data['materials'] = mat_files

        # ZÁPIS HLAVNÍHO JSON
        with open(os.path.join(temp_dir, f"{base_name}.vmdl.json"), 'w') as f:
            json.dump(vmdl_data, f, indent=2)

        for tex_path in texture_files:
            if os.path.exists(tex_path):
                shutil.copy(tex_path, os.path.join(temp_dir, os.path.basename(tex_path)))

        with zipfile.ZipFile(self.filepath, 'w') as zf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    zf.write(os.path.join(root, file), arcname=file)

        shutil.rmtree(temp_dir)
        self.report({'INFO'}, f"Export dokončen do {self.filepath}")
        return {'FINISHED'}