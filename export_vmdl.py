# vmdl_plugin/export_vmdl.py

import bpy
import json
import os
import zipfile
import shutil
from bpy_extras.io_utils import ExportHelper

class VMDLExportProperties(bpy.types.PropertyGroup):
    shader_type_to_create: bpy.props.EnumProperty(
        items=[(s, s, "") for s in ["ShipStandard", "ShipGlass", "Layered4"]],
        name="Shader Type"
    )

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

        base_name = os.path.splitext(os.path.basename(self.filepath))[0]
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

        # EXPORT MESH
        vmdl_data['model_file'] = f"{base_name}.glb"
        bpy.ops.object.select_all(action='DESELECT')
        mesh_obj.select_set(True)
        context.view_layer.objects.active = mesh_obj
        export_path = os.path.join(temp_dir, vmdl_data['model_file'])
        bpy.ops.export_scene.gltf(filepath=export_path, use_selection=True, export_format='GLB')

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
        for i, mat in enumerate(mesh_obj.data.materials):
            if not mat or not mat.use_nodes or not hasattr(mat, "vmdl_shader"):
                continue

            mat_name = f"{base_name}_mat_{i}.mat.json"
            mat_files.append(mat_name)
            mat_data = {
                'shader': mat.vmdl_shader.shader_type,
                'parameters': {},
                'textures': {}
            }

            shader = mat.vmdl_shader
            if shader.shader_type == 'ShipStandard':
                mat_data['parameters']['smoothness'] = shader.smoothness
                mat_data['parameters']['tint_color'] = list(shader.tint_color)
            elif shader.shader_type == 'ShipGlass':
                mat_data['parameters']['opacity'] = shader.opacity
                mat_data['parameters']['fresnel_power'] = shader.fresnel_power
                mat_data['parameters']['reflectivity'] = shader.reflectivity
            elif shader.shader_type == 'Layered4':
                mat_data['parameters']['blend_strength'] = shader.blend_strength
                mat_data['parameters']['global_tint'] = list(shader.global_tint)
                mat_data['parameters']['uv_scale'] = list(shader.uv_scale)

            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    img = node.image
                    tex_name = os.path.basename(img.filepath)
                    dds_name = os.path.splitext(tex_name)[0] + ".dds"
                    mat_data['textures'][node.label or node.name] = dds_name
                    texture_files.add(img.filepath)

            with open(os.path.join(temp_dir, mat_name), 'w') as f:
                json.dump(mat_data, f, indent=2)

        vmdl_data['materials'] = mat_files

        # ANIMACE
        if armature_obj:
            vmdl_data['has_armature'] = True
            vmdl_data['animations'] = []
            for action in bpy.data.actions:
                armature_obj.animation_data.action = action
                anim_name = action.name
                anim_file = f"anim_{anim_name}.glb"
                export_path = os.path.join(temp_dir, anim_file)
                bpy.ops.object.select_all(action='DESELECT')
                armature_obj.select_set(True)
                context.view_layer.objects.active = armature_obj
                bpy.ops.export_scene.gltf(filepath=export_path, use_selection=True, export_format='GLB')
                vmdl_data['animations'].append({
                    'name': anim_name,
                    'file': anim_file,
                    'loop': True
                })

        # MOUNTPOINTY
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
