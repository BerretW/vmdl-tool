bl_info = {
    "name": "VMDL Tools V2.0",
    "author": "Navrženo pro Mousiho, implementace a refactoring AI",
    "version": (2, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > VMDL Tools",
    "description": "Kompletní balík pro vytváření a export herních modelů (.vmdl.pkg)",
    "warning": "Plugin byl kompletně přestavěn na daty řízený systém.",
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
    vmdl_utils.VMDL_OT_create_vmdl_object,
    shader_materials.VMDL_OT_create_shader_material,
    vertex_color_utils.VMDL_OT_fill_vertex_color,
    collider_tools.VMDL_OT_generate_collider_mesh,
    collider_tools.VMDL_OT_toggle_collider_shading,
    mountpoint_tools.VMDL_OT_create_mountpoint,
    export_vmdl.VMDL_OT_export_package,
    import_vmdl.VMDL_OT_import_package,

    # UI Panely
    ui_panel.VMDL_PT_main_panel,
    ui_panel.VMDL_PT_material_panel,
    ui_panel.VMDL_PT_collider_panel,
    ui_panel.VMDL_PT_mountpoint_panel,
    ui_panel.VMDL_PT_export_panel,
    ui_properties_panel.VMDL_PT_material_properties,
    ui_properties_panel.VMDL_PT_object_properties,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # Přidání vlastností do Blender datových struktur
    bpy.types.Material.vmdl_shader = bpy.props.PointerProperty(type=shader_materials.VMDLShaderProperties)
    bpy.types.Object.vmdl_collider = bpy.props.PointerProperty(type=collider_tools.VMDLColliderProperties)
    bpy.types.Object.vmdl_mountpoint = bpy.props.PointerProperty(type=mountpoint_tools.VMDLMountpointProperties)
    bpy.types.Scene.vmdl_export = bpy.props.PointerProperty(type=export_vmdl.VMDLExportProperties)

    # Enum synchronizovaný s vmdl_type
    bpy.types.Object.vmdl_enum_type = bpy.props.EnumProperty(
        name="VMDL Typ",
        description="Typ objektu podle VMDL systému",
        items=ui_properties_panel.vmdl_enum_items,
        get=ui_properties_panel.get_vmdl_enum,
        set=ui_properties_panel.set_vmdl_enum
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # Odstranění přidaných vlastností
    del bpy.types.Material.vmdl_shader
    del bpy.types.Object.vmdl_collider
    del bpy.types.Object.vmdl_mountpoint
    del bpy.types.Scene.vmdl_export
    del bpy.types.Object.vmdl_enum_type

if __name__ == "__main__":
    register()