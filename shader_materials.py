# vmdl_plugin/shader_materials.py

import bpy
from .constants import SHADER_TYPES

class VMDLShaderProperties(bpy.types.PropertyGroup):
    shader_type: bpy.props.EnumProperty(items=[(s,s,"") for s in SHADER_TYPES], name="Shader Type")
    
    # Parametry pro ShipStandard
    smoothness: bpy.props.FloatProperty(name="Smoothness", default=0.5, min=0, max=1)
    tint_color: bpy.props.FloatVectorProperty(name="Tint Color", subtype='COLOR', default=(1,1,1), min=0, max=1)

    # Parametry pro ShipGlass
    opacity: bpy.props.FloatProperty(name="Opacity", default=0.2, min=0, max=1)
    fresnel_power: bpy.props.FloatProperty(name="Fresnel Power", default=5.0)
    reflectivity: bpy.props.FloatProperty(name="Reflectivity", default=0.5, min=0, max=1)

    # Parametry pro Layered4
    blend_strength: bpy.props.FloatProperty(name="Blend Strength", default=1.0)
    global_tint: bpy.props.FloatVectorProperty(name="Global Tint", subtype='COLOR', default=(1,1,1), min=0, max=1)
    uv_scale: bpy.props.FloatVectorProperty(name="UV Scale", size=2, default=(1.0, 1.0))


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

        # Zjednodušená ukázka vytvoření textur
        if shader_type in ['ShipStandard', 'Layered4']:
            albedo = nodes.new('ShaderNodeTexImage')
            albedo.label = "Albedo"
            links.new(albedo.outputs['Color'], bsdf.inputs['Base Color'])
            
            normal = nodes.new('ShaderNodeTexImage')
            normal.label = "Normal"
            normal_map = nodes.new('ShaderNodeNormalMap')
            links.new(normal.outputs['Color'], normal_map.inputs['Color'])
            links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
        
        if shader_type == 'ShipGlass':
            bsdf.inputs['Transmission'].default_value = 1.0
            # ... zde by byla složitější logika pro fresnel a opacity ...
            
        if shader_type == 'Layered4':
            vtx_color = nodes.new('ShaderNodeVertexColor')
            # ... zde by byla komplexní logika míchání 4 vrstev textur pomocí MixRGB a vtx_color ...
            self.report({'WARNING'}, "Layered4 node setup je komplexní a musí být implementován.")

        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
            
        self.report({'INFO'}, f"Materiál '{mat.name}' typu '{shader_type}' vytvořen a přiřazen.")
        return {'FINISHED'}