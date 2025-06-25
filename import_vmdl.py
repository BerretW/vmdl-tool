import bpy
import json
import os
import tempfile
import zipfile
from bpy_extras.io_utils import ImportHelper

def apply_material_properties(mat, mat_data, temp_dir):
    if not mat or not mat_data:
        return

    shader_props = mat.vmdl_shader
    
    for name, value in mat_data.get('parameters', {}).items():
        if name in shader_props.parameters:
            param = shader_props.parameters[name]
            if param.type == 'float': param.float_value = value
            elif param.type == 'vector4': param.vector_value = value
            elif param.type == 'bool': param.bool_value = value
    
    for vmdl_slot_name, image_filename in mat_data.get('textures', {}).items():
        if vmdl_slot_name in shader_props.textures and image_filename:
            texture_path = os.path.join(temp_dir, 'tex', image_filename)
            
            if os.path.exists(texture_path):
                try:
                    loaded_image = bpy.data.images.load(texture_path, check_existing=True)
                    shader_props.textures[vmdl_slot_name].image = loaded_image
                    print(f"INFO: Pro '{mat.name}' načtena textura '{image_filename}' do slotu '{vmdl_slot_name}'.")
                except Exception as e:
                    print(f"CHYBA: Nepodařilo se načíst texturu '{texture_path}': {e}")
            else:
                print(f"VAROVÁNÍ: Textura '{texture_path}' nebyla v archivu nalezena.")

    from .shader_materials import setup_principled_node_graph
    setup_principled_node_graph(mat)


class VMDL_OT_import_vmdl(bpy.types.Operator, ImportHelper):
    bl_idname = "vmdl.import_vmdl"
    bl_label = "Import VMDL Archive"
    filename_ext = ".vmdl"
    filter_glob: bpy.props.StringProperty(default="*.vmdl", options={'HIDDEN'})

    def execute(self, context):
        vmdl_metadata = None
        
        try:
            temp_dir_obj = tempfile.TemporaryDirectory()
            tempdir = temp_dir_obj.name

            with zipfile.ZipFile(self.filepath, 'r') as zf:
                zf.extractall(tempdir)
            
            temp_glb_path = os.path.join(tempdir, 'model.glb')
            temp_json_path = os.path.join(tempdir, 'metadata.json')

            # Zjistíme materiály PŘED importem
            mats_before = set(bpy.data.materials)
            
            bpy.ops.import_scene.gltf(filepath=temp_glb_path, loglevel=50, import_pack_images=False)
            
            # Zjistíme materiály PO importu
            mats_after = set(bpy.data.materials)
            
            # Získáme seznam právě vytvořených materiálů
            newly_imported_mats = list(mats_after - mats_before)
            
            with open(temp_json_path, 'r', encoding='utf-8') as f:
                vmdl_metadata = json.load(f)

        except Exception as e:
            self.report({'ERROR'}, f"Import VMDL archivu selhal: {e}")
            import traceback
            traceback.print_exc()
            if 'temp_dir_obj' in locals(): temp_dir_obj.cleanup()
            return {'CANCELLED'}
        
        if not vmdl_metadata:
            self.report({'WARNING'}, "Metadata se nepodařilo načíst.")
            temp_dir_obj.cleanup()
            return {'FINISHED'}

        # Vytvoříme mapu: Původní jméno -> Skutečný Blender materiál
        final_mat_map = {}
        original_mats_from_meta = vmdl_metadata.get('materials', {})

        for orig_name in original_mats_from_meta.keys():
            found_mat = None
            # Prohledáme nově importované materiály
            for new_mat in newly_imported_mats:
                # Hledáme shodu na začátku jména, abychom pokryli případy jako ".001"
                if new_mat.name.startswith(orig_name):
                    found_mat = new_mat
                    break # Našli jsme, bereme první shodu
            
            if found_mat:
                final_mat_map[orig_name] = found_mat
            else:
                print(f"VAROVÁNÍ: Nepodařilo se v importovaných datech najít materiál pro '{orig_name}'.")

        # Aplikace VMDL dat na objekty (zůstává stejná)
        for obj_name, obj_data in vmdl_metadata.get('objects', {}).items():
            obj = bpy.data.objects.get(obj_name)
            if not obj: continue
            vmdl_type = obj_data.get('vmdl_type')
            if vmdl_type: obj.vmdl_enum_type = vmdl_type
            if vmdl_type == 'COLLIDER':
                obj.vmdl_collider.collider_type = obj_data.get('collider_type', 'COL_METAL_SOLID')
            elif vmdl_type == 'MOUNTPOINT':
                obj.vmdl_mountpoint.forward_vector = obj_data.get('forward_vector', (0,1,0))
                obj.vmdl_mountpoint.up_vector = obj_data.get('up_vector', (0,0,1))
        
        # Aplikace VMDL dat na materiály pomocí naší nové mapy
        for original_mat_name, mat_data in original_mats_from_meta.items():
            final_blender_material = final_mat_map.get(original_mat_name)
            
            if not final_blender_material:
                continue # Varování už bylo vypsáno výše

            print(f"INFO: Aplikuji data na materiál '{final_blender_material.name}' (původně '{original_mat_name}').")
            
            shader_name = mat_data.get('shader_name')
            if shader_name:
                final_blender_material.vmdl_shader.shader_name = shader_name
            
            bpy.app.timers.register(lambda m=final_blender_material, md=mat_data, t_dir=tempdir: apply_material_properties(m, md, t_dir))

        def cleanup_temp_dir():
            try:
                temp_dir_obj.cleanup()
                print("Dočasný adresář po importu uklizen.")
            except Exception as e:
                print(f"Chyba při úklidu dočasného adresáře: {e}")
            return None

        bpy.app.timers.register(cleanup_temp_dir, first_interval=1.0)

        self.report({'INFO'}, f"VMDL soubor '{os.path.basename(self.filepath)}' úspěšně importován.")
        return {'FINISHED'}