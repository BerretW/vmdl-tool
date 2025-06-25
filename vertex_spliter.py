
import bpy
from bpy.props import StringProperty


bl_info = {
    "name": "Vertex Color Channel Tool (Auto-Active)",
    "author": "ChatGPT + Mousi",
    "version": (4, 0, 0), # Verze s automatickým výběrem
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Vertex Colors",
    "description": "Automaticky rozdělí aktivní vertex color vrstvu a umožní spojení kanálů.",
    "category": "Mesh",
}


class VERTEXCOLOR_Props(bpy.types.PropertyGroup):
    """Vlastnosti pro náš nástroj. Sekce pro rozdělení byla odstraněna."""
    # Pro spojování zůstávají StringProperty, které obsluhuje robustní prop_search
    combine_r: StringProperty(name="R vrstva")
    combine_g: StringProperty(name="G vrstva")
    combine_b: StringProperty(name="B vrstva")
    combine_a: StringProperty(name="A vrstva")
    
    combine_name: StringProperty(
        name="Název cílové vrstvy",
        default="VC_Recombined"
    )


def ensure_layer(obj, name):
    """Ponecháváme původní metodu s 'POINT' doménou."""
    if name not in obj.data.color_attributes:
        obj.data.color_attributes.new(name=name, type='BYTE_COLOR', domain='POINT')
    return obj.data.color_attributes[name]


def redraw_ui(context):
    """Pomocná funkce pro vynucení překreslení UI."""
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


class VERTEXCOLOR_OT_split_active(bpy.types.Operator): # Přejmenováno pro přehlednost
    """HLAVNÍ ZMĚNA: Tento operátor nyní pracuje pouze s aktivní vrstvou."""
    bl_idname = "vertexcolor.split_active" # Změněno ID pro přehlednost
    bl_label = "Rozdělit aktivní vrstvu"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Tlačítko bude aktivní, pouze pokud existuje aktivní objekt,
        # je to MESH a má nastavenou aktivní Vertex Color vrstvu.
        obj = context.object
        if obj and obj.type == 'MESH':
            return obj.data.color_attributes.active_color is not None
        return False

    def execute(self, context):
        obj = context.object
        mesh = obj.data

        # Získáme přímo aktivní vrstvu. Díky `poll` víme, že existuje.
        src_layer = mesh.color_attributes.active_color
        layer_name = src_layer.name

        self.report({'INFO'}, f"Rozděluji vrstvu: '{layer_name}'...")

        # Zbytek logiky je stejný jako ve vaší původní, funkční verzi
        for ch in "RGBA":
            ensure_layer(obj, f"{layer_name}_{ch}")

        for i in range(len(mesh.loops)):
            color = src_layer.data[i].color
            mesh.color_attributes[f"{layer_name}_R"].data[i].color = (color[0], 0, 0, 1)
            mesh.color_attributes[f"{layer_name}_G"].data[i].color = (0, color[1], 0, 1)
            mesh.color_attributes[f"{layer_name}_B"].data[i].color = (0, 0, color[2], 1)
            mesh.color_attributes[f"{layer_name}_A"].data[i].color = (0, 0, 0, color[3])
        
        redraw_ui(context)
        self.report({'INFO'}, f"Vrstva '{layer_name}' byla úspěšně rozdělena.")
        return {'FINISHED'}


class VERTEXCOLOR_OT_combine_selected(bpy.types.Operator):
    """Tento operátor zůstává beze změny, je již robustní."""
    bl_idname = "vertexcolor.combine_selected"
    bl_label = "Spojit vybrané kanály"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        mesh = obj.data
        props = context.scene.vertexcolor_tool

        layers = {
            'R': mesh.color_attributes.get(props.combine_r),
            'G': mesh.color_attributes.get(props.combine_g),
            'B': mesh.color_attributes.get(props.combine_b),
            'A': mesh.color_attributes.get(props.combine_a),
        }

        if not all(layers.values()):
            self.report({'ERROR'}, "Chybí některé vrstvy pro spojení")
            return {'CANCELLED'}

        result = ensure_layer(obj, props.combine_name)

        for i in range(len(mesh.loops)):
            rc = layers['R'].data[i].color[0]
            gc = layers['G'].data[i].color[1]
            bc = layers['B'].data[i].color[2]
            ac = layers['A'].data[i].color[3]
            result.data[i].color = (rc, gc, bc, ac)

        mesh.color_attributes.active_color_index = list(mesh.color_attributes).index(result)
        redraw_ui(context)
        self.report({'INFO'}, f"Vrstvy spojeny do '{props.combine_name}'.")
        return {'FINISHED'}


class VERTEXCOLOR_PT_main_panel(bpy.types.Panel):
    """Panel byl výrazně zjednodušen."""
    bl_label = "Vertex Color Tools"
    bl_idname = "VERTEXCOLOR_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Vertex Colors"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and obj.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        obj = context.object
        props = context.scene.vertexcolor_tool
        
        active_layer = obj.data.color_attributes.active_color

        # Sekce pro rozdělení byla kompletně přepracována
        box = layout.box()
        box.label(text="Rozdělení aktivní vrstvy:")

        if active_layer:
            # Informujeme uživatele, která vrstva bude rozdělena
            row = box.row()
            row.label(text=f"Aktivní: {active_layer.name}", icon='COLOR')
            # Zobrazíme tlačítko operátoru
            box.operator("vertexcolor.split_active")
        else:
            # Pokud žádná vrstva není aktivní, zobrazíme informaci
            box.label(text="Vyberte aktivní vrstvu v 'Object Data'", icon='INFO')

        # Sekce pro spojení zůstává stejná
        box = layout.box()
        box.label(text="Spojení RGBA do vrstvy:")
        
        if obj.data.color_attributes:
            col = box.column(align=True)
            col.prop_search(props, "combine_r", obj.data, "color_attributes", text="R")
            col.prop_search(props, "combine_g", obj.data, "color_attributes", text="G")
            col.prop_search(props, "combine_b", obj.data, "color_attributes", text="B")
            col.prop_search(props, "combine_a", obj.data, "color_attributes", text="A")
            
            box.prop(props, "combine_name")
            box.operator("vertexcolor.combine_selected")
        else:
            box.label(text="Objekt nemá žádné vrstvy.", icon='INFO')


# Registrace nyní obsahuje nový operátor
classes = (
    VERTEXCOLOR_Props,
    VERTEXCOLOR_OT_split_active, # Používáme nový operátor
    VERTEXCOLOR_OT_combine_selected,
    VERTEXCOLOR_PT_main_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.vertexcolor_tool = bpy.props.PointerProperty(type=VERTEXCOLOR_Props)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.vertexcolor_tool

if __name__ == "__main__":
    register()
