# Toto je centrální definiční soubor pro všechny shadery.
# Můžete zde snadno přidávat nové shadery nebo upravovat existující.
# Plugin se automaticky přizpůsobí změnám v tomto souboru.

SHADER_DEFINITIONS = {
    # Název shaderu, jak ho používá hra
    "ShipStandard.vfx": {
        "parameters": [
            # Parametry jsou definovány jako slovníky s názvem, typem a výchozí hodnotou
            {"name": "tintpalettefactor", "type": "float", "default": 0.0},
            {"name": "specmapintmask", "type": "vector4", "default": (1.0, 0.0, 0.0, 0.0)},
            {"name": "pbrglassiness", "type": "float", "default": 0.0},
            {"name": "pbrcavityrange", "type": "float", "default": 0.0},
            {"name": "pbrtweak_metallic", "type": "float", "default": 0.0},
            {"name": "pbrtweak_sheen", "type": "float", "default": 0.0},
            {"name": "pbrtweak_roughness", "type": "float", "default": 0.8},
            {"name": "pbrtweak_ao", "type": "float", "default": 1.0},
            {"name": "bumptiness", "type": "float", "default": 1.0},
            {"name": "wetnessmultiplier", "type": "float", "default": 1.0},
            {"name": "usepaintdetail", "type": "bool", "default": False},
            # Přidány Color1 a Color2 pro kompatibilitu s naším systémem
            {"name": "Color1", "type": "vector4", "default": (0.5, 0.5, 1.0, 1.0)},
            {"name": "Color2", "type": "vector4", "default": (0.0, 0.0, 0.0, 1.0)},
        ],
        "textures": [
            # Textury jsou jednodušší, mají jen 'name' (pro engine) a 'label' (pro UI)
            {"name": "tintpalettetex", "label": "Tint Palette"},
            {"name": "diffusetex", "label": "Diffuse Texture"},
            {"name": "detailtexarrayn", "label": "Detail Normal Array"},
            {"name": "diffusetex2", "label": "Diffuse Texture 2"},
            {"name": "bumptex", "label": "Normal/Bump Texture"},
            {"name": "speculartex", "label": "Specular Texture"},
            {"name": "speculartex2", "label": "Specular Texture 2"},
        ]
    },
    "Standard_dirt.vfx": {
        "parameters": [
            {"name": "Color1", "type": "vector4", "default": (0.5, 0.5, 1.0, 1.0)},
            {"name": "Color2", "type": "vector4", "default": (0.0, 0.0, 0.0, 1.0)},
            {"name": "dirt_strength", "type": "float", "default": 1.0},
        ],
        "textures": [
            {"name": "albedo", "label": "Albedo Texture"},
            {"name": "normal", "label": "Normal Texture"},
            {"name": "dirt", "label": "Dirt Texture"},
        ]
    },
    "ShipGlass.vfx": {
         "parameters": [
            {"name": "opacity", "type": "float", "default": 0.2},
            {"name": "fresnel_power", "type": "float", "default": 5.0},
            {"name": "reflectivity", "type": "float", "default": 0.5},
            {"name": "tint_color", "type": "vector4", "default": (1.0, 1.0, 1.0, 1.0)},
        ],
        "textures": [
             {"name": "opacity_map", "label": "Opacity Map"},
        ]
    },
    # Zde můžete přidat definice pro 'Layered4.vfx', 'Character.vfx' atd.
}