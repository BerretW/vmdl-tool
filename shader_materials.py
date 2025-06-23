import bpy
from .shader_definitions import SHADER_DEFINITIONS

def setup_principled_node_graph(mat):
    """
    Vytvoří nebo aktualizuje jednoduchý náhledový node-graph.
    Má speciální logiku pro Layered4 a obecnou pro ostatní.
    """
    if not mat or not mat.use_nodes:
        return

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf:
        nodes.clear()
        output = nodes.new(type='ShaderNodeOutputMaterial'); output.location = (300, 0)
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled'); bsdf.location = (0, 0)
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    # Odstraní staré VMDL nody pro čistou aktualizaci
    for node in list(nodes):
        if node.label.startswith("VMDL_"):
            nodes.remove(node)

    shader_props = mat.vmdl_shader
    shader_name = shader_props.shader_name

    # --- Společné řízení z Vertex Colors (Color1 a Color2) ---
    attr_c1 = nodes.new('ShaderNodeAttribute'); attr_c1.attribute_name = "Color1"; attr_c1.label = "VMDL_AttrC1"
    attr_c2 = nodes.new('ShaderNodeAttribute'); attr_c2.attribute_name = "Color2"; attr_c2.label = "VMDL_AttrC2"
    attr_c1.location = (-1000, 200)
    attr_c2.location = (-1000, -200)

    sep_c1 = nodes.new('ShaderNodeSeparateColor'); sep_c1.label = "VMDL_SepC1"; sep_c1.location = (-800, 200)
    links.new(attr_c1.outputs['Color'], sep_c1.inputs['Color'])
    
    # G kanál z Color1 řídí Roughness
    links.new(sep_c1.outputs['Green'], bsdf.inputs['Roughness'])

    # B kanál z Color1 řídí sílu normálové mapy
    bump_tex_prop = next((t for t in shader_props.textures if "bump" in t.name.lower() or "normal" in t.name.lower()), None)
    if bump_tex_prop and bump_tex_prop.image:
        norm_tex = nodes.new('ShaderNodeTexImage'); norm_tex.label = "VMDL_NormalTex"; norm_tex.image = bump_tex_prop.image
        norm_tex.image.colorspace_settings.name = 'Non-Color'
        norm_map = nodes.new('ShaderNodeNormalMap'); norm_map.label = "VMDL_NormalMap"
        norm_tex.location = (-500, -500); norm_map.location = (-250, -500)
        links.new(norm_tex.outputs['Color'], norm_map.inputs['Color'])
        links.new(sep_c1.outputs['Blue'], norm_map.inputs['Strength'])
        links.new(norm_map.outputs['Normal'], bsdf.inputs['Normal'])

    # --- Specifická logika pro Base Color ---
    if shader_name == "Layered4.vfx":
        # Logika pro 4-vrstvý shader
        sep_c2 = nodes.new('ShaderNodeSeparateColor'); sep_c2.label = "VMDL_SepC2"; sep_c2.location = (-800, -200)
        links.new(attr_c2.outputs['Color'], sep_c2.inputs['Color'])
        
        tex_nodes = {}
        y_pos = 600
        for i, layer_name in enumerate(["layer1tex", "layer2tex", "layer3tex", "layer4tex"]):
            tex_prop = shader_props.textures.get(layer_name)
            if tex_prop and tex_prop.image:
                tex_node = nodes.new('ShaderNodeTexImage')
                tex_node.label = f"VMDL_Layer{i+1}"
                tex_node.image = tex_prop.image
                tex_node.location = (-800, y_pos)
                tex_nodes[i] = tex_node
                y_pos -= 250
        
        if len(tex_nodes) >= 2:
            mix1 = nodes.new('ShaderNodeMixRGB'); mix1.label = "VMDL_Mix1"; mix1.location = (-550, 500)
            links.new(tex_nodes[0].outputs['Color'], mix1.inputs[1])
            links.new(tex_nodes[1].outputs['Color'], mix1.inputs[2])
            links.new(sep_c2.outputs['Red'], mix1.inputs['Fac'])
            last_mix_output = mix1.outputs['Color']

            if len(tex_nodes) >= 3:
                mix2 = nodes.new('ShaderNodeMixRGB'); mix2.label = "VMDL_Mix2"; mix2.location = (-350, 400)
                links.new(last_mix_output, mix2.inputs[1])
                links.new(tex_nodes[2].outputs['Color'], mix2.inputs[2])
                links.new(sep_c2.outputs['Green'], mix2.inputs['Fac'])
                last_mix_output = mix2.outputs['Color']

            if len(tex_nodes) >= 4:
                mix3 = nodes.new('ShaderNodeMixRGB'); mix3.label = "VMDL_Mix3"; mix3.location = (-150, 300)
                links.new(last_mix_output, mix3.inputs[1])
                links.new(tex_nodes[3].outputs['Color'], mix3.inputs[2])
                links.new(sep_c2.outputs['Blue'], mix3.inputs['Fac'])
                last_mix_output = mix3.outputs['Color']
            
            links.new(last_mix_output, bsdf.inputs['Base Color'])
    
    else:
        # Obecná logika pro ostatní shadery - najde Albedo/Diffuse
        albedo_tex_prop = next((t for t in shader_props.textures if "diffuse" in t.name.lower() or "albedo" in t.name.lower()), None)
        if albedo_tex_prop and albedo_tex_prop.image:
            albedo_tex = nodes.new('ShaderNodeTexImage'); albedo_tex.label = "VMDL_AlbedoTex"; albedo_tex.image = albedo_tex_prop.image
            albedo_tex.location = (-250, 300)
            links.new(albedo_tex.outputs['Color'], bsdf.inputs['Base Color'])


class VMDLTextureProperty(bpy.types.PropertyGroup):
    """Vlastnost pro jednu texturu v materiálu."""
    name: bpy.props.StringProperty(name="Texture Name")
    image: bpy.props.PointerProperty(
        name="Image", 
        type=bpy.types.Image, 
        update=lambda self, context: setup_principled_node_graph(context.material)
    )

class VMDLParameterProperty(bpy.types.PropertyGroup):
    """Vlastnost pro jeden parametr v materiálu."""
    name: bpy.props.StringProperty(name="Parameter Name")
    type: bpy.props.StringProperty(name="Parameter Type")
    
    float_value: bpy.props.FloatProperty(name="Value")
    vector_value: bpy.props.FloatVectorProperty(name="Value", size=4, subtype='COLOR')
    bool_value: bpy.props.BoolProperty(name="Value")

def get_shader_enum_items(self, context):
    """Dynamicky načte seznam shaderů z definic pro EnumProperty."""
    items = []
    keys = sorted(SHADER_DEFINITIONS.keys())
    for shader_name in keys:
        items.append((shader_name, shader_name, f"Shader: {shader_name}"))
    if not items:
        items.append(("NONE", "No Shaders Defined", "Please define shaders in shader_definitions.py"))
    return items

def delayed_shader_update(self, context):
    """Zpožděná funkce, která bezpečně aktualizuje properties materiálu."""
    mat = self.id_data
    if not isinstance(mat, bpy.types.Material):
        return

    self.parameters.clear()
    self.textures.clear()

    if self.shader_name not in SHADER_DEFINITIONS:
        return

    shader_def = SHADER_DEFINITIONS[self.shader_name]

    for param_def in shader_def.get("parameters", []):
        new_param = self.parameters.add()
        new_param.name = param_def["name"]
        new_param.type = param_def["type"]
        if new_param.type == "float":
            new_param.float_value = param_def["default"]
        elif new_param.type == "vector4":
            new_param.vector_value = param_def["default"]
        elif new_param.type == "bool":
            new_param.bool_value = param_def["default"]
    
    for tex_def in shader_def.get("textures", []):
        new_tex = self.textures.add()
        new_tex.name = tex_def["name"]
    
    setup_principled_node_graph(mat)

def update_shader_name(self, context):
    """Spustí časovač pro zpožděnou aktualizaci, aby se předešlo kontextovým chybám."""
    bpy.app.timers.register(lambda: delayed_shader_update(self, context))

class VMDLShaderProperties(bpy.types.PropertyGroup):
    """Hlavní kontejner pro vlastnosti VMDL materiálu."""
    shader_name: bpy.props.EnumProperty(
        name="Shader Name",
        description="Vyberte herní shader",
        items=get_shader_enum_items,
        update=update_shader_name
    )
    
    parameters: bpy.props.CollectionProperty(type=VMDLParameterProperty)
    textures: bpy.props.CollectionProperty(type=VMDLTextureProperty)

class VMDL_OT_create_shader_material(bpy.types.Operator):
    bl_idname = "vmdl.create_shader_material"
    bl_label = "Create VMDL Shader Material"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        
        shader_keys = sorted(SHADER_DEFINITIONS.keys())
        if not shader_keys:
            self.report({'ERROR'}, "V 'shader_definitions.py' nejsou definovány žádné shadery.")
            return {'CANCELLED'}

        default_shader = shader_keys[0]
        
        mat = bpy.data.materials.new(name=f"M_{obj.name}_{default_shader.split('.')[0]}")
        mat.use_nodes = True
        
        if len(obj.data.materials) > 0:
            obj.data.materials.append(mat)
        else:
            obj.data.materials.append(mat)
        obj.active_material_index = len(obj.data.materials) - 1
        
        mat.vmdl_shader.shader_name = default_shader

        self.report({'INFO'}, f"Materiál '{mat.name}' typu '{default_shader}' vytvořen.")
        return {'FINISHED'}