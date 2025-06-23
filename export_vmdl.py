# export_vmdl.py

import bpy
import json
import os
import zipfile
import shutil
from bpy_extras.io_utils import ExportHelper
from .constants import SHADER_TYPES

class VMDLExportProperties(bpy.types.PropertyGroup):
    shader_type_to_create: bpy.props.EnumProperty(
        items=[(s, s, "") for s in SHADER_TYPES],
        name="Shader Type"
    )

def get_texture_data(shader_property, texture_name, texture_files):
    """Pomocná funkce pro získání dat textury a přidání do setu."""
    if shader_property:
        path = bpy.path.abspath(shader_property.filepath)
        if os.path.exists(path):
            texture_files.add(path)
            return os.path.basename(path)
    return None

class VMDL_OT_export_package(bpy.types.Operator, ExportHelper):
    bl_idname = "vmdl.export_package"
    bl_label = "Export VMDL Package"
    filename_ext = ".vmdl.pkg"
    filter_glob: bpy.props.StringProperty(default="*.vmdl.pkg", options={'HIDDEN'})

    def execute(self, context):
        root_obj = context.active_object
        if not root_obj or root_obj.get("vmdl_type") != "ROOT":
            self.report({'ERROR'}, "Musíte vybrat VMDL Root objekt pro export.")
            return {'CANCELLED'}

        base_name = os.path.splitext(os.path.basename(self.filepath))[0].replace(".vmdl", "")
        temp_dir = bpy.app.tempdir + os.sep + "vmdl_export_" + base_name

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        vmdl_data = {'name': base_name, 'version': 1}
        mat_files = []
        texture_files = set()

        mesh_obj = next((c for c in root_obj.children if c.get("vmdl_type") == "MESH"), None)
        collider_obj = next((c for c in root_obj.children if c.get("vmdl_type") == "COLLIDER"), None)
        armature_obj = next((c for c in root_obj.children if c.type == 'ARMATURE'), None)
        
        if not mesh_obj:
            self.report({'ERROR'}, "VMDL Root neobsahuje žádný MESH objekt.")
            shutil.rmtree(temp_dir)
            return {'CANCELLED'}

        # EXPORT MESH
        vmdl_data['model_file'] = f"{base_name}.glb"
        bpy.ops.object.select_all(action='DESELECT')
        mesh_obj.select_set(True)
        context.view_layer.objects.active = mesh_obj
        export_path = os.path.join(temp_dir, vmdl_data['model_file'])
        bpy.ops.export_scene.gltf(filepath=export_path, use_selection=True, export_format='GLB', export_attributes=True)

        # EXPORT COLLIDER
        if collider_obj:
            vmdl_data['collider_file'] = f"{base_name}_col.glb"
            vmdl_data['collider_type'] = collider_obj.vmdl_collider.collider_type
            bpy.ops.object.select_all(action='DESELECT')
            collider_obj.select_set(True)
            context.view_layer.objects.active = collider_obj
            export_path = os.path.join(temp_dir, vmdl_data['collider_file'])
            bpy.ops.export_scene.gltf(filepath=export_path, use_selection=True, export_format='GLB')

        # EXPORT MATERIÁLŮ
        for i, mat_slot in enumerate(mesh_obj.material_slots):
            mat = mat_slot.material
            if not mat or not mat.use_nodes or not hasattr(mat, "vmdl_shader"):
                continue

            mat_name = f"{base_name}_mat_{i}.mat.json"
            mat_files.append(mat_name)
            shader = mat.vmdl_shader
            mat_data = {
                'shader': shader.shader_type,
                'parameters': {},
                'textures': {}
            }

            # Společné parametry
            if shader.shader_type != 'ShipGlass':
                mat_data['parameters']['color1'] = list(shader.color1)
                mat_data['parameters']['color2'] = list(shader.color2)

            # Specifické parametry a textury
            if shader.shader_type == 'ShipStandard':
                mat_data['parameters']['smoothness'] = shader.smoothness
                mat_data['parameters']['tint_color'] = list(shader.tint_color)
                
                tex_data = get_texture_data(shader.albedo_image, 'Albedo', texture_files)
                if tex_data: mat_data['textures']['Albedo'] = tex_data
                tex_data = get_texture_data(shader.normal_image, 'Normal', texture_files)
                if tex_data: mat_data['textures']['Normal'] = tex_data
                tex_data = get_texture_data(shader.roughness_image, 'Roughness', texture_files)
                if tex_data: mat_data['textures']['Roughness'] = tex_data
                tex_data = get_texture_data(shader.metallic_image, 'Metallic', texture_files)
                if tex_data: mat_data['textures']['Metallic'] = tex_data

            elif shader.shader_type == 'Standard_dirt':
                tex_data = get_texture_data(shader.albedo_image, 'Albedo', texture_files)
                if tex_data: mat_data['textures']['Albedo'] = tex_data
                tex_data = get_texture_data(shader.normal_image, 'Normal', texture_files)
                if tex_data: mat_data['textures']['Normal'] = tex_data
                tex_data = get_texture_data(shader.dirt_image, 'Dirt', texture_files)
                if tex_data: mat_data['textures']['Dirt'] = tex_data

            elif shader.shader_type == 'ShipGlass':
                mat_data['parameters']['opacity'] = shader.opacity
                mat_data['parameters']['fresnel_power'] = shader.fresnel_power
                mat_data['parameters']['reflectivity'] = shader.reflectivity
                tex_data = get_texture_data(shader.opacity_image, 'Opacity', texture_files)
                if tex_data: mat_data['textures']['Opacity'] = tex_data

            elif shader.shader_type == 'Layered4':
                mat_data['parameters']['blend_strength'] = shader.blend_strength
                mat_data['parameters']['global_tint'] = list(shader.global_tint)
                mat_data['parameters']['uv_scale'] = list(shader.uv_scale)
                for idx in range(1, 5):
                    tex_prop = getattr(shader, f"layer{idx}_image")
                    tex_data = get_texture_data(tex_prop, f"Layer{idx}", texture_files)
                    if tex_data: mat_data['textures'][f"Layer{idx}"] = tex_data

            with open(os.path.join(temp_dir, mat_name), 'w') as f:
                json.dump(mat_data, f, indent=2)

        vmdl_data['materials'] = mat_files

        # ANIMACE (beze změny)
        if armature_obj:
            vmdl_data['has_armature'] = True
            vmdl_data['animations'] = []
            for action in bpy.data.actions:
                if not armature_obj.animation_data:
                    armature_obj.animation_data_create()
                armature_obj.animation_data.action = action
                anim_name = action.name
                anim_file = f"anim_{anim_name}.glb"
                export_path = os.path.join(temp_dir, anim_file)
                bpy.ops.object.select_all(action='DESELECT')
                armature_obj.select_set(True)
                context.view_layer.objects.active = armature_obj
                bpy.ops.export_scene.gltf(filepath=export_path, use_selection=True, export_format='GLB', export_anim=True)
                vmdl_data['animations'].append({
                    'name': anim_name,
                    'file': anim_file,
                    'loop': True
                })

        # MOUNTPOINTY (beze změny)
        vmdl_data['mountpoints'] = []
        for child in root_obj.children:
            if child.get("vmdl_type") == "MOUNTPOINT":
                loc, rot_q, _ = child.matrix_world.decompose()
                vmdl_data['mountpoints'].append({
                    'name': child.name,
                    'position': list(loc),
                    'rotation': [rot_q.x, rot_q.y, rot_q.z, rot_q.w],
                    'forward': list(child.vmdl_mountpoint.forward_vector),
                    'up': list(child.vmdl_mountpoint.up_vector)
                })

        # ZÁPIS JSON
        with open(os.path.join(temp_dir, f"{base_name}.vmdl.json"), 'w') as f:
            json.dump(vmdl_data, f, indent=2)

        # TEXTURY
        for tex_path in texture_files:
            if os.path.exists(tex_path):
                shutil.copy(tex_path, os.path.join(temp_dir, os.path.basename(tex_path)))

        # ZIP BALÍK
        with zipfile.ZipFile(self.filepath, 'w') as zf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    zf.write(os.path.join(root, file), arcname=file)

        shutil.rmtree(temp_dir)
        self.report({'INFO'}, f"Export dokončen do {self.filepath}")
        return {'FINISHED'}