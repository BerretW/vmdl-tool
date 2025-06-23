import bpy

class VMDL_OT_fill_vertex_color(bpy.types.Operator):
    """Aplikuje vybranou barvu z VMDL properties na celou Vertex Color vrstvu"""
    bl_idname = "vmdl.fill_vertex_color"
    bl_label = "Fill With Vertex Color"
    bl_description = "Vyplní aktivní Vertex Color vrstvu barvou nastavenou v UI"
    bl_options = {'REGISTER', 'UNDO'}

    layer_name: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not (obj and obj.type == 'MESH' and obj.active_material):
            return False
        
        mat = obj.active_material
        if not hasattr(mat, 'vmdl_shader'):
            return False
            
        return True

    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        
        if not self.layer_name:
            self.report({'ERROR'}, "Nebyla specifikována cílová vrstva (např. 'Color1').")
            return {'CANCELLED'}

        # Zkontrolujeme, zda vrstva existuje, pokud ne, vytvoříme ji
        if self.layer_name not in mesh.vertex_colors:
            mesh.vertex_colors.new(name=self.layer_name)
            self.report({'INFO'}, f"Vytvořena chybějící Vertex Color vrstva: {self.layer_name}")

        color_layer = mesh.vertex_colors[self.layer_name]

        # Získáme barvu z VMDL parametrů materiálu
        shader_props = obj.active_material.vmdl_shader
        param = shader_props.parameters.get(self.layer_name)
        
        if not param or param.type != "vector4":
            self.report({'ERROR'}, f"Parametr '{self.layer_name}' nebyl nalezen nebo není typu Vector4.")
            return {'CANCELLED'}
            
        color_to_apply = param.vector_value

        # Aplikujeme barvu na všechny loopy meshe
        # Přepneme do Object módu pro jistotu, že můžeme modifikovat data
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        if mesh.loops:
            color_layer.data.foreach_set("color", [c for c in color_to_apply for _ in range(len(mesh.loops))])
        
        mesh.update()

        self.report({'INFO'}, f"Objekt '{obj.name}' byl vyplněn barvou ve vrstvě '{self.layer_name}'.")
        return {'FINISHED'}