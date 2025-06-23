import bpy

class VMDL_OT_fill_vertex_color(bpy.types.Operator):
    """Aplikuje vybranou barvu z VMDL properties na celou Vertex Color vrstvu"""
    bl_idname = "vmdl.fill_vertex_color"
    bl_label = "Fill With Vertex Color"
    bl_description = "Vyplní cílovou Vertex Color vrstvu barvou nastavenou v UI"
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

        # Přepnutí do Object módu je bezpečnější pro modifikaci dat
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Spolehlivá metoda pomocí cyklu
        for loop in mesh.loops:
            color_layer.data[loop.index].color = color_to_apply

        mesh.update() # Ujistíme se, že změny jsou viditelné
        self.report({'INFO'}, f"Objekt '{obj.name}' vyplněn barvou ve vrstvě '{self.layer_name}'.")
        return {'FINISHED'}