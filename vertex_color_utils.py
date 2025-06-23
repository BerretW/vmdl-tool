import bpy

# Standardní hodnoty pro rychlé nastavení
DEFAULT_COLOR_1 = (0.0, 0.8, 1.0, 1.0) # R:Tint (0=začátek palety), G:Roughness, B:Normal, A:Saturation
DEFAULT_COLOR_2 = (0.0, 0.0, 0.0, 1.0) # R,G,B:Blend -> výchozí je 0 (základní vrstva)

class VMDL_OT_toggle_vertex_color_view(bpy.types.Operator):
    """Přepne zobrazení viewportu pro náhled vybrané vertex color vrstvy."""
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
        
        # Přepnutí do Solid view s Vertex barvami
        if space.shading.type != 'SOLID' or space.shading.color_type != 'VERTEX' or mesh.vertex_colors.active_render.name != self.layer_name:
            space.shading.type = 'SOLID'
            space.shading.light = 'FLAT'
            space.shading.color_type = 'VERTEX'
            mesh.vertex_colors.active_render = mesh.vertex_colors[self.layer_name]
        else: # Pokud už jsme v tomto módu, přepneme zpět na materiál
            space.shading.color_type = 'MATERIAL'
            mesh.vertex_colors.active_render = None

        return {'FINISHED'}

class VMDL_OT_fill_vertex_color(bpy.types.Operator):
    """Aplikuje vybranou barvu a přepne do Vertex Paint módu."""
    bl_idname = "vmdl.fill_vertex_color"
    bl_label = "Fill With Vertex Color"
    bl_description = "Vyplní cílovou Vertex Color vrstvu barvou nastavenou v UI a přepne do režimu malování"
    bl_options = {'REGISTER', 'UNDO'}

    layer_name: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.active_material and hasattr(obj.active_material, 'vmdl_shader')

    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        
        if not self.layer_name:
            self.report({'ERROR'}, "Nebyla specifikována cílová vrstva.")
            return {'CANCELLED'}

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        if self.layer_name not in mesh.vertex_colors:
            mesh.vertex_colors.new(name=self.layer_name)
            self.report({'INFO'}, f"Vytvořena chybějící Vertex Color vrstva: {self.layer_name}")

        color_layer = mesh.vertex_colors[self.layer_name]
        
        shader_props = obj.active_material.vmdl_shader
        param = shader_props.parameters.get(self.layer_name)
        
        if not param or param.type != "vector4":
            self.report({'ERROR'}, f"Parametr '{self.layer_name}' v shaderu nenalezen nebo není typu Vector4.")
            return {'CANCELLED'}
            
        color_to_apply = param.vector_value

        for loop in mesh.loops:
            color_layer.data[loop.index].color = color_to_apply

        mesh.update()
        
        mesh.vertex_colors.active_index = mesh.vertex_colors.find(self.layer_name)
        bpy.ops.object.mode_set(mode='VERTEX_PAINT')

        self.report({'INFO'}, f"Objekt vyplněn barvou ve vrstvě '{self.layer_name}'. Režim přepnut na Vertex Paint.")
        return {'FINISHED'}

class VMDL_OT_set_default_vertex_colors(bpy.types.Operator):
    """Nastaví Color1 a Color2 na standardní výchozí hodnoty pro PBR."""
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

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Nastavení Color1
        if "Color1" not in mesh.vertex_colors:
            mesh.vertex_colors.new(name="Color1")
        color_layer_1 = mesh.vertex_colors["Color1"]
        for loop in mesh.loops:
            color_layer_1.data[loop.index].color = DEFAULT_COLOR_1

        # Nastavení Color2
        if "Color2" not in mesh.vertex_colors:
            mesh.vertex_colors.new(name="Color2")
        color_layer_2 = mesh.vertex_colors["Color2"]
        for loop in mesh.loops:
            color_layer_2.data[loop.index].color = DEFAULT_COLOR_2

        mesh.update()
        self.report({'INFO'}, "Vertex barvy nastaveny na výchozí PBR hodnoty.")
        return {'FINISHED'}