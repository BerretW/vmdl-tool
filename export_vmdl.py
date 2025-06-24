import bpy
import json
import os
import struct
from bpy_extras.io_utils import ExportHelper

def _inspect_exported_glb(filepath):
    """
    Pomocná funkce, která otevře GLB soubor, najde JSON chunk 
    a vypíše obsah klíče 'extras' do systémové konzole.
    """
    print("\n================= DEBUG INSPEKCE EXPORTU ==================")
    try:
        with open(filepath, 'rb') as f:
            magic = f.read(4)
            if magic != b'glTF':
                print("[INSPEKCE CHYBA] Soubor nemá platný 'glTF' magic number.")
                return

            version = struct.unpack('<I', f.read(4))[0]
            f.read(4)

            json_chunk_length = struct.unpack('<I', f.read(4))[0]
            json_chunk_type = f.read(4)

            if json_chunk_type != b'JSON':
                print(f"[INSPEKCE CHYBA] První chunk není JSON, ale {json_chunk_type}.")
                return
            
            json_data = f.read(json_chunk_length)
            gltf_dict = json.loads(json_data.decode('utf-8'))

            if 'extras' in gltf_dict:
                print("✅ V souboru byl nalezen klíč 'extras'. Jeho obsah je:")
                print(json.dumps(gltf_dict['extras'], indent=2, ensure_ascii=False))
            else:
                print("❌ V JSON části souboru chybí klíč 'extras'!")

    except Exception as e:
        print(f"[INSPEKCE CHYBA] Během čtení souboru došlo k chybě: {e}")
    finally:
        print("================ KONEC DEBUG INSPEKCE =================\n")


class VMDLExportProperties(bpy.types.PropertyGroup):
    version: bpy.props.FloatProperty(
        name="VMDL Version",
        default=3.0,
        description="Version number for VMDL metadata"
    )
    debug_show_extras: bpy.props.BoolProperty(
        name="Debug: Zobrazit Extras",
        description="Po exportu vypíše obsah 'extras' dat do systémové konzole pro kontrolu",
        default=False
    )


class VMDL_OT_export_glb(bpy.types.Operator, ExportHelper):
    bl_idname = "vmdl.export_glb"
    bl_label = "Export VMDL GLB"
    filename_ext = ".glb"
    filter_glob: bpy.props.StringProperty(default="*.glb", options={'HIDDEN'})

    def invoke(self, context, event):
        root_obj = None
        for obj in context.scene.objects:
            if obj.vmdl_enum_type == "ROOT":
                root_obj = obj
                break
        
        if root_obj:
             self.filepath = root_obj.name.replace("_VMDL", "") + self.filename_ext
        elif context.scene.name:
            self.filepath = context.scene.name + self.filename_ext
        else:
            self.filepath = "untitled" + self.filename_ext
            
        # ======================================================================
        # OPRAVA: Metodě super().invoke() se nepředává 'self' explicitně.
        # Python ho předá automaticky.
        # ======================================================================
        return super().invoke(context, event)

    def execute(self, context):
        # ... (zbytek kódu execute zůstává naprosto stejný) ...
        start_obj = context.active_object
        root_obj = None
        if start_obj:
            if start_obj.vmdl_enum_type == "ROOT": root_obj = start_obj
            else:
                node = start_obj
                while node.parent:
                    node = node.parent
                    if node.vmdl_enum_type == "ROOT": root_obj = node; break
        if not root_obj:
            for obj in bpy.context.scene.objects:
                if obj.vmdl_enum_type == "ROOT": root_obj = obj; break
        if not root_obj:
            self.report({'ERROR'}, "Nelze najít žádný VMDL Root objekt pro export."); return {'CANCELLED'}

        vmdl_extras = {
            'vmdl_version': context.scene.vmdl_export.version,
            'materials': {},
            'objects': {}
        }
        all_objs_to_export = []
        def gather_objects(obj):
            all_objs_to_export.append(obj)
            for child in obj.children: gather_objects(child)
        gather_objects(root_obj)
        if not any(o.type == 'MESH' and o.vmdl_enum_type == "MESH" for o in all_objs_to_export):
            self.report({'ERROR'}, "VMDL Root neobsahuje žádný viditelný MESH objekt."); return {'CANCELLED'}
        unique_materials = set(mat for o in all_objs_to_export if o.type == 'MESH' for mat in o.data.materials if mat)
        for mat in unique_materials:
            props = getattr(mat, 'vmdl_shader', None)
            if not props or not props.shader_name: continue
            mat_data = {'shader_name': props.shader_name, 'parameters': {}, 'textures': {}}
            for p in props.parameters:
                if p.type == 'float': val = p.float_value
                elif p.type == 'vector4': val = list(p.vector_value)
                elif p.type == 'bool': val = p.bool_value
                else: continue
                mat_data['parameters'][p.name] = val
            for t in props.textures:
                if t.image: mat_data['textures'][t.name] = t.image.name
            vmdl_extras['materials'][mat.name] = mat_data
        for obj in all_objs_to_export:
            obj_type = obj.vmdl_enum_type
            if obj_type == 'NONE': continue
            obj_data = {'vmdl_type': obj_type}
            if obj_type == 'COLLIDER': obj_data['collider_type'] = obj.vmdl_collider.collider_type
            elif obj_type == 'MOUNTPOINT':
                obj_data['forward_vector'] = list(obj.vmdl_mountpoint.forward_vector)
                obj_data['up_vector'] = list(obj.vmdl_mountpoint.up_vector)
            vmdl_extras['objects'][obj.name] = obj_data

        bpy.ops.object.select_all(action='DESELECT')
        for obj in all_objs_to_export: obj.select_set(True)
        context.view_layer.objects.active = root_obj

        try:
            bpy.context.scene['gltf_extras'] = vmdl_extras
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
            if 'gltf_extras' in bpy.context.scene:
                del bpy.context.scene['gltf_extras']

        self.report({'INFO'}, f"Export VMDL do {self.filepath} byl úspěšný.")
        
        if context.scene.vmdl_export.debug_show_extras:
            _inspect_exported_glb(self.filepath)
            
        return {'FINISHED'}