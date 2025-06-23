import bpy
import os
from .constants import SHADER_TYPES

def update_texture_image(self, context, tex_prop_name):
    """
    Aktualizuje obrázek v image node, když se změní v UI.
    tex_prop_name je název vlastnosti v PropertyGroup (např. 'albedo_image').
    """
    mat = context.material
    if not mat or not mat.use_nodes:
        return
    
    # Odvodíme název node z názvu property (např. 'albedo_image' -> 'Albedo')
    node_name = tex_prop_name.replace("_image", "").capitalize()
    
    nodes = mat.node_tree.nodes
    tex_node = next((n for n in nodes if n.type == 'TEX_IMAGE' and n.label == node_name), None)
    
    image = getattr(self, tex_prop_name, None)
    if tex_node and image:
        tex_node.image = image
    elif tex_node:
        tex_node.image = None

class VMDLShaderProperties(bpy.types.PropertyGroup):
    shader_type: bpy.props.EnumProperty(
        items=[(s, s, "") for s in SHADER_TYPES],
        name="Shader Type"
    )

    # --- Nové Vector Barvy ---
    color1: bpy.props.FloatVectorProperty(
        name="Color1 (Řízení)",
        description="R: Volné, G: Drsnost, B: Síla Normal, A: Saturace",
        subtype='COLOR',
        size=4,
        default=(0.5, 0.5, 1.0, 1.0),
        min=0, max=1
    )
    color2: bpy.props.FloatVectorProperty(
        name="Color2 (Prolínání)",
        description="RGBA kanály pro prolínání textur",
        subtype='COLOR',
        size=4,
        default=(0.0, 0.0, 0.0, 1.0),
        min=0, max=1
    )

    # --- ShipStandard / Standard_dirt ---
    albedo_image: bpy.props.PointerProperty(
        name="Albedo", type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "albedo_image")
    )
    normal_image: bpy.props.PointerProperty(
        name="Normal", type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "normal_image")
    )
    roughness_image: bpy.props.PointerProperty(
        name="Roughness", type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "roughness_image")
    )
    metallic_image: bpy.props.PointerProperty(
        name="Metallic", type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "metallic_image")
    )
    
    # --- Pouze ShipStandard ---
    smoothness: bpy.props.FloatProperty(name="Smoothness", default=0.5, min=0, max=1)
    tint_color: bpy.props.FloatVectorProperty(name="Tint Color", subtype='COLOR', default=(1,1,1), min=0, max=1)

    # --- Pouze Standard_dirt ---
    dirt_image: bpy.props.PointerProperty(
        name="Dirt", type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "dirt_image")
    )

    # --- Pouze ShipGlass ---
    opacity: bpy.props.FloatProperty(name="Opacity", default=0.2, min=0, max=1)
    fresnel_power: bpy.props.FloatProperty(name="Fresnel Power", default=5.0)
    reflectivity: bpy.props.FloatProperty(name="Reflectivity", default=0.5, min=0, max=1)
    opacity_image: bpy.props.PointerProperty(
        name="Opacity", type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "opacity_image")
    )

    # --- Pouze Layered4 ---
    blend_strength: bpy.props.FloatProperty(name="Blend Strength", default=1.0)
    global_tint: bpy.props.FloatVectorProperty(name="Global Tint", subtype='COLOR', default=(1,1,1), min=0, max=1)
    uv_scale: bpy.props.FloatVectorProperty(name="UV Scale", size=2, default=(1.0, 1.0))
    layer1_image: bpy.props.PointerProperty(name="Layer1", type=bpy.types.Image, update=lambda self, context: update_texture_image(self, context, "layer1_image"))
    layer2_image: bpy.props.PointerProperty(name="Layer2", type=bpy.types.Image, update=lambda self, context: update_texture_image(self, context, "layer2_image"))
    layer3_image: bpy.props.PointerProperty(name="Layer3", type=bpy.types.Image, update=lambda self, context: update_texture_image(self, context, "layer3_image"))
    layer4_image: bpy.props.PointerProperty(name="Layer4", type=bpy.types.Image, update=lambda self, context: update_texture_image(self, context, "layer4_image"))


class VMDL_OT_create_shader_material(bpy.types.Operator):
    bl_idname = "vmdl.create_shader_material"
    bl_label = "Create VMDL Shader Material"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        shader_type = context.scene.vmdl_export.shader_type_to_create

        # --- NOVINKA: Automatické vytvoření Vertex Color vrstev ---
        if obj.data.vertex_colors:
            if 'Color1' not in obj.data.vertex_colors:
                obj.data.vertex_colors.new(name="Color1")
                self.report({'INFO'}, "Vytvořena chybějící Vertex Color vrstva 'Color1'.")
            if 'Color2' not in obj.data.vertex_colors:
                obj.data.vertex_colors.new(name="Color2")
                self.report({'INFO'}, "Vytvořena chybějící Vertex Color vrstva 'Color2'.")
        else: # Pokud neexistuje žádná, vytvoříme obě
            obj.data.vertex_colors.new(name="Color1")
            obj.data.vertex_colors.new(name="Color2")
            self.report({'INFO'}, "Vytvořeny chybějící Vertex Color vrstvy 'Color1' a 'Color2'.")


        mat = bpy.data.materials.new(name=f"M_{obj.name}_{shader_type}")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        output = nodes.new(type='ShaderNodeOutputMaterial')
        output.location = (400, 0)
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf.location = (200, 0)
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

        mat.vmdl_shader.shader_type = shader_type

        # --- Speciální případ: ShipGlass (jednoduchý) ---
        if shader_type == 'ShipGlass':
            bsdf.inputs['Transmission'].default_value = 1.0
            bsdf.inputs['Roughness'].default_value = 0.1
            self.report({'INFO'}, f"Materiál '{mat.name}' typu '{shader_type}' vytvořen.")
            if obj.data.materials: obj.data.materials.append(mat)
            else: obj.data.materials.append(mat)
            return {'FINISHED'}

        # --- Komplexní setup pro ostatní shadery ---
        
        # Atributy pro Vertex Colors
        attr_color1 = nodes.new(type='ShaderNodeAttribute')
        attr_color1.attribute_name = "Color1"
        attr_color1.location = (-800, 200)

        attr_color2 = nodes.new(type='ShaderNodeAttribute')
        attr_color2.attribute_name = "Color2"
        attr_color2.location = (-800, -200)

        # Zpracování Color1
        sep_color1 = nodes.new(type='ShaderNodeSeparateColor')
        sep_color1.location = (-600, 200)
        links.new(attr_color1.outputs['Color'], sep_color1.inputs['Color'])
        
        links.new(sep_color1.outputs['Green'], bsdf.inputs['Roughness']) # G -> Roughness

        # Zpracování saturace přes HSV
        hsv_node = nodes.new(type='ShaderNodeHueSaturation')
        hsv_node.location = (0, 200)
        # OPRAVA: Propojení Alpha kanálu přímo z Attribute node
        links.new(attr_color1.outputs['Alpha'], hsv_node.inputs['Saturation']) # A -> Saturation
        links.new(hsv_node.outputs['Color'], bsdf.inputs['Base Color'])

        # Setup pro Normal Map
        normal_tex = nodes.new('ShaderNodeTexImage')
        normal_tex.label = "Normal"
        normal_tex.location = (-600, -500)
        normal_map = nodes.new('ShaderNodeNormalMap')
        normal_map.location = (-400, -500)
        links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
        links.new(sep_color1.outputs['Blue'], normal_map.inputs['Strength']) # B -> Normal Strength
        links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])

        # --- Shader-specifická logika pro barvu ---
        if shader_type == 'ShipStandard':
            albedo_tex = nodes.new('ShaderNodeTexImage')
            albedo_tex.label = "Albedo"
            albedo_tex.location = (-200, 400)
            links.new(albedo_tex.outputs['Color'], hsv_node.inputs['Color'])

        elif shader_type == 'Standard_dirt':
            sep_color2 = nodes.new(type='ShaderNodeSeparateColor')
            sep_color2.location = (-600, -200)
            links.new(attr_color2.outputs['Color'], sep_color2.inputs['Color'])

            albedo_tex = nodes.new('ShaderNodeTexImage')
            albedo_tex.label = "Albedo"
            albedo_tex.location = (-400, 600)

            dirt_tex = nodes.new('ShaderNodeTexImage')
            dirt_tex.label = "Dirt"
            dirt_tex.location = (-400, 300)

            mix_dirt = nodes.new(type='ShaderNodeMix')
            mix_dirt.data_type = 'RGBA'
            mix_dirt.location = (-200, 400)
            
            links.new(albedo_tex.outputs['Color'], mix_dirt.inputs['A'])
            links.new(dirt_tex.outputs['Color'], mix_dirt.inputs['B'])
            links.new(sep_color2.outputs['Red'], mix_dirt.inputs['Factor']) # Color2.R -> Mix Factor
            links.new(mix_dirt.outputs['Result'], hsv_node.inputs['Color'])

        elif shader_type == 'Layered4':
            sep_color2 = nodes.new(type='ShaderNodeSeparateColor')
            sep_color2.location = (-600, -200)
            links.new(attr_color2.outputs['Color'], sep_color2.inputs['Color'])

            tex1 = nodes.new('ShaderNodeTexImage'); tex1.label = "Layer1"; tex1.location = (-600, 1000)
            tex2 = nodes.new('ShaderNodeTexImage'); tex2.label = "Layer2"; tex2.location = (-600, 750)
            tex3 = nodes.new('ShaderNodeTexImage'); tex3.label = "Layer3"; tex3.location = (-600, 500)
            tex4 = nodes.new('ShaderNodeTexImage'); tex4.label = "Layer4"; tex4.location = (-600, 250)

            mix1 = nodes.new('ShaderNodeMix'); mix1.data_type = 'RGBA'; mix1.location = (-400, 875)
            mix2 = nodes.new('ShaderNodeMix'); mix2.data_type = 'RGBA'; mix2.location = (-200, 750)
            mix3 = nodes.new('ShaderNodeMix'); mix3.data_type = 'RGBA'; mix3.location = (0, 625)

            # Prolínání vrstev pomocí R, G, B kanálů z Color2
            links.new(tex1.outputs['Color'], mix1.inputs['A'])
            links.new(tex2.outputs['Color'], mix1.inputs['B'])
            links.new(sep_color2.outputs['Red'], mix1.inputs['Factor'])

            links.new(mix1.outputs['Result'], mix2.inputs['A'])
            links.new(tex3.outputs['Color'], mix2.inputs['B'])
            links.new(sep_color2.outputs['Green'], mix2.inputs['Factor'])

            links.new(mix2.outputs['Result'], mix3.inputs['A'])
            links.new(tex4.outputs['Color'], mix3.inputs['B'])
            links.new(sep_color2.outputs['Blue'], mix3.inputs['Factor'])

            links.new(mix3.outputs['Result'], hsv_node.inputs['Color'])

        # Připojit materiál k objektu
        if obj.data.materials:
            obj.data.materials.append(mat)
        else:
            obj.data.materials.append(mat)
        
        obj.active_material_index = len(obj.data.materials) - 1

        self.report({'INFO'}, f"Materiál '{mat.name}' typu '{shader_type}' vytvořen a přiřazen.")
        return {'FINISHED'}