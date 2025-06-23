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

        base_name = os.path.splitext(os.path.basename(self.filepath))[0].replace('.vmdl', '')
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
            if not os.path.exists(full_path):
                self.report({'WARNING'}, f"Soubor {filename} v balíčku neexistuje.")
                return None
            bpy.ops.import_scene.gltf(filepath=full_path)
            # Vrátíme importované objekty, abychom našli ten správný
            return [obj for obj in context.selected_objects]

        # Import meshe
        imported_objects = import_glb(vmdl_data['model_file'])
        mesh_obj = imported_objects[0] if imported_objects else None
        if mesh_obj:
            mesh_obj.name = vmdl_data['name'] + ".model"
            mesh_obj["vmdl_type"] = "MESH"
            mesh_obj.parent = root_obj
            # Vyčistíme defaultní materiály z GLB importu
            mesh_obj.data.materials.clear()

        # Import collideru
        if 'collider_file' in vmdl_data:
            imported_objects = import_glb(vmdl_data['collider_file'])
            collider_obj = imported_objects[0] if imported_objects else None
            if collider_obj:
                collider_obj.name = vmdl_data['name'] + ".col"
                collider_obj["vmdl_type"] = "COLLIDER"
                collider_obj.parent = root_obj
                collider_obj.vmdl_collider.collider_type = vmdl_data.get('collider_type', '')

        # Import animací
        for anim in vmdl_data.get('animations', []):
            import_glb(anim['file'])

        # Import mountpointů
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

        # Import materiálů (nová logika)
        if mesh_obj and 'materials' in vmdl_data:
            for mat_filename in vmdl_data['materials']:
                mat_path = os.path.join(temp_dir, mat_filename)
                if not os.path.exists(mat_path):
                    continue
                
                with open(mat_path, 'r') as f:
                    mat_data = json.load(f)

                shader_name = mat_data.get('shader')
                if not shader_name:
                    continue
                    
                mat = bpy.data.materials.new(name=os.path.splitext(mat_filename)[0])
                mat.use_nodes = True
                mat.vmdl_shader.shader_name = shader_name
                
                shader_props = mat.vmdl_shader
                
                # Načtení parametrů
                for param_name, param_value in mat_data.get('parameters', {}).items():
                    if param_name in shader_props.parameters:
                        param_prop = shader_props.parameters[param_name]
                        if param_prop.type == 'float':
                            param_prop.float_value = param_value
                        elif param_prop.type == 'vector4':
                            param_prop.vector_value = param_value
                        elif param_prop.type == 'bool':
                            param_prop.bool_value = param_value

                # Načtení textur
                for tex_name, tex_filename in mat_data.get('textures', {}).items():
                    if tex_name in shader_props.textures:
                        tex_prop = shader_props.textures[tex_name]
                        image_path = os.path.join(temp_dir, tex_filename)
                        if os.path.exists(image_path):
                            try:
                                image = bpy.data.images.load(image_path, check_existing=True)
                                tex_prop.image = image
                            except Exception as e:
                                self.report({'WARNING'}, f"Nelze načíst texturu {image_path}: {e}")
                
                mesh_obj.data.materials.append(mat)

        self.report({'INFO'}, f"Import dokončen: {vmdl_data['name']}")
        return {'FINISHED'}