import bpy
import json
import os
from bpy_extras.io_utils import ImportHelper

class VMDL_OT_import_glb(bpy.types.Operator, ImportHelper):
    bl_idname = "vmdl.import_glb"
    bl_label = "Import VMDL GLB"
    filename_ext = ".glb"
    filter_glob: bpy.props.StringProperty(default="*.glb", options={'HIDDEN'})

    def execute(self, context):
        # --- KROK 1: Standardní import GLB souboru ---
        # Uložíme si objekty, které existovaly před importem
        objects_before = set(bpy.data.objects)
        
        try:
            bpy.ops.import_scene.gltf(filepath=self.filepath, loglevel=50)
        except Exception as e:
            self.report({'ERROR'}, f"Import GLB selhal: {e}")
            return {'CANCELLED'}

        # Získáme nově importované objekty
        imported_objects = list(set(bpy.data.objects) - objects_before)
        
        # --- KROK 2: Zpracování VMDL metadat z 'extras' ---
        if not hasattr(bpy.data, 'gltf_extras'):
            self.report({'WARNING'}, "Soubor neobsahuje VMDL metadata ('extras'). Importován jako standardní GLB.")
            return {'FINISHED'}

        vmdl_extras = bpy.data.gltf_extras
        del bpy.data.gltf_extras # Uklidíme po sobě

        # Aplikace VMDL dat na objekty
        for obj_name, obj_data in vmdl_extras.get('objects', {}).items():
            obj = bpy.data.objects.get(obj_name)
            if not obj:
                print(f"Varování: Objekt '{obj_name}' z metadat nebyl v GLB nalezen.")
                continue

            vmdl_type = obj_data.get('vmdl_type')
            if vmdl_type:
                # OPRAVA: Používáme vmdl_enum_type pro konzistentní zápis
                obj.vmdl_enum_type = vmdl_type
            
            if vmdl_type == 'COLLIDER':
                obj.vmdl_collider.collider_type = obj_data.get('collider_type', 'COL_METAL_SOLID')
            elif vmdl_type == 'MOUNTPOINT':
                obj.vmdl_mountpoint.forward_vector = obj_data.get('forward_vector', (0,1,0))
                obj.vmdl_mountpoint.up_vector = obj_data.get('up_vector', (0,0,1))
        
        # Aplikace VMDL dat na materiály
        for mat_name, mat_data in vmdl_extras.get('materials', {}).items():
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                print(f"Varování: Materiál '{mat_name}' z metadat nebyl v GLB nalezen.")
                continue
            
            shader_name = mat_data.get('shader_name')
            if shader_name:
                mat.vmdl_shader.shader_name = shader_name
            
            bpy.app.timers.register(lambda m=mat, md=mat_data: self.apply_material_properties(m, md))

        self.report({'INFO'}, f"VMDL soubor '{os.path.basename(self.filepath)}' úspěšně importován.")
        return {'FINISHED'}

    def apply_material_properties(self, mat, mat_data):
        """Aplikuje parametry a textury na materiál."""
        if not mat or not mat_data:
            return

        shader_props = mat.vmdl_shader
        
        for name, value in mat_data.get('parameters', {}).items():
            if name in shader_props.parameters:
                param = shader_props.parameters[name]
                if param.type == 'float': param.float_value = value
                elif param.type == 'vector4': param.vector_value = value
                elif param.type == 'bool': param.bool_value = value
        
        for name, image_name in mat_data.get('textures', {}).items():
            if name in shader_props.textures and image_name:
                image = bpy.data.images.get(image_name)
                if image:
                    shader_props.textures[name].image = image
                else:
                    print(f"Varování: Textura '{image_name}' pro materiál '{mat.name}' nenalezena.")
        
        from .shader_materials import setup_principled_node_graph
        setup_principled_node_graph(mat)