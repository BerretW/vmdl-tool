# ================================================
# FILE: ui_panel.py (opraveno)
# ================================================
import bpy
from .shader_definitions import SHADER_DEFINITIONS

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
        if obj and obj.vmdl_enum_type == "ROOT":
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

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        
        # --- SEKCE PRO VYTVOŘENÍ NOVÉHO MATERIÁLU ---
        create_box = layout.box()
        create_box.label(text="Vytvořit a přiřadit materiál", icon='ADD')
        
        # Seznam shaderů jako tlačítka pro rychlé vytvoření
        shader_keys = sorted(SHADER_DEFINITIONS.keys())
        if not shader_keys:
            create_box.label(text="Žádné shadery nejsou definovány!", icon='ERROR')
        else:
            col = create_box.column(align=True)
            for shader_name in shader_keys:
                op = col.operator("vmdl.create_shader_material", text=shader_name)
                op.shader_name_prop = shader_name

        # --- SEKCE PRO NÁSTROJE ---
        tools_box = layout.box()
        tools_box.label(text="Nástroje materiálu", icon='TOOL_SETTINGS')
        
        row = tools_box.row(align=True)
        row.operator("vmdl.save_material_preset", text="Uložit Preset", icon='EXPORT')
        row.operator("vmdl.load_material_preset", text="Načíst Preset", icon='IMPORT')
        
        tools_box.operator("vmdl.set_default_vertex_colors", text="Nastavit výchozí Vertex barvy", icon='BRUSH_DATA')

        # Upozornění na neplatný shader
        mat = obj.active_material
        if mat and hasattr(mat, "vmdl_shader") and mat.vmdl_shader.shader_name not in SHADER_DEFINITIONS:
             warning_box = layout.box()
             warning_box.alert = True
             warning_box.label(text="Neplatný VMDL shader!", icon='ERROR')
             warning_box.operator("vmdl.fix_invalid_shader", text="Opravit na výchozí")


class VMDL_PT_vertex_color_panel(bpy.types.Panel):
    bl_label = "Vertex Color Editor"
    bl_idname = "VMDL_PT_vertex_color_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'VMDL'
    bl_parent_id = 'VMDL_PT_main_panel'
    bl_options = {'DEFAULT_CLOSED'}
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
    def draw(self, context):
        layout = self.layout
        tools = context.scene.vmdl_vc_tools
        obj = context.active_object
        box = layout.box()
        row = box.row(align=True)
        row.prop(tools, "target_layer", text="")
        op_view = row.operator("vmdl.toggle_vertex_color_view", text="", icon='HIDE_OFF')
        op_view.layer_name = tools.target_layer
        active_vc_layer = obj.data.vertex_colors.active
        if (context.space_data.shading.type == 'SOLID' and 
            context.space_data.shading.color_type == 'VERTEX' and
            active_vc_layer and active_vc_layer.name == tools.target_layer):
            op_view.icon = 'HIDE_ON'
        box.prop(tools, "source_color", text="")
        sub = box.column(align=True)
        sub.label(text="Aktivní kanály (maska):")
        row = sub.row(align=True)
        row.prop(tools, "mask_r"); row.prop(tools, "mask_g"); row.prop(tools, "mask_b"); row.prop(tools, "mask_a")
        layout.separator()
        col = layout.column(align=True)
        # ZDE JE PROVEDENÁ OPRAVA
        col.operator("vmdl.set_selection_vertex_color", icon='VPAINT_HLT')
        col.operator("vmdl.fill_vertex_color", text="Fill Entire Layer", icon='FILE_BLANK')
        if context.mode != 'EDIT_MESH':
            info_box = layout.box()
            info_box.alert = True
            info_box.label(text="Pro aplikaci na výběr přepněte do Edit Módu", icon='INFO')

# ... (ostatní panely zůstávají stejné) ...
class VMDL_PT_collider_panel(bpy.types.Panel):
    bl_label = "Colliders"
    bl_idname = "VMDL_PT_collider_panel"
    bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = 'VMDL'; bl_parent_id = 'VMDL_PT_main_panel'; bl_options = {'DEFAULT_CLOSED'}
    @classmethod
    def poll(cls, context): obj = context.active_object; return obj and (obj.type == 'MESH' or obj.vmdl_enum_type in ["ROOT", "COLLIDER"])
    def draw(self, context):
        layout = self.layout; obj = context.active_object; box = layout.box()
        box.label(text="Collider Tools", icon='PHYSICS')
        box.operator("vmdl.generate_collider_mesh", text="Generate Collider", icon='MOD_BUILD')
        if obj and obj.vmdl_enum_type == "COLLIDER":
            col_props = obj.vmdl_collider
            box.prop(col_props, "collider_type", text="Typ")
            box.operator("vmdl.toggle_collider_shading", text="Toggle Preview Shading", icon='SHADING_RENDERED')

class VMDL_PT_mountpoint_panel(bpy.types.Panel):
    bl_label = "Mountpoints"; bl_idname = "VMDL_PT_mountpoint_panel"
    bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = 'VMDL'; bl_parent_id = 'VMDL_PT_main_panel'; bl_options = {'DEFAULT_CLOSED'}
    @classmethod
    def poll(cls, context): return context.active_object is not None
    def draw(self, context):
        layout = self.layout; box = layout.box()
        box.label(text="Mountpoint Tools", icon='EMPTY_ARROWS')
        box.operator("vmdl.create_mountpoint", text="Create from Selection", icon='ADD')
        obj = context.active_object
        if obj and obj.vmdl_enum_type == "MOUNTPOINT":
            box.label(text=f"Editing: {obj.name}")
            mount_props = obj.vmdl_mountpoint
            box.prop(mount_props, "forward_vector", text="Forward")
            box.prop(mount_props, "up_vector", text="Up")

class VMDL_PT_export_panel(bpy.types.Panel):
    bl_label = "Export & Tools"; bl_idname = "VMDL_PT_export_panel"
    bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = 'VMDL'; bl_parent_id = 'VMDL_PT_main_panel'
    @classmethod
    def poll(cls, context):
        for obj in context.scene.objects:
            if obj.vmdl_enum_type == "ROOT": return True
        return False
    def draw(self, context):
        layout = self.layout; export_props = context.scene.vmdl_export; box = layout.box()
        box.label(text="Export VMDL Archive", icon='EXPORT')
        box.operator("vmdl.export_vmdl", text="Export .vmdl", icon='PACKAGE')
        box.prop(export_props, "debug_show_extras")
        tools_box = layout.box()
        tools_box.label(text="Texture Tools", icon='TEXTURE')
        tools_box.operator("vmdl.extract_textures", text="Extract Textures", icon='PACKAGE')