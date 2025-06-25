import bpy
import json
import os
import shutil
import tempfile
import zipfile
from bpy_extras.io_utils import ExportHelper

class VMDLExportProperties(bpy.types.PropertyGroup):
    version: bpy.props.FloatProperty(name="VMDL Version", default=3.0, description="Version number for VMDL metadata")
    debug_show_extras: bpy.props.BoolProperty(name="Debug: Zobrazit Metadata", description="Po exportu vypíše obsah 'metadata.json' do systémové konzole pro kontrolu", default=False)


class VMDL_OT_export_vmdl(bpy.types.Operator, ExportHelper):
    bl_idname = "vmdl.export_vmdl"
    bl_label = "Export VMDL Archive"
    filename_ext = ".vmdl"
    filter_glob: bpy.props.StringProperty(default="*.vmdl", options={'HIDDEN'})

    def invoke(self, context, event):
        root_obj = None
        for obj in context.scene.objects:
            if obj.vmdl_enum_type == "ROOT":
                root_obj = obj
                break
        if root_obj: self.filepath = root_obj.name.replace("_VMDL", "") + self.filename_ext
        elif context.scene.name: self.filepath = context.scene.name + self.filename_ext
        else: self.filepath = "untitled" + self.filename_ext
        return super().invoke(context, event)

    def execute(self, context):
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

        vmdl_metadata = {
            'vmdl_version': context.scene.vmdl_export.version,
            'materials': {},
            'objects': {}
            # Odebrána logika s indexy, není potřeba
        }
        all_objs_to_export = []
        def gather_objects(obj):
            all_objs_to_export.append(obj)
            for child in obj.children: gather_objects(child)
        gather_objects(root_obj)

        if not any(o.type == 'MESH' and o.vmdl_enum_type == "MESH" for o in all_objs_to_export):
            self.report({'ERROR'}, "VMDL Root neobsahuje žádný viditelný MESH objekt."); return {'CANCELLED'}
        
        unique_materials = set(mat for o in all_objs_to_export if o.type == 'MESH' for mat in o.data.materials if mat)
        unique_images = set()

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
                if t.image:
                    mat_data['textures'][t.name] = os.path.basename(t.image.name)
                    unique_images.add(t.image)
            # Ukládáme data pod původním jménem materiálu
            vmdl_metadata['materials'][mat.name] = mat_data
            
        for obj in all_objs_to_export:
            obj_type = obj.vmdl_enum_type
            if obj_type == 'NONE': continue
            obj_data = {'vmdl_type': obj_type}
            if obj_type == 'COLLIDER': obj_data['collider_type'] = obj.vmdl_collider.collider_type
            elif obj_type == 'MOUNTPOINT':
                obj_data['forward_vector'] = list(obj.vmdl_mountpoint.forward_vector)
                obj_data['up_vector'] = list(obj.vmdl_mountpoint.up_vector)
            vmdl_metadata['objects'][obj.name] = obj_data
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        for obj in all_objs_to_export: obj.select_set(True)
        context.view_layer.objects.active = root_obj

        try:
            with tempfile.TemporaryDirectory() as tempdir:
                temp_glb_path = os.path.join(tempdir, 'model.glb')
                temp_json_path = os.path.join(tempdir, 'metadata.json')
                
                temp_tex_dir = os.path.join(tempdir, 'tex')
                os.makedirs(temp_tex_dir)

                for image in unique_images:
                    if not image.has_data: continue
                    dest_filename = os.path.basename(image.name)
                    dest_filepath = os.path.join(temp_tex_dir, dest_filename)
                    
                    if image.packed_file or not os.path.exists(bpy.path.abspath(image.filepath_raw)):
                        temp_img = image.copy()
                        temp_img.filepath_raw = dest_filepath
                        temp_img.file_format = image.file_format or 'PNG'
                        temp_img.save()
                        bpy.data.images.remove(temp_img)
                    else:
                        shutil.copy(bpy.path.abspath(image.filepath_raw), dest_filepath)

                bpy.ops.export_scene.gltf(
                    filepath=temp_glb_path,
                    export_format='GLB',
                    use_selection=True,
                    export_attributes=True,
                    export_image_format='NONE',
                    export_extras=False
                )

                with open(temp_json_path, 'w', encoding='utf-8') as f:
                    json.dump(vmdl_metadata, f, ensure_ascii=False, indent=4)
                
                with zipfile.ZipFile(self.filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(temp_glb_path, arcname='model.glb')
                    zf.write(temp_json_path, arcname='metadata.json')
                    for filename in os.listdir(temp_tex_dir):
                        zf.write(os.path.join(temp_tex_dir, filename), arcname=f'tex/{filename}')

        except Exception as e:
            self.report({'ERROR'}, f"Export VMDL archivu selhal: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

        self.report({'INFO'}, f"Export VMDL do {self.filepath} byl úspěšný.")
        
        if context.scene.vmdl_export.debug_show_extras:
            print("\n================= DEBUG VMDL METADATA ==================")
            print(json.dumps(vmdl_metadata, indent=2, ensure_ascii=False))
            print("============== KONEC DEBUG VMDL METADATA ===============\n")
        
        return {'FINISHED'}