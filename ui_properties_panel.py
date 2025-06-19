# ui_properties_panel.py

import bpy

def vmdl_enum_items(self, context):
    return [
        ('NONE', "Žádný", ""),
        ('ROOT', "Root", ""),
        ('MESH', "Model (.model)", ""),
        ('COLLIDER', "Collider (.col)", ""),
        ('MOUNTPOINT', "Mountpoint", "")
    ]

def get_vmdl_enum(self):
    return self.get("vmdl_type", "NONE")

def set_vmdl_enum(self, value):
    self["vmdl_type"] = value

class VMDL_PT_material_properties(bpy.types.Panel):
    bl_label = "VMDL Shader"
    bl_idname = "MATERIAL_PT_vmdl_shader"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        mat = context.material
        return mat and hasattr(mat, "vmdl_shader")

    def draw(self, context):
        layout = self.layout
        mat = context.material
        shader = mat.vmdl_shader

        layout.prop(shader, "shader_type", text="Shader")

        if shader.shader_type == 'ShipStandard':
            layout.prop(shader, "smoothness")
            layout.prop(shader, "tint_color")
            layout.prop(shader, "albedo_texture")
            layout.prop(shader, "normal_texture")
            layout.prop(shader, "roughness_texture")
            layout.prop(shader, "metallic_texture")

        elif shader.shader_type == 'ShipGlass':
            layout.prop(shader, "opacity")
            layout.prop(shader, "fresnel_power")
            layout.prop(shader, "reflectivity")
            layout.prop(shader, "opacity_texture")

        elif shader.shader_type == 'Layered4':
            layout.prop(shader, "blend_strength")
            layout.prop(shader, "global_tint")
            layout.prop(shader, "uv_scale")
            layout.prop(shader, "layer1_texture")
            layout.prop(shader, "layer2_texture")
            layout.prop(shader, "layer3_texture")
            layout.prop(shader, "layer4_texture")

class VMDL_PT_object_properties(bpy.types.Panel):
    bl_label = "VMDL Nastavení objektu"
    bl_idname = "OBJECT_PT_vmdl_properties"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        obj = context.object

        layout.prop(obj, 'vmdl_enum_type', text="VMDL Typ")

        if obj.vmdl_enum_type == "COLLIDER":
            layout.prop(obj.vmdl_collider, "collider_type")
        elif obj.vmdl_enum_type == "MOUNTPOINT":
            layout.prop(obj.vmdl_mountpoint, "forward_vector")
            layout.prop(obj.vmdl_mountpoint, "up_vector")
