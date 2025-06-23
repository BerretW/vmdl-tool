# ui_properties_panel.py

import bpy

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

    def draw_color_row(self, layout, props, prop_name, layer_name):
        """Pomocná funkce pro vykreslení řádku s barvou a tlačítkem."""
        row = layout.row(align=True)
        row.prop(props, prop_name)
        op = row.operator("vmdl.fill_vertex_color", text="", icon='VPAINT_HLT')
        op.layer_name = layer_name

    def draw(self, context):
        layout = self.layout
        mat = context.material
        shader = mat.vmdl_shader

        layout.prop(shader, "shader_type", text="Shader")
        
        # Společné vlastnosti
        if shader.shader_type != 'ShipGlass':
            col = layout.column(align=True)
            self.draw_color_row(col, shader, "color1", "Color1")
            self.draw_color_row(col, shader, "color2", "Color2")


        # Specifické vlastnosti
        if shader.shader_type == 'ShipStandard':
            col = layout.column(align=True)
            col.prop(shader, "smoothness")
            col.prop(shader, "tint_color")
            col.separator()
            self.draw_texture_slot(col, shader, "albedo_image", "vmdl.load_image_albedo")
            self.draw_texture_slot(col, shader, "normal_image", "vmdl.load_image_normal")
            self.draw_texture_slot(col, shader, "roughness_image", "vmdl.load_image_roughness")
            self.draw_texture_slot(col, shader, "metallic_image", "vmdl.load_image_metallic")

        elif shader.shader_type == 'Standard_dirt':
            col = layout.column(align=True)
            self.draw_texture_slot(col, shader, "albedo_image", "vmdl.load_image_albedo")
            self.draw_texture_slot(col, shader, "normal_image", "vmdl.load_image_normal")
            self.draw_texture_slot(col, shader, "dirt_image", "vmdl.load_image_dirt")

        elif shader.shader_type == 'ShipGlass':
            col = layout.column(align=True)
            col.prop(shader, "opacity")
            col.prop(shader, "fresnel_power")
            col.prop(shader, "reflectivity")
            col.separator()
            self.draw_texture_slot(col, shader, "opacity_image", "vmdl.load_image_opacity")

        elif shader.shader_type == 'Layered4':
            col = layout.column(align=True)
            col.prop(shader, "blend_strength")
            col.prop(shader, "global_tint")
            col.prop(shader, "uv_scale")
            col.separator()
            self.draw_texture_slot(col, shader, "layer1_image", "vmdl.load_image_layer1")
            self.draw_texture_slot(col, shader, "layer2_image", "vmdl.load_image_layer2")
            self.draw_texture_slot(col, shader, "layer3_image", "vmdl.load_image_layer3")
            self.draw_texture_slot(col, shader, "layer4_image", "vmdl.load_image_layer4")

    def draw_texture_slot(self, layout, props, prop_name, operator_id):
        row = layout.row(align=True)
        row.prop(props, prop_name)
        row.operator(operator_id, text="", icon='FILEBROWSER')


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