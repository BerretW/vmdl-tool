import bpy

class VMDL_OT_create_vmdl_object(bpy.types.Operator):
    bl_idname = "vmdl.create_vmdl_object"
    bl_label = "Create VMDL Object"
    bl_description = "Vytvoří VMDL hierarchii s modelem a colliderem z aktivního objektu"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        # OPRAVA: Používáme vmdl_enum_type pro zjištění, zda objekt již není součástí hierarchie
        return obj and obj.type == 'MESH' and obj.vmdl_enum_type == 'NONE'

    def execute(self, context):
        source_obj = context.active_object

        # 1. Vytvoř root objekt (Empty)
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=source_obj.location)
        root = context.active_object
        root.name = source_obj.name + "_VMDL"
        root.vmdl_enum_type = "ROOT"

        # Přenastavíme source_obj na VMDL MESH a připarentujeme
        original_name = source_obj.name
        source_obj.name = original_name + ".model"
        source_obj.parent = root
        source_obj.location = (0, 0, 0)
        source_obj.vmdl_enum_type = "MESH"

        # Duplikuj .model → .col
        bpy.ops.object.select_all(action='DESELECT')
        source_obj.select_set(True)
        context.view_layer.objects.active = source_obj
        bpy.ops.object.duplicate()
        col = context.selected_objects[0]
        col.name = original_name + ".col"
        col.parent = root
        col.location = (0, 0, 0)
        col.vmdl_enum_type = "COLLIDER"
        
        # Vytvoříme výchozí Vertex Color vrstvy na obou meshech
        for obj in [source_obj, col]:
            if 'Color1' not in obj.data.vertex_colors:
                obj.data.vertex_colors.new(name="Color1")
            if 'Color2' not in obj.data.vertex_colors:
                obj.data.vertex_colors.new(name="Color2")

        bpy.ops.object.select_all(action='DESELECT')
        root.select_set(True)
        context.view_layer.objects.active = root

        self.report({'INFO'}, f"VMDL '{root.name}' vytvořen. Původní objekt byl použit jako .model.")
        return {'FINISHED'}