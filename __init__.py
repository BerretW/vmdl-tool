bl_info = {
    "name": "VMDL Tools V3.0 (GLB)",
    "author": "Navrženo pro Mousiho, implementace a opravy AI, GLB refaktor",
    "version": (3, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > VMDL, a File > Import/Export",
    "description": "Kompletní balík pro vytváření a export herních modelů (.glb s VMDL metadaty)",
    "warning": "Přepracováno na standardní GLB formát s metadaty v 'extras'.",
    "category": "Import-Export",
}

import bpy

# Modulové importy
from . import (
    shader_definitions,
    constants,
    vmdl_utils,
    shader_materials,
    collider_tools,
    mountpoint_tools,
    export_vmdl,
    import_vmdl,
    ui_panel,
    ui_properties_panel,
    vertex_color_utils,
)

# Všechny třídy k registraci
classes = (
    # Vlastnosti (Properties)
    shader_materials.VMDLTextureProperty,
    shader_materials.VMDLParameterProperty,
    shader_materials.VMDLShaderProperties,
    collider_tools.VMDLColliderProperties,
    mountpoint_tools.VMDLMountpointProperties,
    export_vmdl.VMDLExportProperties,

    # Operátory
    shader_materials.VMDL_OT_load_image,
    shader_materials.VMDL_OT_save_material_preset,
    shader_materials.VMDL_OT_load_material_preset,
    shader_materials.VMDL_OT_fix_invalid_shader,
    vmdl_utils.VMDL_OT_create_vmdl_object,
    shader_materials.VMDL_OT_create_shader_material,
    vertex_color_utils.VMDL_OT_fill_vertex_color,
    vertex_color_utils.VMDL_OT_set_default_vertex_colors,
    vertex_color_utils.VMDL_OT_toggle_vertex_color_view,
    collider_tools.VMDL_OT_generate_collider_mesh,
    collider_tools.VMDL_OT_toggle_collider_shading,
    mountpoint_tools.VMDL_OT_create_mountpoint,
    export_vmdl.VMDL_OT_export_glb, # ZMĚNA NÁZVU
    import_vmdl.VMDL_OT_import_glb, # ZMĚNA NÁZVU

    # UI Panely
    ui_panel.VMDL_PT_main_panel,
    ui_panel.VMDL_PT_material_panel,
    ui_panel.VMDL_PT_collider_panel,
    ui_panel.VMDL_PT_mountpoint_panel,
    ui_panel.VMDL_PT_export_panel,
    ui_properties_panel.VMDL_PT_material_properties,
    ui_properties_panel.VMDL_PT_object_properties,
)


# Funkce, která přidá exportní operátor do menu
def menu_func_export(self, context):
    self.layout.operator(export_vmdl.VMDL_OT_export_glb.bl_idname, text="VMDL GLB (.glb)")

# Funkce, která přidá importní operátor do menu
def menu_func_import(self, context):
    self.layout.operator(import_vmdl.VMDL_OT_import_glb.bl_idname, text="VMDL GLB (.glb)")


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Material.vmdl_shader = bpy.props.PointerProperty(type=shader_materials.VMDLShaderProperties)
    bpy.types.Object.vmdl_collider = bpy.props.PointerProperty(type=collider_tools.VMDLColliderProperties)
    bpy.types.Object.vmdl_mountpoint = bpy.props.PointerProperty(type=mountpoint_tools.VMDLMountpointProperties)
    bpy.types.Scene.vmdl_export = bpy.props.PointerProperty(type=export_vmdl.VMDLExportProperties)
    bpy.types.Object.vmdl_enum_type = bpy.props.EnumProperty(
        name="VMDL Typ",
        description="Typ objektu podle VMDL systému",
        items=ui_properties_panel.vmdl_enum_items,
        get=ui_properties_panel.get_vmdl_enum,
        set=ui_properties_panel.set_vmdl_enum
    )

    # Přidání do menu File > Export/Import
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Material.vmdl_shader
    del bpy.types.Object.vmdl_collider
    del bpy.types.Object.vmdl_mountpoint
    del bpy.types.Scene.vmdl_export
    del bpy.types.Object.vmdl_enum_type

if __name__ == "__main__":
    register()