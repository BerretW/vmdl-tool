import bpy
from .constants import COLLIDER_TYPES, COLLIDER_MATERIALS

class VMDLColliderProperties(bpy.types.PropertyGroup):
    collider_type: bpy.props.EnumProperty(
        items=[(ct['id'], ct['name'], "") for ct in COLLIDER_TYPES],
        name="Collider Type",
        description="Typ fyzikálního materiálu collideru"
    )

class VMDL_OT_generate_collider_mesh(bpy.types.Operator):
    bl_idname = "vmdl.generate_collider_mesh"
    bl_label = "Generate Collider Mesh"
    bl_description = "Vytvoří duplikát meshe jako základ pro collider"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        # OPRAVA: Používáme vmdl_enum_type pro konzistentní čtení
        return obj and obj.type == 'MESH' and obj.vmdl_enum_type == "MESH"

    def execute(self, context):
        source_obj = context.active_object
        vmdl_root = source_obj.parent
        
        # OPRAVA: Používáme vmdl_enum_type pro konzistentní čtení
        if not vmdl_root or vmdl_root.vmdl_enum_type != "ROOT":
            self.report({'ERROR'}, "Zdrojový mesh musí být součástí VMDL hierarchie.")
            return {'CANCELLED'}
            
        # Smazat starý collider pokud existuje
        for child in vmdl_root.children:
            # OPRAVA: Používáme vmdl_enum_type pro konzistentní čtení
            if child.vmdl_enum_type == "COLLIDER":
                bpy.data.objects.remove(child, do_unlink=True)
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        source_obj.select_set(True)
        bpy.ops.object.duplicate()
        collider_obj = context.active_object
        collider_obj.name = source_obj.name.replace('.model', '.col')
        # OPRAVA: Používáme vmdl_enum_type pro konzistentní zápis
        collider_obj.vmdl_enum_type = "COLLIDER"
        collider_obj.parent = vmdl_root
        
        self.report({'INFO'}, f"Collider {collider_obj.name} vytvořen.")
        return {'FINISHED'}

class VMDL_OT_toggle_collider_shading(bpy.types.Operator):
    bl_idname = "vmdl.toggle_collider_shading"
    bl_label = "Toggle Collider Preview Shading"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        # OPRAVA: Používáme vmdl_enum_type pro konzistentní čtení
        return obj and obj.vmdl_enum_type == "COLLIDER"

    def execute(self, context):
        obj = context.active_object
        col_type = obj.vmdl_collider.collider_type
        
        if not col_type:
            self.report({'WARNING'}, "Není nastaven typ collideru.")
            return {'CANCELLED'}

        mat_name = "VMDL_COL_PREVIEW_" + col_type
        mat = bpy.data.materials.get(mat_name)
        
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            mat.diffuse_color = COLLIDER_MATERIALS.get(col_type, (0.8, 0.8, 0.8, 1.0))
        
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
            
        return {'FINISHED'}