# ui_panel.py

import bpy
from .constants import SHADER_TYPES

class VMDL_PT_main_panel(bpy.types.Panel):
    bl_label = "VMDL Tools"
    bl_idname = "VMDL_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VMDL'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        box = layout.box()
        box.label(text="VMDL Workflow", icon='OBJECT_DATA')
        box.operator("vmdl.create_vmdl_object", text="Create VMDL Object", icon='CUBE')

        if obj and obj.get("vmdl_type") == "ROOT":
            box.label(text=f"Aktivní VMDL: {obj.name}", icon='OUTLINER_OB_EMPTY')
        elif not obj:
            box.label(text="Vyberte objekt pro start.", icon='INFO')


class VMDL_PT_material_panel(bpy.types.Panel):
    bl_label = "Shader & Materiály"
    bl_idname = "VMDL_PT_material_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VMDL'
    bl_parent_id = 'VMDL_PT_main_panel'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def draw_color_row(self, layout, props, prop_name, layer_name):
        """Pomocná funkce pro vykreslení řádku s barvou a tlačítkem."""
        row = layout.row(align=True)
        row.prop(props, prop_name)
        op = row.operator("vmdl.fill_vertex_color", text="", icon='VPAINT_HLT')
        op.layer_name = layer_name

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        mat = obj.active_material

        box = layout.box()
        box.label(text="Vytvořit materiál", icon='MATERIAL')

        row = box.row(align=True)
        row.prop(context.scene.vmdl_export, "shader_type_to_create", text="")
        row.operator("vmdl.create_shader_material", text="Create", icon='ADD')

        if mat and hasattr(mat, "vmdl_shader"):
            box = layout.box()
            shader_props = mat.vmdl_shader
            box.label(text=f"Nastavení: {mat.name} ({shader_props.shader_type})", icon='NODE_MATERIAL')
            
            box.prop(shader_props, "shader_type", text="Změnit Shader")

            # Společné vlastnosti
            if shader_props.shader_type != 'ShipGlass':
                col = box.column(align=True)
                self.draw_color_row(col, shader_props, "color1", "Color1")
                self.draw_color_row(col, shader_props, "color2", "Color2")


            # Specifické vlastnosti
            if shader_props.shader_type == 'ShipStandard':
                col = box.column(align=True)
                col.prop(shader_props, "smoothness")
                col.prop(shader_props, "tint_color")
                col.separator()
                col.prop(shader_props, "albedo_image")
                col.prop(shader_props, "normal_image")
                col.prop(shader_props, "roughness_image")
                col.prop(shader_props, "metallic_image")

            elif shader_props.shader_type == 'Standard_dirt':
                col = box.column(align=True)
                col.prop(shader_props, "albedo_image")
                col.prop(shader_props, "normal_image")
                col.prop(shader_props, "dirt_image")

            elif shader_props.shader_type == 'ShipGlass':
                col = box.column(align=True)
                col.prop(shader_props, "opacity")
                col.prop(shader_props, "fresnel_power")
                col.prop(shader_props, "reflectivity")
                col.separator()
                col.prop(shader_props, "opacity_image")

            elif shader_props.shader_type == 'Layered4':
                col = box.column(align=True)
                col.prop(shader_props, "blend_strength")
                col.prop(shader_props, "global_tint")
                col.prop(shader_props, "uv_scale")
                col.separator()
                col.prop(shader_props, "layer1_image")
                col.prop(shader_props, "layer2_image")
                col.prop(shader_props, "layer3_image")
                col.prop(shader_props, "layer4_image")


class VMDL_PT_collider_panel(bpy.types.Panel):
    bl_label = "Colliders"
    bl_idname = "VMDL_PT_collider_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VMDL'
    bl_parent_id = 'VMDL_PT_main_panel'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and (obj.type == 'MESH' or obj.get("vmdl_type") == "ROOT" or obj.get("vmdl_type") == "COLLIDER")

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        box = layout.box()
        box.label(text="Collider Tools", icon='PHYSICS')
        box.operator("vmdl.generate_collider_mesh", text="Generate Collider", icon='MOD_BUILD')

        if obj and obj.get("vmdl_type") == "COLLIDER":
            col_props = obj.vmdl_collider
            box.prop(col_props, "collider_type", text="Typ")
            box.operator("vmdl.toggle_collider_shading", text="Toggle Preview Shading", icon='SHADING_RENDERED')


class VMDL_PT_mountpoint_panel(bpy.types.Panel):
    bl_label = "Mountpoints"
    bl_idname = "VMDL_PT_mountpoint_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VMDL'
    bl_parent_id = 'VMDL_PT_main_panel'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Mountpoint Tools", icon='EMPTY_ARROWS')
        box.operator("vmdl.create_mountpoint", text="Create from Selection", icon='ADD')

        obj = context.active_object
        if obj and obj.get("vmdl_type") == "MOUNTPOINT":
            box.label(text=f"Editing: {obj.name}")
            mount_props = obj.vmdl_mountpoint
            box.prop(mount_props, "forward_vector", text="Forward")
            box.prop(mount_props, "up_vector", text="Up")


class VMDL_PT_export_panel(bpy.types.Panel):
    bl_label = "Export"
    bl_idname = "VMDL_PT_export_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VMDL'
    bl_parent_id = 'VMDL_PT_main_panel'

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.get("vmdl_type") == "ROOT"

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Export VMDL Package", icon='EXPORT')
        box.operator("vmdl.export_package", text="Export .vmdl.pkg", icon='PACKAGE')