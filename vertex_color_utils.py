# ================================================
# Vložte do souboru: vertex_color_utils.py (OPRAVENÁ VERZE)
# ================================================
import bpy
import bmesh

DEFAULT_COLOR_1 = (0.0, 0.8, 1.0, 1.0)
DEFAULT_COLOR_2 = (0.0, 0.0, 0.0, 1.0)

class VMDLVertexColorToolsProperties(bpy.types.PropertyGroup):
    # Nástroje pro malování po výběru
    target_layer: bpy.props.EnumProperty(
        name="Cílová vrstva",
        description="Vyberte, kterou Vertex Color vrstvu chcete modifikovat",
        items=[('Color1', "Color1", "Hlavní PBR data (Tint, Roughness, Normal)"),
               ('Color2', "Color2", "Data pro míchání vrstev (Blend)")]
    )
    source_color: bpy.props.FloatVectorProperty(
        name="Zdrojová barva", subtype='COLOR', size=4, min=0.0, max=1.0, default=(0.0, 0.8, 1.0, 1.0)
    )
    mask_r: bpy.props.BoolProperty(name="R", default=True, description="Aplikovat červený kanál")
    mask_g: bpy.props.BoolProperty(name="G", default=True, description="Aplikovat zelený kanál")
    mask_b: bpy.props.BoolProperty(name="B", default=True, description="Aplikovat modrý kanál")
    mask_a: bpy.props.BoolProperty(name="A", default=True, description="Aplikovat alfa kanál")
    
    # Vlastnosti pro globální nastavení
    global_roughness: bpy.props.FloatProperty(
        name="Global Roughness",
        description="Hodnota, která se zapíše do G kanálu Color1",
        min=0.0, max=1.0, default=0.8
    )
    global_normal_strength: bpy.props.FloatProperty(
        name="Global Normal Strength",
        description="Hodnota, která se zapíše do B kanálu Color1",
        min=0.0, max=1.0, default=1.0
    )


# Operátor pro globální aplikaci
class VMDL_OT_apply_global_vertex_data(bpy.types.Operator):
    bl_idname = "vmdl.apply_global_vertex_data"
    bl_label = "Apply Global Values to Color1"
    bl_description = "Nastaví hodnoty Roughness (G) a Normal (B) na celém objektu"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        tools = context.scene.vmdl_vc_tools
        
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        if "Color1" not in mesh.vertex_colors:
            mesh.vertex_colors.new(name="Color1")
            self.report({'INFO'}, "Vytvořena chybějící vrstva 'Color1'.")
        
        color_layer = mesh.vertex_colors["Color1"]
        
        new_g = tools.global_roughness
        new_b = tools.global_normal_strength
        
        # Projdeme všechny loopy a upravíme jen G a B kanály
        for loop_color in color_layer.data:
            current_color = loop_color.color
            
            # === ZDE JE OPRAVA: POUŽÍVÁME INDEXY [0] A [3] MÍSTO .r A .a ===
            loop_color.color = (current_color[0], new_g, new_b, current_color[3])
            
        mesh.update()
        self.report({'INFO'}, f"Globální hodnoty pro Roughness a Normal aplikovány.")
        return {'FINISHED'}


# --- Zbytek souboru zůstává stejný ---
class VMDL_OT_set_selection_vertex_color(bpy.types.Operator):
    bl_idname = "vmdl.set_selection_vertex_color"
    bl_label = "Apply to Selection"
    bl_description = "Aplikuje barvu a masku kanálů na vybrané plochy"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.active_object and
                context.active_object.type == 'MESH' and
                context.mode == 'EDIT_MESH')
                
    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        tools = context.scene.vmdl_vc_tools
        layer_name = tools.target_layer
        
        bm = bmesh.from_edit_mesh(mesh)
        color_layer = bm.loops.layers.color.get(layer_name)
        if color_layer is None:
            color_layer = bm.loops.layers.color.new(layer_name)
            self.report({'INFO'}, f"Vytvořena chybějící vrstva '{layer_name}'.")

        source_color = tools.source_color
        selected_loops = [loop for face in bm.faces if face.select for loop in face.loops]
        
        if not selected_loops:
            self.report({'WARNING'}, "Nejsou vybrány žádné plochy (faces).")
            return {'CANCELLED'}
            
        for loop in selected_loops:
            current_color = loop[color_layer]
            new_color = (
                source_color[0] if tools.mask_r else current_color[0],
                source_color[1] if tools.mask_g else current_color[1],
                source_color[2] if tools.mask_b else current_color[2],
                source_color[3] if tools.mask_a else current_color[3],
            )
            loop[color_layer] = new_color
            
        bmesh.update_edit_mesh(mesh)
        self.report({'INFO'}, f"Barva aplikována na výběr ve vrstvě '{layer_name}'.")
        return {'FINISHED'}

class VMDL_OT_toggle_vertex_color_view(bpy.types.Operator):
    bl_idname = "vmdl.toggle_vertex_color_view"
    bl_label = "Toggle Vertex Color Preview"
    bl_description = "Zobrazí tuto vertex color vrstvu ve viewportu"
    layer_name: bpy.props.StringProperty()
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
        
    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        space = context.space_data
        
        if self.layer_name not in mesh.vertex_colors:
            self.report({'WARNING'}, f"Vrstva '{self.layer_name}' na objektu neexistuje.")
            return {'CANCELLED'}
            
        active_layer = mesh.vertex_colors.active
        is_already_active_view = (space.shading.type == 'SOLID' and space.shading.color_type == 'VERTEX' and active_layer and active_layer.name == self.layer_name)
        if not is_already_active_view:
            space.shading.type = 'SOLID'
            space.shading.light = 'FLAT'
            space.shading.color_type = 'VERTEX'
            try:
                mesh.vertex_colors.active_index = mesh.vertex_colors.find(self.layer_name)
            except ValueError:
                return {'CANCELLED'}
        else:
            space.shading.color_type = 'MATERIAL'
        return {'FINISHED'}

class VMDL_OT_fill_vertex_color(bpy.types.Operator):
    bl_idname = "vmdl.fill_vertex_color"
    bl_label = "Fill Entire Object"
    bl_description = "Vyplní cílovou Vertex Color vrstvu barvou nastavenou v UI"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
        
    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        tools = context.scene.vmdl_vc_tools
        layer_name = tools.target_layer
        
        if context.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        if layer_name not in mesh.vertex_colors: mesh.vertex_colors.new(name=layer_name)
        color_layer = mesh.vertex_colors[layer_name]
        color_to_apply = tools.source_color
        for loop in mesh.loops: color_layer.data[loop.index].color = color_to_apply
        mesh.update()
        self.report({'INFO'}, f"Celý objekt vyplněn barvou ve vrstvě '{layer_name}'.")
        return {'FINISHED'}

class VMDL_OT_set_default_vertex_colors(bpy.types.Operator):
    bl_idname = "vmdl.set_default_vertex_colors"
    bl_label = "Set Default Vertex Colors"
    bl_description = "Vyplní Color1 a Color2 standardními hodnotami pro PBR workflow"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
        
    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        if context.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        if "Color1" not in mesh.vertex_colors: mesh.vertex_colors.new(name="Color1")
        color_layer_1 = mesh.vertex_colors["Color1"]
        for loop in mesh.loops: color_layer_1.data[loop.index].color = DEFAULT_COLOR_1
        if "Color2" not in mesh.vertex_colors: mesh.vertex_colors.new(name="Color2")
        color_layer_2 = mesh.vertex_colors["Color2"]
        for loop in mesh.loops: color_layer_2.data[loop.index].color = DEFAULT_COLOR_2
        mesh.update()
        self.report({'INFO'}, "Vertex barvy nastaveny na výchozí PBR hodnoty.")
        return {'FINISHED'}