import bpy
from mathutils import Vector

class VMDLMountpointProperties(bpy.types.PropertyGroup):
    forward_vector: bpy.props.FloatVectorProperty(
        name="Forward",
        subtype='DIRECTION',
        default=(0.0, 1.0, 0.0)
    )
    up_vector: bpy.props.FloatVectorProperty(
        name="Up",
        subtype='DIRECTION',
        default=(0.0, 0.0, 1.0)
    )

class VMDL_OT_create_mountpoint(bpy.types.Operator):
    bl_idname = "vmdl.create_mountpoint"
    bl_label = "Create Mountpoint"
    bl_description = "Vytvoří mountpoint z výběru (kost, empty, vertex...)"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        sel_obj = context.active_object

        # Najdi VMDL root
        vmdl_root = None
        # OPRAVA: Používáme vmdl_enum_type pro konzistentní čtení
        if sel_obj.vmdl_enum_type == "ROOT":
            vmdl_root = sel_obj
        # OPRAVA: Používáme vmdl_enum_type pro konzistentní čtení
        elif sel_obj.parent and sel_obj.parent.vmdl_enum_type == "ROOT":
            vmdl_root = sel_obj.parent
        else:
            self.report({'ERROR'}, "Aktivní objekt není součástí VMDL hierarchie.")
            return {'CANCELLED'}

        pos = Vector((0, 0, 0))
        rot = (1, 0, 0, 0)  # Quaternion
        forward = Vector((0, 1, 0))
        up = Vector((0, 0, 1))

        if sel_obj.type == 'EMPTY':
            pos = sel_obj.matrix_world.to_translation()
            rot = sel_obj.matrix_world.to_quaternion()
            forward = sel_obj.matrix_world.to_3x3() @ Vector((0, 1, 0))
            up = sel_obj.matrix_world.to_3x3() @ Vector((0, 0, 1))

        elif sel_obj.type == 'ARMATURE' and context.mode == 'POSE':
            bone = context.selected_pose_bones[0] if context.selected_pose_bones else None
            if bone:
                pos = bone.tail
                forward = (bone.tail - bone.head).normalized()
                up = Vector((0, 0, 1)) if abs(forward.z) < 0.9 else Vector((0, 1, 0))
            else:
                self.report({'ERROR'}, "V Pose módu musí být vybrána kost.")
                return {'CANCELLED'}
        else:
            self.report({'ERROR'}, "Vyberte Empty nebo kost v Pose módu.")
            return {'CANCELLED'}

        bpy.ops.object.empty_add(type='ARROWS', location=pos, rotation=rot)
        mount_obj = context.active_object
        mount_obj.name = "MOUNT_" + sel_obj.name
        # OPRAVA: Používáme vmdl_enum_type pro konzistentní zápis
        mount_obj.vmdl_enum_type = "MOUNTPOINT"
        mount_obj.parent = vmdl_root

        mount_obj.vmdl_mountpoint.forward_vector = forward
        mount_obj.vmdl_mountpoint.up_vector = up

        self.report({'INFO'}, f"Mountpoint {mount_obj.name} vytvořen.")
        return {'FINISHED'}