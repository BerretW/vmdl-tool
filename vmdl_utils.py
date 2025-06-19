# vmdl_plugin/vmdl_utils.py

import bpy

class VMDL_OT_create_vmdl_object(bpy.types.Operator):
    bl_idname = "vmdl.create_vmdl_object"
    bl_label = "Create VMDL Object"
    bl_description = "Vytvoří VMDL hierarchii s modelem a colliderem"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        source_obj = context.active_object

        # 1. Vytvoř root objekt (Empty)
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=source_obj.location)
        root = context.active_object
        root.name = source_obj.name + "_VMDL"
        root["vmdl_type"] = "ROOT"
        root.vmdl_enum_type = "ROOT"

        # 2. Duplikuj zdroj → .model
        bpy.ops.object.select_all(action='DESELECT')
        source_obj.select_set(True)
        bpy.ops.object.duplicate()
        model = context.selected_objects[0]
        model.name = source_obj.name + ".model"
        model.parent = root
        model.location = (0, 0, 0)
        model["vmdl_type"] = "MESH"
        model.vmdl_enum_type = "MESH"

        # 3. Duplikuj model → .col
        bpy.ops.object.select_all(action='DESELECT')
        model.select_set(True)
        bpy.ops.object.duplicate()
        col = context.selected_objects[0]
        col.name = source_obj.name + ".col"
        col.parent = root
        col.location = (0, 0, 0)
        col["vmdl_type"] = "COLLIDER"
        col.vmdl_enum_type = "COLLIDER"

        # 4. Přepnout zpět na model
        bpy.ops.object.select_all(action='DESELECT')
        model.select_set(True)
        context.view_layer.objects.active = model

        self.report({'INFO'}, f"VMDL '{root.name}' vytvořen s .model a .col")
        return {'FINISHED'}
