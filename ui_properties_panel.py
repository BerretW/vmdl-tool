import bpy
from .shader_definitions import SHADER_DEFINITIONS

def vmdl_enum_items(self, context):
    return [
        ('NONE', "Žádný", "Objekt není součástí VMDL hierarchie"),
        ('ROOT', "Root", "Kořenový objekt VMDL modelu"),
        ('MESH', "Mesh", "Viditelný model"),
        ('COLLIDER', "Collider", "Fyzikální kolizní model"),
        ('MOUNTPOINT', "Mountpoint", "Bod pro připojení (zbraně, efekty)")
    ]

def get_vmdl_enum(self):
    return self.get("vmdl_type", "NONE")

def set_vmdl_enum(self, value):
    if value == "NONE":
        if "vmdl_type" in self:
            del self["vmdl_type"]
    else:
        self["vmdl_type"] = value

class VMDL_PT_material_properties(bpy.types.Panel):
    bl_label = "VMDL Shader Properties"
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
        shader_props = mat.vmdl_shader
        
        layout.prop(shader_props, "shader_name", text="Shader")
        
        if shader_props.textures:
            tex_box = layout.box()
            tex_box.label(text="Textury", icon='TEXTURE_DATA')
            shader_def = SHADER_DEFINITIONS.get(shader_props.shader_name, {})
            tex_defs = {t["name"]: t for t in shader_def.get("textures", [])}
            for tex in shader_props.textures:
                tex_def = tex_defs.get(tex.name)
                label = tex_def["label"] if tex_def else tex.name
                tex_box.prop(tex, "image", text=label)
        
        if shader_props.parameters:
            param_box = layout.box()
            param_box.label(text="Parametry", icon='PROPERTIES')
            for param in shader_props.parameters:
                if param.name in ["Color1", "Color2"]:
                    row = param_box.row(align=True)
                    row.prop(param, "vector_value", text=param.name)
                    op = row.operator("vmdl.fill_vertex_color", text="", icon='VPAINT_HLT')
                    op.layer_name = param.name
                else:
                    row = param_box.row(align=True)
                    if param.type == "float":
                        row.prop(param, "float_value", text=param.name)
                    elif param.type == "vector4":
                        row.prop(param, "vector_value", text=param.name)
                    elif param.type == "bool":
                        row.prop(param, "bool_value", text=param.name)

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

        vmdl_type = obj.get("vmdl_type")
        if vmdl_type == "COLLIDER":
            box = layout.box()
            box.label(text="Collider Vlastnosti")
            box.prop(obj.vmdl_collider, "collider_type")
        elif vmdl_type == "MOUNTPOINT":
            box = layout.box()
            box.label(text="Mountpoint Vlastnosti")
            box.prop(obj.vmdl_mountpoint, "forward_vector")
            box.prop(obj.vmdl_mountpoint, "up_vector")