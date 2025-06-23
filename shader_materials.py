import bpy
from .shader_definitions import SHADER_DEFINITIONS

# --- Nová struktura pro dynamické vlastnosti ---

class VMDLTextureProperty(bpy.types.PropertyGroup):
    """Vlastnost pro jednu texturu v materiálu."""
    name: bpy.props.StringProperty(name="Texture Name")
    image: bpy.props.PointerProperty(name="Image", type=bpy.types.Image, update=lambda self, context: setup_principled_node_graph(context.material))

class VMDLParameterProperty(bpy.types.PropertyGroup):
    """Vlastnost pro jeden parametr v materiálu."""
    name: bpy.props.StringProperty(name="Parameter Name")
    type: bpy.props.StringProperty(name="Parameter Type") # 'float', 'vector4', 'bool'
    
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

def update_shader(self, context):
    """
    Klíčová funkce. Spustí se, když uživatel změní shader v UI.
    Vymaže staré parametry/textury a načte nové podle definice.
    """
    # Použijeme invoke_props_dialog, abychom se vyhnuli problémům s kontextem
    bpy.app.timers.register(lambda: delayed_update(self, context))

def delayed_update(self, context):
    self.parameters.clear()
    self.textures.clear()

    if self.shader_name not in SHADER_DEFINITIONS:
        return

    shader_def = SHADER_DEFINITIONS[self.shader_name]

    # Načtení parametrů
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
    
    # Načtení textur
    for tex_def in shader_def.get("textures", []):
        new_tex = self.textures.add()
        new_tex.name = tex_def["name"]
    
    if context.material:
        setup_principled_node_graph(context.material)


class VMDLShaderProperties(bpy.types.PropertyGroup):
    """Hlavní kontejner pro vlastnosti VMDL materiálu."""
    shader_name: bpy.props.EnumProperty(
        name="Shader Name",
        description="Vyberte herní shader",
        items=get_shader_enum_items,
        update=update_shader
    )
    
    parameters: bpy.props.CollectionProperty(type=VMDLParameterProperty)
    textures: bpy.props.CollectionProperty(type=VMDLTextureProperty)


# --- Operátor a pomocné funkce ---

def setup_principled_node_graph(mat):
    """
    Vytvoří jednoduchý náhledový node-graph.
    Pokusí se najít a zapojit běžné textury.
    """
    if not mat or not mat.use_nodes:
        return

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Najdeme existující BSDF nebo vytvoříme nový
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf:
        nodes.clear()
        output = nodes.new(type='ShaderNodeOutputMaterial')
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    # Odpojíme staré textury
    for input in bsdf.inputs:
        if input.is_linked:
            links.remove(input.links[0])
    
    # Smažeme staré image a normal map nody
    for node in nodes:
        if node.type in ('TEX_IMAGE', 'NORMAL_MAP') and node.label.startswith("VMDL_"):
            nodes.remove(node)

    shader_props = mat.vmdl_shader

    # Najdi běžné textury a zapoj je
    y_offset = 300
    for tex_prop in shader_props.textures:
        if not tex_prop.image:
            continue

        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.image = tex_prop.image
        tex_node.label = "VMDL_" + tex_prop.name

        name_lower = tex_prop.name.lower()
        if "diffuse" in name_lower or "albedo" in name_lower:
            tex_node.location = (-300, y_offset)
            links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
        elif "bump" in name_lower or "normal" in name_lower:
            tex_node.location = (-300, y_offset)
            if tex_node.image:
                tex_node.image.colorspace_settings.name = 'Non-Color'
            normal_map_node = nodes.new('ShaderNodeNormalMap')
            normal_map_node.location = (-100, y_offset)
            normal_map_node.label = "VMDL_" + tex_prop.name + "_map"
            links.new(tex_node.outputs['Color'], normal_map_node.inputs['Color'])
            links.new(normal_map_node.outputs['Normal'], bsdf.inputs['Normal'])
        elif "specular" in name_lower:
            tex_node.location = (-300, y_offset)
            links.new(tex_node.outputs['Color'], bsdf.inputs['Specular IOR Level'])
        elif "roughness" in name_lower:
            tex_node.location = (-300, y_offset)
            links.new(tex_node.outputs['Color'], bsdf.inputs['Roughness'])
        elif "metallic" in name_lower:
            tex_node.location = (-300, y_offset)
            links.new(tex_node.outputs['Color'], bsdf.inputs['Metallic'])
        else:
            # Nezapojené textury dáme stranou
            tex_node.location = (-500, y_offset)
        
        y_offset -= 300


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
            self.report({'ERROR'}, "V souboru 'shader_definitions.py' nejsou definovány žádné shadery.")
            return {'CANCELLED'}

        default_shader = shader_keys[0]
        
        mat = bpy.data.materials.new(name=f"M_{obj.name}_{default_shader.split('.')[0]}")
        mat.use_nodes = True
        
        if obj.data.materials:
            obj.data.materials.append(mat)
        else:
            obj.data.materials.append(mat)
        obj.active_material_index = len(obj.data.materials) - 1
        
        # Přiřadíme shader, což automaticky spustí 'update_shader' funkci
        mat.vmdl_shader.shader_name = default_shader

        self.report({'INFO'}, f"Materiál '{mat.name}' typu '{default_shader}' vytvořen.")
        return {'FINISHED'}