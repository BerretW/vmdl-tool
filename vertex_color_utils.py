import bpy

class VMDL_OT_fill_vertex_color(bpy.types.Operator):
    """Aplikuje vybranou barvu a přepne do Vertex Paint módu."""
    bl_idname = "vmdl.fill_vertex_color"
    bl_label = "Fill With Vertex Color"
    bl_description = "Vyplní cílovou Vertex Color vrstvu a přepne do režimu malování"
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

        # Přepnutí do Object módu je bezpečnější pro modifikaci dat
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
        
        # Přepnutí do Vertex Paint módu a aktivace správné vrstvy
        mesh.vertex_colors.active_index = mesh.vertex_colors.find(self.layer_name)
        bpy.ops.object.mode_set(mode='VERTEX_PAINT')

        self.report({'INFO'}, f"Objekt vyplněn barvou ve vrstvě '{self.layer_name}'. Režim přepnut na Vertex Paint.")
        return {'FINISHED'}