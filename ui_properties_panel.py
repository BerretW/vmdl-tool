# ================================================
# FILE: ui_properties_panel.py
# ================================================
import bpy
from .shader_definitions import SHADER_DEFINITIONS

def vmdl_enum_items(self, context):
    return [('NONE', "Žádný", ""), ('ROOT', "Root", ""), ('MESH', "Mesh", ""), ('COLLIDER', "Collider", ""), ('MOUNTPOINT', "Mountpoint", "")]
def get_vmdl_enum(self): return self.get("vmdl_type", "NONE")
def set_vmdl_enum(self, value):
    if value == "NONE":
        if "vmdl_type" in self: del self["vmdl_type"]
    else: self["vmdl_type"] = value

class VMDL_PT_material_properties(bpy.types.Panel):
    bl_label = "VMDL Shader Properties"
    bl_idname = "MATERIAL_PT_vmdl_shader"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        return context.material and hasattr(context.material, "vmdl_shader")

    def draw_texture_row(self, layout, tex_prop):
        shader_def = SHADER_DEFINITIONS.get(tex_prop.id_data.vmdl_shader.shader_name, {})
        tex_def = next((t for t in shader_def.get("textures", []) if t["name"] == tex_prop.name), None)
        label = tex_def["label"] if tex_def else tex_prop.name
        split = layout.split(factor=0.35); split.label(text=label)
        row = split.row(align=True); row.prop(tex_prop, "image", text="")
        op_load = row.operator("vmdl.load_image", text="", icon='FILEBROWSER'); op_load.texture_name = tex_prop.name
        op_clear = row.operator("vmdl.clear_texture_slot", text="", icon='X'); op_clear.texture_name = tex_prop.name

    def draw(self, context):
        layout = self.layout
        mat = context.material
        shader_props = mat.vmdl_shader
        
        layout.prop(shader_props, "shader_name", text="Shader")
        
        if shader_props.shader_name not in SHADER_DEFINITIONS:
            box = layout.box(); box.alert = True; box.label(text="Neplatný VMDL shader!", icon='ERROR')
            box.operator("vmdl.fix_invalid_shader", text="Opravit na výchozí"); return

        # --- SEKCE PRO TINT PALETU ---
        tint_tex_prop = shader_props.textures.get("tintpalettetex")
        if tint_tex_prop and tint_tex_prop.image:
            tint_box = layout.box()
            tint_box.label(text="Tint Palette Control", icon='COLOR')
            
            row = tint_box.row(align=True)
            row.label(text="Preview:")
            
            # Zobrazí barvu z palety. Bohužel template_color_ramp zde nefunguje s texturou,
            # takže použijeme jednodušší náhled. V budoucnu by to šlo řešit přes custom widget.
            # Prozatím je důležitý slider a tlačítko.
            
            # Slider pro výběr barvy
            row.prop(shader_props, "tint_preview", slider=True, text="Select Tint")
            
            # Tlačítko pro aplikaci
            op = tint_box.operator("vmdl.apply_tint_to_object", text="Apply", icon='VPAINT_HLT')
            op.tint_value = shader_props.tint_preview

        # --- SEZNAM TEXTUR ---
        if shader_props.textures:
            tex_box = layout.box()
            header = tex_box.row(); header.label(text="Texture Parameters", icon='TEXTURE_DATA'); header.label(text=f"({len(shader_props.textures)})")
            for tex in shader_props.textures:
                self.draw_texture_row(tex_box, tex)
        
        # --- SEZNAM PARAMETRŮ ---
        if shader_props.parameters:
            param_box = layout.box()
            param_box.label(text="Shader Parameters", icon='PROPERTIES')
            for param in shader_props.parameters:
                row = param_box.row()
                if param.type == "float": row.prop(param, "float_value", text=param.name)
                elif param.type == "vector4": row.prop(param, "vector_value", text=param.name)
                elif param.type == "bool": row.prop(param, "bool_value", text=param.name)

class VMDL_PT_object_properties(bpy.types.Panel):
    bl_label = "VMDL Nastavení objektu"; bl_idname = "OBJECT_PT_vmdl_properties"
    bl_space_type = 'PROPERTIES'; bl_region_type = 'WINDOW'; bl_context = "object"
    @classmethod
    def poll(cls, context): return context.object is not None
    def draw(self, context):
        layout = self.layout; obj = context.object
        layout.prop(obj, 'vmdl_enum_type', text="VMDL Typ")
        vmdl_type = obj.vmdl_enum_type
        if vmdl_type == "COLLIDER":
            box = layout.box(); box.label(text="Collider Vlastnosti")
            box.prop(obj.vmdl_collider, "collider_type")
            box.operator("vmdl.toggle_collider_shading", text="Toggle Preview", icon='SHADING_RENDERED')
        elif vmdl_type == "MOUNTPOINT":
            box = layout.box(); box.label(text="Mountpoint Vlastnosti")
            box.prop(obj.vmdl_mountpoint, "forward_vector"); box.prop(obj.vmdl_mountpoint, "up_vector")