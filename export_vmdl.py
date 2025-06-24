import bpy
import json
import os
from bpy_extras.io_utils import ExportHelper

class VMDLExportProperties(bpy.types.PropertyGroup):
    version: bpy.props.FloatProperty(
        name="VMDL Version",
        default=3.0,
        description="Version number for VMDL metadata"
    )

class VMDL_OT_export_glb(bpy.types.Operator, ExportHelper):
    bl_idname = "vmdl.export_glb"
    bl_label = "Export VMDL GLB"
    filename_ext = ".glb"
    filter_glob: bpy.props.StringProperty(default="*.glb", options={'HIDDEN'})

    def invoke(self, context, event):
        # Najdeme root, abychom mohli pojmenovat soubor podle něj
        root_obj = None
        for obj in context.scene.objects:
            # OPRAVA: Používáme vmdl_enum_type pro konzistentní čtení
            if obj.vmdl_enum_type == "ROOT":
                root_obj = obj
                break
        
        if root_obj:
             self.filepath = root_obj.name.replace("_VMDL", "") + self.filename_ext
        elif context.scene.name:
            self.filepath = context.scene.name + self.filename_ext
        else:
            self.filepath = "untitled" + self.filename_ext
        return super().invoke(context, event)

    def execute(self, context):
        # --- Robustní způsob nalezení VMDL Root objektu ---
        start_obj = context.active_object
        root_obj = None

        # 1. Zkusit aktivní objekt a jeho parenty
        if start_obj:
            # OPRAVA: Používáme vmdl_enum_type pro konzistentní čtení
            if start_obj.vmdl_enum_type == "ROOT":
                root_obj = start_obj
            else:
                # Hledání root přes parenty
                node = start_obj
                while node.parent:
                    node = node.parent
                    # OPRAVA: Používáme vmdl_enum_type pro konzistentní čtení
                    if node.vmdl_enum_type == "ROOT":
                        root_obj = node
                        break

        # 2. Pokud se nenašel, projít všechny objekty ve scéně a najít první root
        if not root_obj:
            for obj in bpy.context.scene.objects:
                # OPRAVA: Používáme vmdl_enum_type pro konzistentní čtení
                if obj.vmdl_enum_type == "ROOT":
                    root_obj = obj
                    break

        if not root_obj:
            self.report({'ERROR'}, "Nelze najít žádný VMDL Root objekt pro export.")
            return {'CANCELLED'}

        # --- KROK 1: Sběr všech VMDL metadat ---
        vmdl_extras = {
            'vmdl_version': context.scene.vmdl_export.version,
            'materials': {},
            'objects': {}
        }
        
        all_objs_to_export = []
        def gather_objects(obj):
            all_objs_to_export.append(obj)
            for child in obj.children:
                gather_objects(child)
        gather_objects(root_obj)
        
        # OPRAVA: Používáme vmdl_enum_type pro konzistentní čtení
        if not any(o.type == 'MESH' and o.vmdl_enum_type == "MESH" for o in all_objs_to_export):
            self.report({'ERROR'}, "VMDL Root neobsahuje žádný viditelný MESH objekt.")
            return {'CANCELLED'}

        # Sběr dat o materiálech
        unique_materials = set(
            mat for o in all_objs_to_export if o.type == 'MESH' for mat in o.data.materials if mat
        )
        
        for mat in unique_materials:
            props = getattr(mat, 'vmdl_shader', None)
            if not props or not props.shader_name:
                continue
            
            mat_data = {'shader_name': props.shader_name, 'parameters': {}, 'textures': {}}
            
            for p in props.parameters:
                if p.type == 'float': val = p.float_value
                elif p.type == 'vector4': val = list(p.vector_value)
                elif p.type == 'bool': val = p.bool_value
                else: continue
                mat_data['parameters'][p.name] = val

            for t in props.textures:
                if t.image:
                    mat_data['textures'][t.name] = t.image.name
            
            vmdl_extras['materials'][mat.name] = mat_data

        # Sběr dat o objektech
        for obj in all_objs_to_export:
            # OPRAVA: Používáme vmdl_enum_type pro konzistentní čtení
            obj_type = obj.vmdl_enum_type
            if obj_type == 'NONE':
                continue
            
            obj_data = {'vmdl_type': obj_type}
            
            if obj_type == 'COLLIDER':
                obj_data['collider_type'] = obj.vmdl_collider.collider_type
            elif obj_type == 'MOUNTPOINT':
                obj_data['forward_vector'] = list(obj.vmdl_mountpoint.forward_vector)
                obj_data['up_vector'] = list(obj.vmdl_mountpoint.up_vector)
            
            vmdl_extras['objects'][obj.name] = obj_data

        # --- KROK 2: Export do GLB s metadaty v 'extras' ---
        bpy.ops.object.select_all(action='DESELECT')
        for obj in all_objs_to_export:
            obj.select_set(True)
        context.view_layer.objects.active = root_obj

        try:
            bpy.context.scene['gltf_export_extras'] = vmdl_extras
            
            bpy.ops.export_scene.gltf(
                filepath=self.filepath,
                use_selection=True,
                export_format='GLB',
                export_extras=True,
                export_attributes=True,
                export_image_format='AUTO'
            )
        except Exception as e:
            self.report({'ERROR'}, f"Export GLB selhal: {e}")
            return {'CANCELLED'}
        finally:
            if 'gltf_export_extras' in bpy.context.scene:
                del bpy.context.scene['gltf_export_extras']

        self.report({'INFO'}, f"Export VMDL do {self.filepath} byl úspěšný.")
        return {'FINISHED'}