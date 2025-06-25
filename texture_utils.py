import bpy
import os
import shutil
from bpy_extras.io_utils import ExportHelper

class VMDL_OT_extract_textures(bpy.types.Operator, ExportHelper):
    """
    Najde všechny textury použité na aktivním VMDL modelu
    a uloží je do vybraného adresáře.
    """
    bl_idname = "vmdl.extract_textures"
    bl_label = "Extract Model Textures"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Používáme ExportHelper, ale ne pro soubor, ale pro cestu k adresáři
    filename_ext = ""  # Prázdné, protože vybíráme adresář

    filepath: bpy.props.StringProperty(
        name="Output Directory",
        description="Vyberte adresář, kam se mají textury extrahovat",
        subtype='DIR_PATH' # Důležité: vybíráme adresář
    )

    @classmethod
    def poll(cls, context):
        # Operátor je aktivní, pokud existuje nějaký VMDL Root objekt ve scéně
        for obj in context.scene.objects:
            if obj.vmdl_enum_type == "ROOT":
                return True
        return False

    def execute(self, context):
        # Najdi VMDL root objekt
        root_obj = None
        for obj in context.scene.objects:
            if obj.vmdl_enum_type == "ROOT":
                root_obj = obj
                break
        
        if not root_obj:
            self.report({'ERROR'}, "Ve scéně nebyl nalezen žádný VMDL Root objekt.")
            return {'CANCELLED'}

        # Shromáždi všechny unikátní obrázky z meshů pod rootem
        unique_images = set()
        objects_to_scan = [root_obj] + list(root_obj.children_recursive)
        
        for obj in objects_to_scan:
            if obj.type != 'MESH' or not obj.data.materials:
                continue
            
            for mat in obj.data.materials:
                if mat and hasattr(mat, "vmdl_shader"):
                    for tex_prop in mat.vmdl_shader.textures:
                        if tex_prop.image:
                            unique_images.add(tex_prop.image)

        if not unique_images:
            self.report({'INFO'}, "Na modelu nebyly nalezeny žádné VMDL textury k extrahování.")
            return {'FINISHED'}

        # Uložení každého unikátního obrázku
        extracted_count = 0
        output_dir = self.filepath # Cesta k adresáři vybraná uživatelem
        
        for image in unique_images:
            if not image.has_data:
                print(f"Přeskakuji texturu '{image.name}', protože nemá data (je prázdná).")
                continue
            
            # Název výstupního souboru bude jméno datablocku obrázku
            dest_filename = os.path.basename(image.name)
            dest_filepath = os.path.join(output_dir, dest_filename)
            
            # Robustní způsob uložení/kopírování
            try:
                # Pokud je obrázek zabalený v .blend souboru nebo nemá platnou cestu,
                # uložíme ho z paměti Blenderu.
                if image.packed_file or not os.path.exists(bpy.path.abspath(image.filepath_raw)):
                    # Vytvoříme dočasnou kopii obrázku, abychom mohli změnit formát bez ovlivnění originálu
                    temp_image = image.copy()
                    temp_image.filepath_raw = dest_filepath
                    temp_image.file_format = image.file_format or 'PNG' # Výchozí formát, pokud není znám
                    temp_image.save()
                    bpy.data.images.remove(temp_image) # Uklidíme dočasnou kopii
                    print(f"Uloženo (z paměti): {dest_filename}")
                else:
                    # Pokud obrázek existuje na disku, jednoduše ho zkopírujeme. Je to rychlejší.
                    shutil.copy(bpy.path.abspath(image.filepath_raw), dest_filepath)
                    print(f"Zkopírováno: {dest_filename}")
                
                extracted_count += 1
            except Exception as e:
                self.report({'ERROR'}, f"Nepodařilo se uložit '{image.name}': {e}")
                print(f"Chyba při ukládání '{image.name}': {e}")


        self.report({'INFO'}, f"Úspěšně extrahováno {extracted_count} textur do '{output_dir}'.")
        return {'FINISHED'}