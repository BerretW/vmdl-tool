import bpy
import json
import os
from bpy_extras.io_utils import ExportHelper

class VMDLExportProperties(bpy.types.PropertyGroup):
    # Tato property group zůstává pro případná budoucí nastavení exportu
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
        # Defaultní název souboru podle názvu scény
        if context.scene.name:
            self.filepath = context.scene.name + self.filename_ext
        else:
            self.filepath = "untitled" + self.filename_ext
        return super().invoke(self, context, event)

    def execute(self, context):
        # Najdi VMDL root objekt
        root_obj = context.active_object
        if not root_obj or root_obj.get("vmdl_type") != "ROOT":
            node = root_obj
            while node and node.parent:
                node = node.parent
                if node.get("vmdl_type") == "ROOT":
                    root_obj = node
                    break
            else:
                self.report({'ERROR'}, "Musíte vybrat objekt z VMDL hierarchie pro export.")
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
        
        if not any(o.type == 'MESH' and o.get("vmdl_type") == "MESH" for o in all_objs_to_export):
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
                    # GLTF exporter se postará o texturu, my si jen uložíme její název
                    mat_data['textures'][t.name] = t.image.name
            
            vmdl_extras['materials'][mat.name] = mat_data

        # Sběr dat o objektech (typ, collider, mountpoint)
        for obj in all_objs_to_export:
            obj_type = obj.get("vmdl_type")
            if not obj_type:
                continue
            
            obj_data = {'vmdl_type': obj_type}
            
            if obj_type == 'COLLIDER':
                obj_data['collider_type'] = obj.vmdl_collider.collider_type
            elif obj_type == 'MOUNTPOINT':
                obj_data['forward_vector'] = list(obj.vmdl_mountpoint.forward_vector)
                obj_data['up_vector'] = list(obj.vmdl_mountpoint.up_vector)
            
            vmdl_extras['objects'][obj.name] = obj_data

        # --- KROK 2: Export do GLB s metadaty v 'extras' ---
        
        # Výběr všech objektů v hierarchii pro export
        bpy.ops.object.select_all(action='DESELECT')
        for obj in all_objs_to_export:
            obj.select_set(True)
        context.view_layer.objects.active = root_obj

        try:
            # Uložíme naše data do dočasné scéna property, kterou si glTF exporter přečte
            bpy.context.scene['gltf_export_extras'] = vmdl_extras
            
            bpy.ops.export_scene.gltf(
                filepath=self.filepath,
                use_selection=True,
                export_format='GLB',
                export_extras=True, # DŮLEŽITÉ: Povolí export 'extras'
                export_attributes=True, # DŮLEŽITÉ: Exportuje Vertex Colors
                export_image_format='AUTO' # Necháme Blender, aby se rozhodl
            )
        except Exception as e:
            self.report({'ERROR'}, f"Export GLB selhal: {e}")
            return {'CANCELLED'}
        finally:
            # Uklidíme po sobě
            if 'gltf_export_extras' in bpy.context.scene:
                del bpy.context.scene['gltf_export_extras']

        self.report({'INFO'}, f"Export VMDL do {self.filepath} byl úspěšný.")
        return {'FINISHED'}