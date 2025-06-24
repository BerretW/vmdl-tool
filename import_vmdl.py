import bpy
import os
import json
import zipfile
import tempfile
import shutil
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector

from .shader_definitions import SHADER_DEFINITIONS
from .shader_materials import setup_principled_node_graph
from .vmdl_utils import VMDL_OT_create_vmdl_object


class VMDL_OT_import_package(bpy.types.Operator, ImportHelper):
    bl_idname = "vmdl.import_package"
    bl_label = "Import VMDL Package"
    filename_ext = ".vmdl.pkg"
    filter_glob: bpy.props.StringProperty(default="*.vmdl.pkg", options={'HIDDEN'})
    auto_parent: bpy.props.BoolProperty(
        name="Auto Parent",
        default=True,
        description="Automaticky nastaví hierarchii VMDL objektů"
    )

    def invoke(self, context, event):
        return super().invoke(context, event)

    def execute(self, context):
        temp_dir = tempfile.mkdtemp(prefix="vmdl_import_")
        try:
            with zipfile.ZipFile(self.filepath, 'r') as zf:
                zf.extractall(temp_dir)

            base = os.path.splitext(os.path.basename(self.filepath))[0]
            json_p = os.path.join(temp_dir, f"{base}.vmdl.json")
            if not os.path.exists(json_p):
                self.report({'ERROR'}, "Chybí .vmdl.json v balíku.")
                return {'CANCELLED'}

            with open(json_p) as f:
                data = json.load(f)

            # --- KROK 1: Import materiálů ---
            mat_map = {}
            for mf in data.get('materials', []):
                mat_path = os.path.join(temp_dir, mf)
                if not os.path.exists(mat_path):
                    continue
                with open(mat_path) as ff:
                    md = json.load(ff)
                lookup, mat = self._create_material(md, mf, temp_dir)
                if mat:
                    mat_map[lookup] = mat

            # --- KROK 2: Import .glb ---
            parts = self._import_glb(data.get('model_file'), temp_dir)
            if not parts:
                full = os.path.join(temp_dir, data.get('model_file'))
                if os.path.exists(full):
                    bpy.ops.import_scene.gltf(filepath=full, loglevel=50)
                    parts = list(context.selected_objects)

            # Map imported objects by name
            obj_map = {o.name: o for o in parts}

            # --- KROK 3: Nastavení objektů ---
            for name, obj in obj_map.items():
                if obj.type == 'MESH':
                    obj["vmdl_type"] = "MESH"
                    for slot in obj.material_slots:
                        if not slot.material:
                            continue
                        orig = slot.material.name
                        key = orig.split('_')[-1]
                        if key in mat_map:
                            old = slot.material
                            slot.material = mat_map[key]
                            bpy.data.materials.remove(old)

            # --- KROK 4: Hierarchie ---
            if self.auto_parent:
                for link in data.get('hierarchy', []):
                    child = obj_map.get(link['child'])
                    parent = obj_map.get(link['parent'])
                    if child and parent:
                        child.parent = parent

            # Najděme root
            root = next((o for o in parts if o.parent is None), None)
            if root:
                root.name = data.get('name', '') + '_VMDL'
                root["vmdl_type"] = "ROOT"
                context.view_layer.objects.active = root

            self.report({'INFO'}, f"Import dokončen: {data.get('name', '')}")
            return {'FINISHED'}
        finally:
            shutil.rmtree(temp_dir)

    def _create_material(self, mat_data, mat_filename, temp_dir):
        shader = mat_data.get('shader')
        if shader not in SHADER_DEFINITIONS:
            self.report({'WARNING'}, f"Shader '{shader}' neexistuje.")
            return None, None
        name = os.path.splitext(mat_filename)[0].split('_')[-1]
        mat = bpy.data.materials.new(name=f"VMDL_{name}")
        mat.use_nodes = True
        mat.vmdl_shader.shader_name = shader
        setup_principled_node_graph(mat)
        return name, mat

    def _import_glb(self, fn, temp_dir):
        fp = os.path.join(temp_dir, fn)
        if not os.path.exists(fp):
            return []
        before = set(bpy.context.scene.objects)
        bpy.ops.import_scene.gltf(filepath=fp, loglevel=50)
        return list(set(bpy.context.scene.objects) - before)