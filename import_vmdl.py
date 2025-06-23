import bpy
import os
import json
import zipfile
import tempfile
import shutil
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector, Quaternion

from .shader_definitions import SHADER_DEFINITIONS
from .shader_materials import setup_principled_node_graph
from .vmdl_utils import VMDL_OT_create_vmdl_object # Funkce z minulé opravy

# (funkce create_and_setup_vmdl_material z minulé verze zde zůstává beze změny)
def create_and_setup_vmdl_material(mat_data, temp_dir, report_func):
    shader_name = mat_data.get('shader')
    if not shader_name or shader_name not in SHADER_DEFINITIONS:
        report_func({'WARNING'}, f"Shader '{shader_name}' v presetu neexistuje. Materiál bude přeskočen.")
        return None, None
    base_mat_name = os.path.splitext(os.path.splitext(os.path.basename(mat_data['filename']))[0])[0]
    lookup_name = base_mat_name.split('_')[-1] if '_mat_' in base_mat_name else base_mat_name
    mat = bpy.data.materials.new(name=f"VMDL_{lookup_name}")
    mat.use_nodes = True
    mat.vmdl_shader.shader_name = shader_name
    shader_def = SHADER_DEFINITIONS[shader_name]
    mat.vmdl_shader.parameters.clear(); mat.vmdl_shader.textures.clear()
    for param_def in shader_def.get("parameters", []):
        new_param = mat.vmdl_shader.parameters.add()
        new_param.name = param_def["name"]; new_param.type = param_def["type"]
        if new_param.type == "float": new_param.float_value = param_def["default"]
        elif new_param.type == "vector4": new_param.vector_value = param_def["default"]
        elif new_param.type == "bool": new_param.bool_value = param_def["default"]
    for tex_def in shader_def.get("textures", []):
        new_tex = mat.vmdl_shader.textures.add(); new_tex.name = tex_def["name"]
    shader_props = mat.vmdl_shader
    for param_name, param_value in mat_data.get('parameters', {}).items():
        if param_name in shader_props.parameters:
            param_prop = shader_props.parameters[param_name]
            if param_prop.type == 'float': param_prop.float_value = param_value
            elif param_prop.type == 'vector4': param_prop.vector_value = param_value
            elif param_prop.type == 'bool': param_prop.bool_value = param_value
    for tex_name, tex_filename in mat_data.get('textures', {}).items():
        if tex_name in shader_props.textures:
            tex_prop = shader_props.textures[tex_name]
            image_path = os.path.join(temp_dir, tex_filename)
            if os.path.exists(image_path):
                try:
                    image = bpy.data.images.load(image_path, check_existing=True)
                    tex_prop.image = image
                except Exception as e:
                    report_func({'WARNING'}, f"Nelze načíst texturu {image_path}: {e}")
    setup_principled_node_graph(mat)
    return lookup_name, mat

class VMDL_OT_import_package(bpy.types.Operator, ImportHelper):
    bl_idname = "vmdl.import_package"
    bl_label = "Import VMDL Package"
    filename_ext = ".vmdl.pkg"
    filter_glob: bpy.props.StringProperty(default="*.vmdl.pkg", options={'HIDDEN'})

    def execute(self, context):
        temp_dir = tempfile.mkdtemp(prefix="vmdl_import_")
        try:
            with zipfile.ZipFile(self.filepath, 'r') as zf:
                zf.extractall(temp_dir)

            base_name = os.path.splitext(os.path.basename(self.filepath))[0].replace('.vmdl', '')
            json_path = os.path.join(temp_dir, f"{base_name}.vmdl.json")
            if not os.path.exists(json_path):
                self.report({'ERROR'}, "Chybí .vmdl.json v balíku."); return {'CANCELLED'}

            with open(json_path, 'r') as f:
                vmdl_data = json.load(f)

            def import_glb(filename):
                # ... (funkce beze změny) ...
                full_path = os.path.join(temp_dir, filename)
                if not os.path.exists(full_path):
                    self.report({'WARNING'}, f"Soubor {filename} v balíčku neexistuje."); return []
                objects_before = set(context.scene.objects)
                bpy.ops.import_scene.gltf(filepath=full_path, loglevel=50)
                objects_after = set(context.scene.objects)
                return list(objects_after - objects_before)

            # --- KROK 1: Vytvoříme VMDL materiály ---
            vmdl_materials_map = {}
            if 'materials' in vmdl_data:
                for mat_filename in vmdl_data['materials']:
                    mat_path = os.path.join(temp_dir, mat_filename)
                    if not os.path.exists(mat_path): continue
                    with open(mat_path, 'r') as f: mat_data = json.load(f)
                    mat_data['filename'] = mat_filename
                    lookup_name, new_material = create_and_setup_vmdl_material(mat_data, temp_dir, self.report)
                    if new_material:
                        vmdl_materials_map[lookup_name] = new_material

            # --- KROK 2: Importujeme VŠECHNY objekty z GLB najednou ---
            imported_parts = import_glb(vmdl_data['model_file'])
            
            # Slovník pro rychlé nalezení objektů podle jména
            imported_obj_map = {obj.name: obj for obj in imported_parts}
            
            # --- KROK 3: Přejmenujeme a nastavíme VMDL vlastnosti, ale zatím NEPAIPARENTUJEME ---
            for original_name, obj in imported_obj_map.items():
                # Nastavení VMDL typu a dalších vlastností
                # Můžeme si informaci o typu uložit i do exportu, pokud chceme rozlišit MESH/COLLIDER/atd.
                # Prozatím předpokládáme, že vše z GLB je MESH nebo ARMATURE
                if obj.type == 'MESH':
                    obj["vmdl_type"] = "MESH"
                    # Aplikujeme materiály
                    for slot in obj.material_slots:
                        if not slot.material: continue
                        original_mat_name = slot.material.name.split('.')[0]
                        if original_mat_name in vmdl_materials_map:
                            old_mat = slot.material
                            slot.material = vmdl_materials_map[original_mat_name]
                            bpy.data.materials.remove(old_mat)

            # --- KROK 4: Sestavíme hierarchii podle uložených dat ---
            if 'hierarchy' in vmdl_data:
                for link in vmdl_data['hierarchy']:
                    child_name = link['child']
                    parent_name = link['parent']
                    
                    if child_name in imported_obj_map and parent_name in imported_obj_map:
                        child_obj = imported_obj_map[child_name]
                        parent_obj = imported_obj_map[parent_name]
                        child_obj.parent = parent_obj
            
            # Najdeme hlavní ROOT objekt (ten, který nemá parenta) a přejmenujeme ho
            root_obj = next((obj for obj in imported_parts if not obj.parent), None)
            if root_obj:
                 root_obj.name = vmdl_data['name'] + "_VMDL"
                 root_obj["vmdl_type"] = "ROOT"
            
            self.report({'INFO'}, f"Import '{vmdl_data['name']}' dokončen s hierarchií.")
            return {'FINISHED'}

        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)