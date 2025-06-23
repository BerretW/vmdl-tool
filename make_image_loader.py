import bpy

def make_image_loader(prop_name):
    """
    Továrna pro vytváření operátorů pro načítání obrázků.
    prop_name: název property bez '_image' (např. 'albedo', 'normal').
    """
    class VMDL_OT_load_image(bpy.types.Operator):
        bl_idname = f"vmdl.load_image_{prop_name}"
        bl_label = f"Load {prop_name.capitalize()} Image"
        bl_description = f"Načti {prop_name} texturu a přiřaď ji do shaderu"
        bl_options = {'REGISTER', 'UNDO'}

        filepath: bpy.props.StringProperty(subtype="FILE_PATH")
        filter_glob: bpy.props.StringProperty(
            default="*.png;*.jpg;*.jpeg;*.tga;*.bmp;*.tif;*.tiff",
            options={'HIDDEN'},
        )

        def execute(self, context):
            mat = context.material
            if not mat:
                self.report({'ERROR'}, "Není aktivní žádný materiál.")
                return {'CANCELLED'}

            shader = mat.vmdl_shader
            image_prop_name = f"{prop_name}_image"

            if not hasattr(shader, image_prop_name):
                self.report({'ERROR'}, f"Vlastnost '{image_prop_name}' na shaderu neexistuje.")
                return {'CANCELLED'}

            try:
                # Použijeme abspath pro korektní zpracování relativních cest
                abs_filepath = bpy.path.abspath(self.filepath)
                image = bpy.data.images.load(abs_filepath, check_existing=True)
                
                # Nastavíme color space pro Normal mapy
                if prop_name == "normal":
                    image.colorspace_settings.name = 'Non-Color'
                
                setattr(shader, image_prop_name, image)
                self.report({'INFO'}, f"Textura '{image.name}' načtena.")
            except Exception as e:
                self.report({'ERROR'}, f"Načtení obrázku selhalo: {e}")
                return {'CANCELLED'}
            return {'FINISHED'}

        def invoke(self, context, event):
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
            
    # Dynamicky nastavíme název třídy, aby se předešlo kolizím při registraci
    VMDL_OT_load_image.__name__ = f"VMDL_OT_LoadImage_{prop_name.capitalize()}"
    return VMDL_OT_load_image