import bpy
from .shader_definitions import SHADER_DEFINITIONS
from .shader_materials import VMDL_OT_load_image

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

    def draw_texture_row(self, layout, tex_prop):
        shader_def = SHADER_DEFINITIONS.get(tex_prop.id_data.vmdl_shader.shader_name, {})
        tex_def = next((t for t in shader_def.get("textures", []) if t["name"] == tex_prop.name), None)
        label = tex_def["label"] if tex_def else tex_prop.name
        
        row = layout.row(align=True)
        row.prop(tex_prop, "image", text=label)
        op = row.operator("vmdl.load_image", text="", icon='FILEBROWSER')
        op.texture_name = tex_prop.name

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        mat = obj.active_material

        box = layout.box()
        box.label(text="Správa Materiálu", icon='MATERIAL')
        row = box.row(align=True)
        row.operator("vmdl.create_shader_material", text="Nový", icon='ADD')
        row.operator("vmdl.save_material_preset", text="Uložit Preset", icon='EXPORT')
        row.operator("vmdl.load_material_preset", text="Načíst Preset", icon='IMPORT')

        if mat and hasattr(mat, "vmdl_shader"):
            shader_props = mat.vmdl_shader
            
            main_box = layout.box()
            main_box.label(text=f"Materiál: {mat.name}", icon='NODE_MATERIAL')
            
            # Validace shaderu
            if shader_props.shader_name not in SHADER_DEFINITIONS:
                warning_box = main_box.box()
                warning_box.label(text="Neplatný shader!", icon='ERROR')
                warning_box.operator("vmdl.fix_invalid_shader", text="Opravit Shader")
                return

            main_box.prop(shader_props, "shader_name", text="")
            main_box.operator("vmdl.set_default_vertex_colors", text="Nastavit výchozí Vertex Colors", icon='BRUSH_DATA')
            
            if shader_props.textures:
                tex_box = main_box.box()
                tex_box.label(text="Textury", icon='TEXTURE_DATA')
                for tex in shader_props.textures:
                    self.draw_texture_row(tex_box, tex)
            
            if shader_props.parameters:
                param_box = main_box.box()
                param_box.label(text="Parametry", icon='PROPERTIES')
                for param in shader_props.parameters:
                    if param.name in ["Color1", "Color2"]:
                        row = param_box.row(align=True)
                        row.prop(param, "vector_value", text=param.name)
                        op_fill = row.operator("vmdl.fill_vertex_color", text="", icon='VPAINT_HLT')
                        op_fill.layer_name = param.name
                        
                        is_active_preview = (context.space_data.shading.type == 'SOLID' and 
                                             context.space_data.shading.color_type == 'VERTEX' and 
                                             obj.data.vertex_colors.active_render and
                                             obj.data.vertex_colors.active_render.name == param.name)
                        
                        op_view = row.operator("vmdl.toggle_vertex_color_view", text="", icon='HIDE_ON' if is_active_preview else 'HIDE_OFF')
                        op_view.layer_name = param.name
                    else:
                        row = param_box.row(align=True)
                        if param.type == "float":
                            row.prop(param, "float_value", text=param.name)
                        elif param.type == "vector4":
                            row.prop(param, "vector_value", text=param.name)
                        elif param.type == "bool":
                            row.prop(param, "bool_value", text=param.name)

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
        return obj and (obj.type == 'MESH' or obj.get("vmdl_type") in ["ROOT", "COLLIDER"])

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        box = layout.box()
        box.label(text="Collider Tools", icon='PHYSICS')
        op = box.operator("vmdl.generate_collider_mesh", text="Generate Collider", icon='MOD_BUILD')
        
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
        # Povolit export, pokud je vybrán jakýkoliv objekt z VMDL hierarchie
        obj = context.active_object
        if not obj:
            return False
        
        # Projít hierarchii nahoru a najít root
        if obj.get("vmdl_type") == "ROOT":
            return True
        node = obj
        while node.parent:
            node = node.parent
            if node.get("vmdl_type") == "ROOT":
                return True
        return False

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Export VMDL GLB", icon='EXPORT')
        box.operator("vmdl.export_glb", text="Export .glb", icon='PACKAGE') # ZMĚNA