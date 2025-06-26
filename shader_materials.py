# ================================================
# FILE: shader_materials.py
# ================================================
import bpy
import json
import os
from bpy_extras.io_utils import ImportHelper, ExportHelper
from .shader_definitions import SHADER_DEFINITIONS

class VMDL_OT_apply_tint_to_object(bpy.types.Operator):
    """Aplikuje vybraný tint na celý objekt úpravou Vertex Color."""
    bl_idname = "vmdl.apply_tint_to_object"
    bl_label = "Apply Tint to Object"
    bl_description = "Vyplní R kanál vrstvy 'Color1' vybranou hodnotou tintu na celém objektu"
    bl_options = {'REGISTER', 'UNDO'}

    tint_value: bpy.props.FloatProperty(name="Tint Value", min=0.0, max=1.0)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.active_material

    def execute(self, context):
        obj = context.active_object
        mesh = obj.data

        if 'Color1' not in mesh.vertex_colors:
            mesh.vertex_colors.new(name="Color1")
            self.report({'INFO'}, "Vytvořena chybějící vrstva 'Color1'.")
        
        color_layer = mesh.vertex_colors['Color1'].data
        
        for loop_color in color_layer:
            original_g = loop_color.color[1]
            original_b = loop_color.color[2]
            original_a = loop_color.color[3]
            loop_color.color = (self.tint_value, original_g, original_b, original_a)

        mesh.update()
        self.report({'INFO'}, f"Tint hodnota {self.tint_value:.2f} aplikována na objekt.")
        return {'FINISHED'}


def setup_principled_node_graph(mat):
    """
    Vytvoří PBR náhled, který míchá i normálové mapy a podporuje interaktivní tint.
    """
    if not mat or not mat.use_nodes:
        return

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    output = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if not bsdf or not output:
        nodes.clear(); output = nodes.new(type='ShaderNodeOutputMaterial'); output.location = (400, 0)
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled'); bsdf.location = (100, 0)
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    for node in list(nodes):
        if node.name.startswith("VMDL_"): nodes.remove(node)

    shader_props = mat.vmdl_shader
    shader_name = shader_props.shader_name
    x_pos = -1600

    attr_c1 = nodes.new('ShaderNodeVertexColor'); attr_c1.name = "VMDL_AttrC1"; attr_c1.layer_name = "Color1"; attr_c1.location = (x_pos, 400)
    sep_c1 = nodes.new('ShaderNodeSeparateColor'); sep_c1.name = "VMDL_SepC1"; sep_c1.location = (x_pos + 200, 400); links.new(attr_c1.outputs['Color'], sep_c1.inputs['Color'])
    attr_c2 = nodes.new('ShaderNodeVertexColor'); attr_c2.name = "VMDL_AttrC2"; attr_c2.layer_name = "Color2"; attr_c2.location = (x_pos, 100)
    sep_c2 = nodes.new('ShaderNodeSeparateColor'); sep_c2.name = "VMDL_SepC2"; sep_c2.location = (x_pos + 200, 100); links.new(attr_c2.outputs['Color'], sep_c2.inputs['Color'])

    def find_texture_node(name_part):
        prop = next((t for t in shader_props.textures if name_part in t.name.lower() and t.image), None)
        if not prop: return None
        node = nodes.new('ShaderNodeTexImage'); node.name = f"VMDL_{name_part.capitalize()}Tex"; node.image = prop.image
        return node

    base_color_output_socket = None
    if "Standard_dirt" in shader_name:
        albedo_node = find_texture_node("albedo"); dirt_node = find_texture_node("dirt")
        if albedo_node and dirt_node:
            albedo_node.location = (x_pos + 450, 0); dirt_node.location = (x_pos + 450, -250)
            mix_dirt = nodes.new('ShaderNodeMix'); mix_dirt.name = "VMDL_DirtMix"; mix_dirt.data_type = 'RGBA'; mix_dirt.blend_type = 'MIX'; mix_dirt.location = (x_pos + 700, 0)
            links.new(albedo_node.outputs['Color'], mix_dirt.inputs['A']); links.new(dirt_node.outputs['Color'], mix_dirt.inputs['B']); links.new(sep_c2.outputs['Red'], mix_dirt.inputs['Factor'])
            base_color_output_socket = mix_dirt.outputs['Result']
        elif albedo_node: base_color_output_socket = albedo_node.outputs['Color']
    else:
        albedo_node = find_texture_node("diffuse") or find_texture_node("albedo")
        if albedo_node: albedo_node.location = (x_pos + 450, 0); base_color_output_socket = albedo_node.outputs['Color']

    tint_palette_node = find_texture_node("tintpalettetex")
    if tint_palette_node:
        tint_palette_node.interpolation = 'Closest'; tint_palette_node.location = (x_pos + 700, 600)
        tint_preview_value = nodes.new('ShaderNodeValue'); tint_preview_value.name = "VMDL_TintPreviewValue"
        tint_preview_value.outputs[0].default_value = shader_props.tint_preview
        tint_preview_value.location = (x_pos + 200, 800)
        
        is_rendering = nodes.new('ShaderNodeLightPath'); is_rendering.name = "VMDL_IsRender"; is_rendering.location = (x_pos, 600)
        
        mix_tint_source = nodes.new('ShaderNodeMix'); mix_tint_source.name = "VMDL_MixTintSource"; mix_tint_source.data_type = 'FLOAT'; mix_tint_source.location = (x_pos + 450, 800)
        links.new(is_rendering.outputs['Is Camera Ray'], mix_tint_source.inputs['Factor'])
        links.new(sep_c1.outputs['Red'], mix_tint_source.inputs['A'])
        links.new(tint_preview_value.outputs['Value'], mix_tint_source.inputs['B'])

        combine_uv = nodes.new('ShaderNodeCombineXYZ'); combine_uv.name = "VMDL_CombineUV"; combine_uv.location = (x_pos + 450, 600); combine_uv.inputs[0].default_value = 0.5
        links.new(mix_tint_source.outputs['Result'], combine_uv.inputs[1]); links.new(combine_uv.outputs['Vector'], tint_palette_node.inputs['Vector'])

        if base_color_output_socket:
            mix_tint = nodes.new('ShaderNodeMix'); mix_tint.name = "VMDL_TintMix"; mix_tint.data_type = 'RGBA'; mix_tint.blend_type = 'MULTIPLY'; mix_tint.location = (x_pos + 1250, 100)
            links.new(base_color_output_socket, mix_tint.inputs['A']); links.new(tint_palette_node.outputs['Color'], mix_tint.inputs['B'])
            links.new(mix_tint.outputs['Result'], bsdf.inputs['Base Color'])
        else: links.new(tint_palette_node.outputs['Color'], bsdf.inputs['Base Color'])
    elif base_color_output_socket: links.new(base_color_output_socket, bsdf.inputs['Base Color'])

    base_normal_node = find_texture_node("bumptex")
    dirt_normal_node = find_texture_node("dirtbumptex") if "Standard_dirt" in shader_name else None
    final_normal_socket = None
    if base_normal_node and dirt_normal_node:
        base_normal_node.image.colorspace_settings.name = 'Non-Color'; base_normal_node.location = (x_pos + 450, -750)
        dirt_normal_node.image.colorspace_settings.name = 'Non-Color'; dirt_normal_node.location = (x_pos + 450, -1000)
        mix_normal = nodes.new('ShaderNodeMix'); mix_normal.name = "VMDL_NormalMix"; mix_normal.data_type = 'VECTOR'; mix_normal.blend_type = 'MIX'; mix_normal.location = (x_pos + 700, -850)
        links.new(base_normal_node.outputs['Color'], mix_normal.inputs['A']); links.new(dirt_normal_node.outputs['Color'], mix_normal.inputs['B']); links.new(sep_c2.outputs['Red'], mix_normal.inputs['Factor'])
        final_normal_socket = mix_normal.outputs['Result']
    elif base_normal_node:
        base_normal_node.image.colorspace_settings.name = 'Non-Color'; base_normal_node.location = (x_pos + 450, -750); final_normal_socket = base_normal_node.outputs['Color']

    if final_normal_socket:
        norm_map = nodes.new('ShaderNodeNormalMap'); norm_map.name = "VMDL_NormalMap"; norm_map.location = (x_pos + 950, -750)
        links.new(final_normal_socket, norm_map.inputs['Color']); links.new(sep_c1.outputs['Blue'], norm_map.inputs['Strength']); links.new(norm_map.outputs['Normal'], bsdf.inputs['Normal'])

    roughness_node = find_texture_node("roughnesstex")
    if roughness_node:
        roughness_node.image.colorspace_settings.name = 'Non-Color'; roughness_node.location = (x_pos + 450, -500)
        links.new(roughness_node.outputs['Color'], bsdf.inputs['Roughness'])
    else: links.new(sep_c1.outputs['Green'], bsdf.inputs['Roughness'])

class VMDL_OT_clear_texture_slot(bpy.types.Operator):
    bl_idname = "vmdl.clear_texture_slot"; bl_label = "Clear Texture"; bl_description = "Odstraní texturu z tohoto slotu"; bl_options = {'REGISTER', 'UNDO'}
    texture_name: bpy.props.StringProperty()
    @classmethod
    def poll(cls, context): return context.material is not None
    def execute(self, context):
        mat = context.material
        if hasattr(mat, "vmdl_shader") and self.texture_name in mat.vmdl_shader.textures:
            mat.vmdl_shader.textures[self.texture_name].image = None
        return {'FINISHED'}

class VMDL_OT_load_image(bpy.types.Operator):
    bl_idname = "vmdl.load_image"; bl_label = "Load Image"; bl_description = "Načte obrázek (.png, .jpg, .dds...) do tohoto slotu"; bl_options = {'REGISTER', 'UNDO'}
    filepath: bpy.props.StringProperty(subtype="FILE_PATH"); filter_glob: bpy.props.StringProperty(default="*.png;*.jpg;*.jpeg;*.tga;*.bmp;*.dds", options={'HIDDEN'}); texture_name: bpy.props.StringProperty()
    def execute(self, context):
        mat = context.active_object.active_material; shader_props = mat.vmdl_shader
        tex_prop = shader_props.textures.get(self.texture_name)
        try: tex_prop.image = bpy.data.images.load(self.filepath, check_existing=True); self.report({'INFO'}, f"Obrázek načten.")
        except Exception as e: self.report({'ERROR'}, f"Chyba při načítání: {e}"); return {'CANCELLED'}
        return {'FINISHED'}
    def invoke(self, context, event): context.window_manager.fileselect_add(self); return {'RUNNING_MODAL'}

def update_tint_preview(self, context):
    mat = self.id_data
    if mat and mat.use_nodes:
        preview_node = mat.node_tree.nodes.get("VMDL_TintPreviewValue")
        if preview_node: preview_node.outputs[0].default_value = self.tint_preview

class VMDLTextureProperty(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Texture Name")
    image: bpy.props.PointerProperty(name="Image", type=bpy.types.Image, update=lambda self, context: setup_principled_node_graph(self.id_data))
class VMDLParameterProperty(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Parameter Name"); type: bpy.props.StringProperty(name="Parameter Type"); float_value: bpy.props.FloatProperty(name="Value"); vector_value: bpy.props.FloatVectorProperty(name="Value", size=4, subtype='COLOR'); bool_value: bpy.props.BoolProperty(name="Value")
def get_shader_enum_items(self, context):
    items = [(name, name, f"Shader: {name}") for name in sorted(SHADER_DEFINITIONS.keys())]
    if not items: items.append(("NONE", "No Shaders Defined", ""))
    return items
def delayed_shader_update(self, context):
    mat = self.id_data; self.parameters.clear(); self.textures.clear()
    if self.shader_name in SHADER_DEFINITIONS:
        shader_def = SHADER_DEFINITIONS[self.shader_name]
        for p_def in shader_def.get("parameters", []):
            new_p = self.parameters.add(); new_p.name=p_def["name"]; new_p.type=p_def["type"]
            if new_p.type=="float": new_p.float_value=p_def["default"]
            elif new_p.type=="vector4": new_p.vector_value=p_def["default"]
            elif new_p.type=="bool": new_p.bool_value=p_def["default"]
        for t_def in shader_def.get("textures", []):
            new_t = self.textures.add(); new_t.name = t_def["name"]
    setup_principled_node_graph(mat)
def update_shader_name(self, context): bpy.app.timers.register(lambda: delayed_shader_update(self, context))
class VMDLShaderProperties(bpy.types.PropertyGroup):
    shader_name: bpy.props.EnumProperty(name="Shader Name", items=get_shader_enum_items, update=update_shader_name)
    parameters: bpy.props.CollectionProperty(type=VMDLParameterProperty); textures: bpy.props.CollectionProperty(type=VMDLTextureProperty)
    tint_preview: bpy.props.FloatProperty(name="Tint Preview", description="Interaktivně vyberte barvu z palety", min=0.0, max=1.0, default=0.0, update=update_tint_preview)

class VMDL_OT_save_material_preset(bpy.types.Operator, ExportHelper):
    bl_idname = "vmdl.save_material_preset"; bl_label = "Save Material Preset"; filename_ext = ".mat.json"; filter_glob: bpy.props.StringProperty(default="*.mat.json", options={'HIDDEN'})
    @classmethod
    def poll(cls, context): return context.active_object and context.active_object.active_material and hasattr(context.active_object.active_material, "vmdl_shader")
    def execute(self, context):
        mat = context.active_object.active_material; props = mat.vmdl_shader; data = {'shader': props.shader_name, 'parameters': {}, 'textures': {}}
        for p in props.parameters:
            if p.type == "float": data['parameters'][p.name] = p.float_value
            elif p.type == "vector4": data['parameters'][p.name] = list(p.vector_value)
            elif p.type == "bool": data['parameters'][p.name] = p.bool_value
        for t in props.textures:
            if t.image and t.image.filepath: data['textures'][t.name] = bpy.path.abspath(t.image.filepath)
        with open(self.filepath, 'w') as f: json.dump(data, f, indent=4)
        self.report({'INFO'}, f"Preset uložen."); return {'FINISHED'}
class VMDL_OT_load_material_preset(bpy.types.Operator, ImportHelper):
    bl_idname = "vmdl.load_material_preset"; bl_label = "Load Material Preset"; filename_ext = ".mat.json"; filter_glob: bpy.props.StringProperty(default="*.mat.json", options={'HIDDEN'})
    @classmethod
    def poll(cls, context): return context.active_object and context.active_object.active_material
    def execute(self, context):
        mat = context.active_object.active_material
        try:
            with open(self.filepath, 'r') as f: data = json.load(f)
        except Exception as e: self.report({'ERROR'}, f"Chyba: {e}"); return {'CANCELLED'}
        shader_name = data.get('shader')
        if not shader_name or shader_name not in SHADER_DEFINITIONS: self.report({'ERROR'}, "Shader neexistuje."); return {'CANCELLED'}
        mat.vmdl_shader.shader_name = shader_name
        def apply_data():
            props = mat.vmdl_shader
            for n, v in data.get('parameters', {}).items():
                if n in props.parameters:
                    p = props.parameters[n]
                    if p.type=='float':p.float_value=v
                    elif p.type=='vector4':p.vector_value=v
                    elif p.type=='bool':p.bool_value=v
            for n, p in data.get('textures', {}).items():
                if n in props.textures:
                    try:
                        abs_p = bpy.path.abspath(os.path.normpath(p))
                        if os.path.exists(abs_p): props.textures[n].image = bpy.data.images.load(abs_p, check_existing=True)
                        else: self.report({'WARNING'}, f"Cesta neexistuje: '{abs_p}'")
                    except Exception as e: self.report({'WARNING'}, f"Nelze načíst: {e}")
            self.report({'INFO'}, f"Preset načten.")
        bpy.app.timers.register(apply_data); return {'FINISHED'}
class VMDL_OT_fix_invalid_shader(bpy.types.Operator):
    bl_idname = "vmdl.fix_invalid_shader"; bl_label = "Fix Invalid Shader"
    @classmethod
    def poll(cls, context): return context.active_object and context.active_object.active_material
    def execute(self, context):
        mat = context.active_object.active_material
        if SHADER_DEFINITIONS: mat.vmdl_shader.shader_name = sorted(SHADER_DEFINITIONS.keys())[0]; self.report({'INFO'}, "Shader opraven.")
        else: self.report({'ERROR'}, "Nejsou definovány shadery."); return {'CANCELLED'}
        return {'FINISHED'}
class VMDL_MT_create_material_menu(bpy.types.Menu):
    bl_idname = "VMDL_MT_create_material_menu"; bl_label = "Create VMDL Material"
    def draw(self, context):
        layout = self.layout; keys = sorted(SHADER_DEFINITIONS.keys())
        if not keys: layout.label(text="Žádné shadery nejsou definovány!", icon='ERROR'); return
        for name in keys: op = layout.operator("vmdl.create_shader_material", text=name); op.shader_name_prop = name
class VMDL_OT_create_shader_material(bpy.types.Operator):
    bl_idname = "vmdl.create_shader_material"; bl_label = "Create VMDL Shader Material"; bl_description = "Vytvoří nový materiál s vybraným VMDL shaderem"; bl_options = {'REGISTER', 'UNDO'}
    shader_name_prop: bpy.props.StringProperty(name="Shader Name")
    @classmethod
    def poll(cls, context): return context.active_object and context.active_object.type == 'MESH'
    def execute(self, context):
        obj = context.active_object; mat_name = f"M_{obj.name}_{self.shader_name_prop.split('.')[0]}"
        mat = bpy.data.materials.new(name=mat_name); mat.use_nodes = True
        obj.data.materials.append(mat); obj.active_material = mat
        mat.vmdl_shader.shader_name = self.shader_name_prop
        self.report({'INFO'}, f"Materiál '{mat.name}' vytvořen a přiřazen.")
        return {'FINISHED'}