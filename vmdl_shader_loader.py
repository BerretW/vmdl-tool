import bpy

def make_image_loader(prop_name):
    class VMDL_OT_load_image(bpy.types.Operator):
        bl_idname = f"vmdl.load_image_{prop_name}"
        bl_label = f"Load {prop_name.capitalize()} Image"
        bl_description = "Načti texturu a přiřaď ji do shaderu"

        filepath: bpy.props.StringProperty(subtype='FILE_PATH')

        def execute(self, context):
            mat = context.material
            shader = mat.vmdl_shader
            try:
                image = bpy.data.images.load(bpy.path.abspath(self.filepath), check_existing=True)
                setattr(shader, f"{prop_name}_image", image)
                self.report({'INFO'}, f"Textura '{image.name}' načtena.")
            except Exception as e:
                self.report({'ERROR'}, str(e))
            return {'FINISHED'}

        def invoke(self, context, event):
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
    return VMDL_OT_load_image
