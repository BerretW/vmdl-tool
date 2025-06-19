import bpy
import os

def update_texture_image(self, context, tex_name):
    mat = context.material
    if not mat or not mat.use_nodes:
        return
    nodes = mat.node_tree.nodes
    tex_node = next((n for n in nodes if n.type == 'TEX_IMAGE' and n.name == tex_name), None)
    image = getattr(self, tex_name.lower().replace(" ", "_") + "_image", None)
    if tex_node and image:
        tex_node.image = image

class VMDLShaderProperties(bpy.types.PropertyGroup):
    shader_type: bpy.props.EnumProperty(
        items=[(s,s,"") for s in ["ShipStandard", "ShipGlass", "Layered4"]],
        name="Shader Type"
    )

    # ShipStandard / Common
    albedo_image: bpy.props.PointerProperty(
        name="Albedo",
        type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "Albedo")
    )
    normal_image: bpy.props.PointerProperty(
        name="Normal",
        type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "Normal")
    )

    # ShipStandard
    smoothness: bpy.props.FloatProperty(name="Smoothness", default=0.5, min=0, max=1)
    tint_color: bpy.props.FloatVectorProperty(name="Tint Color", subtype='COLOR', default=(1,1,1), min=0, max=1)
    roughness_image: bpy.props.PointerProperty(
        name="Roughness",
        type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "Roughness")
    )
    metallic_image: bpy.props.PointerProperty(
        name="Metallic",
        type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "Metallic")
    )

    # ShipGlass
    opacity: bpy.props.FloatProperty(name="Opacity", default=0.2, min=0, max=1)
    fresnel_power: bpy.props.FloatProperty(name="Fresnel Power", default=5.0)
    reflectivity: bpy.props.FloatProperty(name="Reflectivity", default=0.5, min=0, max=1)
    opacity_image: bpy.props.PointerProperty(
        name="Opacity Map",
        type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "Opacity")
    )

    # Layered4
    blend_strength: bpy.props.FloatProperty(name="Blend Strength", default=1.0)
    global_tint: bpy.props.FloatVectorProperty(name="Global Tint", subtype='COLOR', default=(1,1,1), min=0, max=1)
    uv_scale: bpy.props.FloatVectorProperty(name="UV Scale", size=2, default=(1.0, 1.0))
    layer1_image: bpy.props.PointerProperty(
        name="Layer 1",
        type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "Layer 1")
    )
    layer2_image: bpy.props.PointerProperty(
        name="Layer 2",
        type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "Layer 2")
    )
    layer3_image: bpy.props.PointerProperty(
        name="Layer 3",
        type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "Layer 3")
    )
    layer4_image: bpy.props.PointerProperty(
        name="Layer 4",
        type=bpy.types.Image,
        update=lambda self, context: update_texture_image(self, context, "Layer 4")
    )


class VMDL_OT_create_shader_material(bpy.types.Operator):
    bl_idname = "vmdl.create_shader_material"
    bl_label = "Create VMDL Shader Material"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        shader_type = context.scene.vmdl_export.shader_type_to_create

        mat = bpy.data.materials.new(name=f"M_{obj.name}_{shader_type}")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        output = nodes.new(type='ShaderNodeOutputMaterial')
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

        mat.vmdl_shader.shader_type = shader_type

        if shader_type == 'ShipStandard' or shader_type == 'Layered4':
            # Albedo
            albedo = nodes.new('ShaderNodeTexImage')
            albedo.label = "Albedo"
            albedo.name = "Albedo"
            mat.vmdl_shader.albedo_texture = ""
            links.new(albedo.outputs['Color'], bsdf.inputs['Base Color'])

            # Normal
            normal = nodes.new('ShaderNodeTexImage')
            normal.label = "Normal"
            normal.name = "Normal"
            mat.vmdl_shader.normal_texture = ""
            normal_map = nodes.new('ShaderNodeNormalMap')
            links.new(normal.outputs['Color'], normal_map.inputs['Color'])
            links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])

        if shader_type == 'Layered4':
            vtx_color = nodes.new('ShaderNodeVertexColor')
            vtx_color.layer_name = "Col"

            mix1 = nodes.new('ShaderNodeMixRGB')
            mix2 = nodes.new('ShaderNodeMixRGB')
            mix3 = nodes.new('ShaderNodeMixRGB')

            tex1 = nodes.new('ShaderNodeTexImage')
            tex1.label = "Layer 1"
            tex1.name = "Layer 1"
            mat.vmdl_shader.layer1_texture = ""

            tex2 = nodes.new('ShaderNodeTexImage')
            tex2.label = "Layer 2"
            tex2.name = "Layer 2"
            mat.vmdl_shader.layer2_texture = ""

            tex3 = nodes.new('ShaderNodeTexImage')
            tex3.label = "Layer 3"
            tex3.name = "Layer 3"
            mat.vmdl_shader.layer3_texture = ""

            tex4 = nodes.new('ShaderNodeTexImage')
            tex4.label = "Layer 4"
            tex4.name = "Layer 4"
            mat.vmdl_shader.layer4_texture = ""

            # Míchání vrstev pomocí vertex color (RGBA)
            links.new(tex1.outputs['Color'], mix1.inputs[1])
            links.new(tex2.outputs['Color'], mix1.inputs[2])
            links.new(vtx_color.outputs['Color'], mix1.inputs['Fac'])

            links.new(mix1.outputs['Color'], mix2.inputs[1])
            links.new(tex3.outputs['Color'], mix2.inputs[2])
            links.new(vtx_color.outputs['Color'], mix2.inputs['Fac'])

            links.new(mix2.outputs['Color'], mix3.inputs[1])
            links.new(tex4.outputs['Color'], mix3.inputs[2])
            links.new(vtx_color.outputs['Color'], mix3.inputs['Fac'])

            links.new(mix3.outputs['Color'], bsdf.inputs['Base Color'])

        if shader_type == 'ShipGlass':
            bsdf.inputs['Transmission'].default_value = 1.0
            mat.vmdl_shader.opacity_texture = ""

        # Připojit materiál k objektu
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

        self.report({'INFO'}, f"Materiál '{mat.name}' typu '{shader_type}' vytvořen a přiřazen.")
        return {'FINISHED'}