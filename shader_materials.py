import bpy
import json
import os
from bpy_extras.io_utils import ImportHelper, ExportHelper
from .shader_definitions import SHADER_DEFINITIONS

# ... (TŘÍDY OPERÁTORŮ, MENU A DALŠÍ ZŮSTÁVAJÍ STEJNÉ) ...
# ... (Níže je uvedena kompletní verze souboru, abyste měl jistotu) ...


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
        mat = context.active_object.active_material
        if not mat: 
            self.report({'ERROR'}, "Aktivní objekt nemá žádný materiál.")
            return {'CANCELLED'}
        
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

class VMDL_OT_save_material_preset(bpy.types.Operator, ExportHelper):
    """Uloží aktuální VMDL nastavení materiálu do JSON presetu."""
    bl_idname = "vmdl.save_material_preset"
    bl_label = "Save Material Preset"
    filename_ext = ".mat.json"
    filter_glob: bpy.props.StringProperty(default="*.mat.json", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        mat = context.active_object.active_material if context.active_object else None
        return mat and hasattr(mat, "vmdl_shader")

    def execute(self, context):
        mat = context.active_object.active_material
        shader_props = mat.vmdl_shader
        mat_data = {'shader': shader_props.shader_name, 'parameters': {}, 'textures': {}}
        
        for param in shader_props.parameters:
            if param.type == "float": mat_data['parameters'][param.name] = param.float_value
            elif param.type == "vector4": mat_data['parameters'][param.name] = list(param.vector_value)
            elif param.type == "bool": mat_data['parameters'][param.name] = param.bool_value
        
        for tex in shader_props.textures:
            if tex.image and tex.image.filepath:
                mat_data['textures'][tex.name] = bpy.path.abspath(tex.image.filepath)
        
        with open(self.filepath, 'w') as f:
            json.dump(mat_data, f, indent=4)
            
        self.report({'INFO'}, f"Preset uložen do {self.filepath}")
        return {'FINISHED'}

class VMDL_OT_load_material_preset(bpy.types.Operator, ImportHelper):
    """Načte VMDL nastavení materiálu z JSON presetu."""
    bl_idname = "vmdl.load_material_preset"
    bl_label = "Load Material Preset"
    filename_ext = ".mat.json"
    filter_glob: bpy.props.StringProperty(default="*.mat.json", options={'HIDDEN'})
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.active_material

    def execute(self, context):
        mat = context.active_object.active_material
        try:
            with open(self.filepath, 'r') as f:
                mat_data = json.load(f)
        except Exception as e:
            self.report({'ERROR'}, f"Chyba při čtení souboru presetu: {e}")
            return {'CANCELLED'}
        
        shader_name = mat_data.get('shader')
        if not shader_name or shader_name not in SHADER_DEFINITIONS:
            self.report({'ERROR'}, f"Shader '{shader_name}' v presetu neexistuje v definicích.")
            return {'CANCELLED'}
        
        mat.vmdl_shader.shader_name = shader_name
        
        def apply_data():
            shader_props = mat.vmdl_shader
            for name, value in mat_data.get('parameters', {}).items():
                if name in shader_props.parameters:
                    param = shader_props.parameters[name]
                    if param.type == 'float': param.float_value = value
                    elif param.type == 'vector4': param.vector_value = value
                    elif param.type == 'bool': param.bool_value = value
            
            for name, path in mat_data.get('textures', {}).items():
                if name in shader_props.textures:
                    try:
                        abs_path = bpy.path.abspath(os.path.normpath(path))
                        if os.path.exists(abs_path):
                           shader_props.textures[name].image = bpy.data.images.load(abs_path, check_existing=True)
                        else:
                           self.report({'WARNING'}, f"Cesta k textuře neexistuje: '{abs_path}'")
                    except Exception as e:
                        self.report({'WARNING'}, f"Nepodařilo se načíst texturu '{path}': {e}")
            
            self.report({'INFO'}, f"Preset '{os.path.basename(self.filepath)}' načten.")
        
        bpy.app.timers.register(apply_data)
        return {'FINISHED'}

class VMDL_OT_fix_invalid_shader(bpy.types.Operator):
    """Opraví neplatný shader na materiálu."""
    bl_idname = "vmdl.fix_invalid_shader"
    bl_label = "Fix Invalid Shader"
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.active_material
        
    def execute(self, context):
        mat = context.active_object.active_material
        if SHADER_DEFINITIONS:
            default_shader = sorted(SHADER_DEFINITIONS.keys())[0]
            mat.vmdl_shader.shader_name = default_shader
            self.report({'INFO'}, f"Shader opraven na výchozí: {default_shader}")
        else:
            self.report({'ERROR'}, "Nejsou definovány žádné shadery.")
            return {'CANCELLED'}
        return {'FINISHED'}

# =============================================================================
# FINÁLNÍ VERZE FUNKCE PRO TVORBU NODE-GRAPHU S PALETOVÝM TINTEM
# =============================================================================
def setup_principled_node_graph(mat):
    """
    Vytvoří nebo aktualizuje PBR náhledový node-graph, který reflektuje
    VMDL vlastnosti (Tint, Roughness, Specular, Normal, Albedo).
    """
    if not mat or not mat.use_nodes:
        return

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # 1. Základní nastavení a úklid
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf:
        nodes.clear()
        output = nodes.new(type='ShaderNodeOutputMaterial'); output.location = (400, 0)
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled'); bsdf.location = (100, 0)
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    for node in list(nodes):
        if hasattr(node, "label") and node.label and node.label.startswith("VMDL_"):
            nodes.remove(node)

    shader_props = mat.vmdl_shader

    # 2. Získání Vertex Color a Textur
    active_obj = bpy.context.active_object
    obj_using_mat = active_obj if active_obj and active_obj.active_material == mat else next((o for o in bpy.data.objects if o.active_material == mat), None)

    def find_texture(name_part):
        return next((t for t in shader_props.textures if name_part in t.name.lower()), None)

    albedo_tex_prop = find_texture("diffuse") or find_texture("albedo") or find_texture("layer1tex")
    tint_palette_tex_prop = find_texture("tintpalettetex")
    bump_tex_prop = find_texture("bumptex")
    roughness_tex_prop = find_texture("roughnesstex")
    specular_tex_prop = find_texture("speculartex")

    # 3. Vytvoření vstupních nodů (vlevo)
    x_pos = -1400 # Posuneme vše doleva, aby bylo více místa
    
    attr_c1 = None
    sep_c1 = None
    if obj_using_mat and "Color1" in obj_using_mat.data.vertex_colors:
        attr_c1 = nodes.new('ShaderNodeVertexColor'); attr_c1.layer_name = "Color1"; attr_c1.label = "VMDL_AttrC1"
        attr_c1.location = (x_pos, 200)
        sep_c1 = nodes.new('ShaderNodeSeparateColor'); sep_c1.label = "VMDL_SepC1"; sep_c1.location = (x_pos + 200, 200)
        links.new(attr_c1.outputs['Color'], sep_c1.inputs['Color'])

    albedo_tex_node = None
    if albedo_tex_prop and albedo_tex_prop.image:
        albedo_tex_node = nodes.new('ShaderNodeTexImage'); albedo_tex_node.label = "VMDL_AlbedoTex"; albedo_tex_node.image = albedo_tex_prop.image
        albedo_tex_node.location = (x_pos + 450, -50)

    # 4. Zpracování a propojení do BSDF
    
    # --- TINT & BASE COLOR (s paletovou texturou) ---
    if albedo_tex_node and sep_c1 and tint_palette_tex_prop and tint_palette_tex_prop.image:
        # R kanál z Vertex Color slouží jako Y souřadnice (V) pro vyhledání barvy v paletě.
        # X souřadnice (U) je konstantní 0.5.
        
        # Sestavíme nový UV vektor
        combine_uv = nodes.new('ShaderNodeCombineXYZ'); combine_uv.label = "VMDL_CombineUV"
        combine_uv.location = (x_pos + 450, 350)
        combine_uv.inputs[1].default_value = 1.0  # U souřadnice
        links.new(sep_c1.outputs['Red'], combine_uv.inputs[0])  # R kanál -> V souřadnice
        
        # Vytvoříme node pro paletovou texturu
        palette_tex_node = nodes.new('ShaderNodeTexImage'); palette_tex_node.label = "VMDL_TintPaletteTex"
        palette_tex_node.image = tint_palette_tex_prop.image
        palette_tex_node.interpolation = 'Closest' # Chceme přesnou barvu, ne interpolaci
        palette_tex_node.location = (x_pos + 700, 350)
        links.new(combine_uv.outputs['Vector'], palette_tex_node.inputs['Vector'])

        # Smícháme Albedo texturu s barvou z palety
        mix_tint = nodes.new('ShaderNodeMix'); mix_tint.label = "VMDL_TintMix"
        mix_tint.data_type = 'RGBA'
        mix_tint.blend_type = 'MULTIPLY'
        mix_tint.inputs['Factor'].default_value = 1.0
        mix_tint.location = (x_pos + 950, 50)
        links.new(albedo_tex_node.outputs['Color'], mix_tint.inputs['A'])
        links.new(palette_tex_node.outputs['Color'], mix_tint.inputs['B'])
        links.new(mix_tint.outputs['Result'], bsdf.inputs['Base Color'])
    elif albedo_tex_node:
        # Pokud není tintování, propojíme jen Albedo
        links.new(albedo_tex_node.outputs['Color'], bsdf.inputs['Base Color'])

    # --- ROUGHNESS ---
    if roughness_tex_prop and roughness_tex_prop.image:
        rough_tex_node = nodes.new('ShaderNodeTexImage'); rough_tex_node.label = "VMDL_RoughTex"; rough_tex_node.image = roughness_tex_prop.image
        rough_tex_node.image.colorspace_settings.name = 'Non-Color'
        rough_tex_node.location = (x_pos + 450, -250)
        links.new(rough_tex_node.outputs['Color'], bsdf.inputs['Roughness'])
    elif sep_c1:
        links.new(sep_c1.outputs['Green'], bsdf.inputs['Roughness'])

    # --- SPECULAR ---
    if specular_tex_prop and specular_tex_prop.image:
        spec_tex_node = nodes.new('ShaderNodeTexImage'); spec_tex_node.label = "VMDL_SpecTex"; spec_tex_node.image = specular_tex_prop.image
        spec_tex_node.image.colorspace_settings.name = 'Non-Color'
        spec_tex_node.location = (x_pos + 450, -450)
        links.new(spec_tex_node.outputs['Color'], bsdf.inputs['Specular IOR Level'])

    # --- NORMAL ---
    if bump_tex_prop and bump_tex_prop.image:
        norm_tex_node = nodes.new('ShaderNodeTexImage'); norm_tex_node.label = "VMDL_NormalTex"; norm_tex_node.image = bump_tex_prop.image
        norm_tex_node.image.colorspace_settings.name = 'Non-Color'
        norm_map = nodes.new('ShaderNodeNormalMap'); norm_map.label = "VMDL_NormalMap"
        norm_tex_node.location = (x_pos + 200, -650)
        norm_map.location = (x_pos + 450, -650)
        links.new(norm_tex_node.outputs['Color'], norm_map.inputs['Color'])
        if sep_c1:
            links.new(sep_c1.outputs['Blue'], norm_map.inputs['Strength'])
        links.new(norm_map.outputs['Normal'], bsdf.inputs['Normal'])

# =============================================================================
# ZBYTEK SOUBORU ZŮSTÁVÁ BEZE ZMĚNY
# =============================================================================

class VMDLTextureProperty(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Texture Name")
    image: bpy.props.PointerProperty(
        name="Image", 
        type=bpy.types.Image, 
        update=lambda self, context: setup_principled_node_graph(self.id_data)
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

class VMDL_MT_create_material_menu(bpy.types.Menu):
    bl_idname = "VMDL_MT_create_material_menu"
    bl_label = "Create VMDL Material"

    def draw(self, context):
        layout = self.layout
        shader_keys = sorted(SHADER_DEFINITIONS.keys())
        
        if not shader_keys:
            layout.label(text="Žádné shadery nejsou definovány!", icon='ERROR')
            return

        for shader_name in shader_keys:
            op = layout.operator("vmdl.create_shader_material", text=shader_name)
            op.shader_name_prop = shader_name

class VMDL_OT_create_shader_material(bpy.types.Operator):
    bl_idname = "vmdl.create_shader_material"
    bl_label = "Create VMDL Shader Material"
    bl_description = "Vytvoří nový materiál s vybraným VMDL shaderem"
    bl_options = {'REGISTER', 'UNDO'}

    shader_name_prop: bpy.props.StringProperty(name="Shader Name")

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        
        if not self.shader_name_prop:
            self.report({'ERROR'}, "Nebyl vybrán žádný shader.")
            return {'CANCELLED'}

        mat_name = f"M_{obj.name}_{self.shader_name_prop.split('.')[0]}"
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        
        obj.data.materials.append(mat)
        obj.active_material_index = len(obj.data.materials) - 1
        
        mat.vmdl_shader.shader_name = self.shader_name_prop
        
        self.report({'INFO'}, f"Materiál '{mat.name}' typu '{self.shader_name_prop}' vytvořen.")
        return {'FINISHED'}