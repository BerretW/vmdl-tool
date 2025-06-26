# ================================================
# FILE: __init__.py (Kompletní a opravená verze)
# ================================================
bl_info = {
    "name": "VMDL Tools V3.6 (Advanced Features)",
    "author": "Navrženo pro Mousiho, implementace a opravy AI, GLB refaktor, ZIP archivátor, Texture Utils, VC Editor, UI Refaktor, Advanced Shading",
    "version": (3, 6, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > VMDL, a File > Import/Export",
    "description": "Kompletní balík pro vytváření a export herních modelů (.vmdl archiv s .glb, metadaty a texturami)",
    "warning": "Přidána podpora pro Dirt Normal Mapy a interaktivní výběr Tint barvy.",
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
    texture_utils,
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
    vertex_color_utils.VMDLVertexColorToolsProperties,

    # Operátory
    shader_materials.VMDL_OT_load_image,
    shader_materials.VMDL_OT_clear_texture_slot,
    shader_materials.VMDL_OT_save_material_preset,
    shader_materials.VMDL_OT_load_material_preset,
    shader_materials.VMDL_OT_fix_invalid_shader,
    shader_materials.VMDL_OT_apply_tint_to_object,
    vmdl_utils.VMDL_OT_create_vmdl_object,
    shader_materials.VMDL_OT_create_shader_material,
    vertex_color_utils.VMDL_OT_toggle_vertex_color_view,
    vertex_color_utils.VMDL_OT_set_selection_vertex_color,
    vertex_color_utils.VMDL_OT_fill_vertex_color,
    vertex_color_utils.VMDL_OT_set_default_vertex_colors,
    vertex_color_utils.VMDL_OT_apply_global_vertex_data, # <-- ZDE JE PŘIDANÝ NOVÝ OPERÁTOR
    collider_tools.VMDL_OT_generate_collider_mesh,
    collider_tools.VMDL_OT_toggle_collider_shading,
    mountpoint_tools.VMDL_OT_create_mountpoint,
    export_vmdl.VMDL_OT_export_vmdl,
    import_vmdl.VMDL_OT_import_vmdl,
    texture_utils.VMDL_OT_extract_textures,

    # Menu
    shader_materials.VMDL_MT_create_material_menu,

    # UI Panely
    ui_panel.VMDL_PT_main_panel,
    ui_panel.VMDL_PT_material_panel,
    ui_panel.VMDL_PT_vertex_color_panel,
    ui_panel.VMDL_PT_collider_panel,
    ui_panel.VMDL_PT_mountpoint_panel,
    ui_panel.VMDL_PT_export_panel,
    ui_properties_panel.VMDL_PT_material_properties,
    ui_properties_panel.VMDL_PT_object_properties,
)

def menu_func_export(self, context):
    self.layout.operator(export_vmdl.VMDL_OT_export_vmdl.bl_idname, text="VMDL Archive (.vmdl)")
def menu_func_import(self, context):
    self.layout.operator(import_vmdl.VMDL_OT_import_vmdl.bl_idname, text="VMDL Archive (.vmdl)")

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Material.vmdl_shader = bpy.props.PointerProperty(type=shader_materials.VMDLShaderProperties)
    bpy.types.Object.vmdl_collider = bpy.props.PointerProperty(type=collider_tools.VMDLColliderProperties)
    bpy.types.Object.vmdl_mountpoint = bpy.props.PointerProperty(type=mountpoint_tools.VMDLMountpointProperties)
    bpy.types.Scene.vmdl_export = bpy.props.PointerProperty(type=export_vmdl.VMDLExportProperties)
    bpy.types.Scene.vmdl_vc_tools = bpy.props.PointerProperty(type=vertex_color_utils.VMDLVertexColorToolsProperties)

    bpy.types.Object.vmdl_enum_type = bpy.props.EnumProperty(
        name="VMDL Typ",
        description="Typ objektu podle VMDL systému",
        items=ui_properties_panel.vmdl_enum_items,
        get=ui_properties_panel.get_vmdl_enum,
        set=ui_properties_panel.set_vmdl_enum
    )
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
    del bpy.types.Scene.vmdl_vc_tools
    del bpy.types.Object.vmdl_enum_type

if __name__ == "__main__":
    register()