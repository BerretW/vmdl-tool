import bpy
from .shader_definitions import SHADER_DEFINITIONS

class VMDL_OT_load_image(bpy.types.Operator):
    """Operátor pro načtení obrázku (včetně DDS) do vybraného slotu."""
    bl_idname = "vmdl.load_image"
    bl_label = "Load Image"
    bl_description = "Načte obrázek (.png, .jpg, .dds...) do tohoto slotu"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(
        default="*.png;*.jpg;*.jpeg;*.tga;*.bmp;*.dds",
        options={'HIDDEN'},
    )
    
    texture_name: bpy.props.StringProperty()

    def execute(self, context):
        mat = context.material
        if not mat: return {'CANCELLED'}
        
        shader_props = mat.vmdl_shader
        tex_prop = shader_props.textures.get(self.texture_name)
        if not tex_prop:
            self.report({'ERROR'}, f"Texture slot '{self.texture_name}' not found.")
            return {'CANCELLED'}

        try:
            image = bpy.data.images.load(self.filepath, check_existing=True)
            tex_prop.image = image
            self.report({'INFO'}, f"Obrázek '{image.name}' načten.")
        except Exception as e:
            self.report({'ERROR'}, f"Chyba při načítání obrázku: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def setup_principled_node_graph(mat):
    """
    Vytvoří nebo aktualizuje jednoduchý náhledový node-graph.
    """
    if not mat or not mat.use_nodes:
        return

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf:
        nodes.clear()
        output = nodes.new(type='ShaderNodeOutputMaterial'); output.location = (400, 0)
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled'); bsdf.location = (100, 0)
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    for node in list(nodes):
        if node.label.startswith("VMDL_"):
            nodes.remove(node)

    shader_props = mat.vmdl_shader
    shader_name = shader_props.shader_name

    attr_c1 = nodes.new('ShaderNodeAttribute'); attr_c1.attribute_name = "Color1"; attr_c1.label = "VMDL_AttrC1"
    attr_c2 = nodes.new('ShaderNodeAttribute'); attr_c2.attribute_name = "Color2"; attr_c2.label = "VMDL_AttrC2"
    attr_c1.location = (-1200, 200)
    attr_c2.location = (-1200, -200)

    sep_c1 = nodes.new('ShaderNodeSeparateColor'); sep_c1.label = "VMDL_SepC1"; sep_c1.location = (-1000, 200)
    links.new(attr_c1.outputs['Color'], sep_c1.inputs['Color'])
    
    links.new(sep_c1.outputs['Green'], bsdf.inputs['Roughness'])

    bump_tex_prop = next((t for t in shader_props.textures if "bumptex" == t.name.lower()), None)
    if bump_tex_prop and bump_tex_prop.image:
        norm_tex = nodes.new('ShaderNodeTexImage'); norm_tex.label = "VMDL_NormalTex"; norm_tex.image = bump_tex_prop.image
        if norm_tex.image: norm_tex.image.colorspace_settings.name = 'Non-Color'
        norm_map = nodes.new('ShaderNodeNormalMap'); norm_map.label = "VMDL_NormalMap"
        norm_tex.location = (-700, -600); norm_map.location = (-450, -600)
        links.new(norm_tex.outputs['Color'], norm_map.inputs['Color'])
        links.new(sep_c1.outputs['Blue'], norm_map.inputs['Strength'])
        links.new(norm_map.outputs['Normal'], bsdf.inputs['Normal'])

    # --- Zpracování Base Color ---
    base_color_input = bsdf.inputs['Base Color']
    last_color_output = None

    albedo_tex_prop = next((t for t in shader_props.textures if "diffuse" in t.name.lower() or "albedo" in t.name.lower() or "layer1tex" in t.name.lower()), None)
    if albedo_tex_prop and albedo_tex_prop.image:
        albedo_tex = nodes.new('ShaderNodeTexImage'); albedo_tex.label = "VMDL_AlbedoTex"; albedo_tex.image = albedo_tex_prop.image
        albedo_tex.location = (-700, 300)
        last_color_output = albedo_tex.outputs['Color']

    # --- NOVÁ LOGIKA PRO TINT PALETTE ---
    tint_palette_tex_prop = next((t for t in shader_props.textures if "tintpalettetex" in t.name.lower()), None)
    if tint_palette_tex_prop and tint_palette_tex_prop.image and last_color_output:
        tint_tex = nodes.new('ShaderNodeTexImage'); tint_tex.label = "VMDL_TintPalette"; tint_tex.image = tint_palette_tex_prop.image
        tint_tex.location = (-700, 0)
        
        # Použijeme R kanál z Color1 pro posun UV souřadnic
        combine_uv = nodes.new('ShaderNodeCombineXYZ'); combine_uv.label = "VMDL_TintUV"; combine_uv.location = (-950, 0)
        links.new(sep_c1.outputs['Red'], combine_uv.inputs['X'])
        links.new(combine_uv.outputs['Vector'], tint_tex.inputs['Vector'])
        
        # Smícháme barvu z palety s albedem
        mix_tint = nodes.new('ShaderNodeMix'); mix_tint.data_type = "RGBA"; mix_tint.blend_type = 'OVERLAY'
        mix_tint.label = "VMDL_TintMix"; mix_tint.location = (-450, 200)
        
        links.new(last_color_output, mix_tint.inputs['A'])
        links.new(tint_tex.outputs['Color'], mix_tint.inputs['B'])
        
        # Propojíme globální faktor tintu
        tint_factor_param = shader_props.parameters.get("tintpalettefactor")
        if tint_factor_param:
            mix_tint.inputs['Factor'].default_value = tint_factor_param.float_value
            
        last_color_output = mix_tint.outputs['Result']
    
    # --- LOGIKA PRO LAYERED4 ---
    if shader_name == "Layered4.vfx" and last_color_output:
        sep_c2 = nodes.new('ShaderNodeSeparateColor'); sep_c2.label = "VMDL_SepC2"; sep_c2.location = (-1000, -200)
        links.new(attr_c2.outputs['Color'], sep_c2.inputs['Color'])
        
        layer_tex_props = [shader_props.textures.get(name) for name in ["layer2tex", "layer3tex", "layer4tex"]]
        blend_channels = [sep_c2.outputs['Red'], sep_c2.outputs['Green'], sep_c2.outputs['Blue']]
        
        current_mix_y = 100
        for i, tex_prop in enumerate(layer_tex_props):
            if tex_prop and tex_prop.image:
                layer_tex = nodes.new('ShaderNodeTexImage'); layer_tex.label = f"VMDL_LayerTex{i+2}"; layer_tex.image = tex_prop.image
                layer_tex.location = (-700, current_mix_y)
                
                mix_layer = nodes.new('ShaderNodeMix'); mix_layer.data_type = "RGBA"
                mix_layer.label = f"VMDL_LayerMix{i+2}"; mix_layer.location = (-450, current_mix_y)
                
                links.new(last_color_output, mix_layer.inputs['A'])
                links.new(layer_tex.outputs['Color'], mix_layer.inputs['B'])
                links.new(blend_channels[i], mix_layer.inputs['Factor'])
                last_color_output = mix_layer.outputs['Result']
                current_mix_y -= 150
    
    if last_color_output:
        links.new(last_color_output, base_color_input)

class VMDLTextureProperty(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Texture Name")
    image: bpy.props.PointerProperty(
        name="Image", 
        type=bpy.types.Image, 
        update=lambda self, context: setup_principled_node_graph(context.material)
    )

class VMDLParameterProperty(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Parameter Name")
    type: bpy.props.StringProperty(name="Parameter Type")
    float_value: bpy.props.FloatProperty(name="Value")
    vector_value: bpy.props.FloatVectorProperty(name="Value", size=4, subtype='COLOR')
    bool_value: bpy.props.BoolProperty(name="Value")

def get_shader_enum_items(self, context):
    items = []
    keys = sorted(SHADER_DEFINITIONS.keys())
    for shader_name in keys:
        items.append((shader_name, shader_name, f"Shader: {shader_name}"))
    if not items:
        items.append(("NONE", "No Shaders Defined", "Please define shaders in shader_definitions.py"))
    return items

def delayed_shader_update(self, context):
    mat = self.id_data
    if not isinstance(mat, bpy.types.Material): return
    self.parameters.clear(); self.textures.clear()
    if self.shader_name not in SHADER_DEFINITIONS: return
    shader_def = SHADER_DEFINITIONS[self.shader_name]
    for param_def in shader_def.get("parameters", []):
        new_param = self.parameters.add()
        new_param.name = param_def["name"]
        new_param.type = param_def["type"]
        if new_param.type == "float": new_param.float_value = param_def["default"]
        elif new_param.type == "vector4": new_param.vector_value = param_def["default"]
        elif new_param.type == "bool": new_param.bool_value = param_def["default"]
    for tex_def in shader_def.get("textures", []):
        new_tex = self.textures.add()
        new_tex.name = tex_def["name"]
    setup_principled_node_graph(mat)

def update_shader_name(self, context):
    bpy.app.timers.register(lambda: delayed_shader_update(self, context))

class VMDLShaderProperties(bpy.types.PropertyGroup):
    shader_name: bpy.props.EnumProperty(name="Shader Name", description="Vyberte herní shader", items=get_shader_enum_items, update=update_shader_name)
    parameters: bpy.props.CollectionProperty(type=VMDLParameterProperty)
    textures: bpy.props.CollectionProperty(type=VMDLTextureProperty)

class VMDL_OT_create_shader_material(bpy.types.Operator):
    bl_idname = "vmdl.create_shader_material"
    bl_label = "Create VMDL Shader Material"
    @classmethod
    def poll(cls, context): return context.active_object and context.active_object.type == 'MESH'
    def execute(self, context):
        obj = context.active_object
        shader_keys = sorted(SHADER_DEFINITIONS.keys())
        if not shader_keys:
            self.report({'ERROR'}, "V 'shader_definitions.py' nejsou definovány žádné shadery."); return {'CANCELLED'}
        default_shader = shader_keys[0]
        mat = bpy.data.materials.new(name=f"M_{obj.name}_{default_shader.split('.')[0]}")
        mat.use_nodes = True
        if obj.data.materials: obj.data.materials.append(mat)
        else: obj.data.materials.append(mat)
        obj.active_material_index = len(obj.data.materials) - 1
        mat.vmdl_shader.shader_name = default_shader
        self.report({'INFO'}, f"Materiál '{mat.name}' typu '{default_shader}' vytvořen."); return {'FINISHED'}