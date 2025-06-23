# Toto je centrální definiční soubor pro všechny shadery.
# Můžete zde snadno přidávat nové shadery nebo upravovat existující.

# Společná sada PBR parametrů pro většinu fyzikálních shaderů
BASE_PBR_PARAMETERS = [
    {"name": "pbrtweak_metallic", "type": "float", "default": 0.0},
    {"name": "pbrtweak_roughness", "type": "float", "default": 0.8},
    {"name": "pbrtweak_ao", "type": "float", "default": 1.0},
    {"name": "pbrtweak_sheen", "type": "float", "default": 0.0},
    {"name": "bumptiness", "type": "float", "default": 1.0},
    {"name": "wetnessmultiplier", "type": "float", "default": 1.0},
    {"name": "pbrglassiness", "type": "float", "default": 0.0},
    {"name": "pbrcavityrange", "type": "float", "default": 0.0},
    # Naše interní barvy pro řízení v Blenderu
    {"name": "Color1", "type": "vector4", "default": (0.5, 0.8, 1.0, 1.0)}, # G->Roughness, B->Normal, A->Saturation
    {"name": "Color2", "type": "vector4", "default": (0.0, 0.0, 0.0, 1.0)}, # R,G,B -> Blend
]

SHADER_DEFINITIONS = {
    "ShipStandard.vfx": {
        "parameters": BASE_PBR_PARAMETERS + [
            # Parametry specifické pouze pro ShipStandard
            {"name": "tintpalettefactor", "type": "float", "default": 0.0},
            {"name": "specmapintmask", "type": "vector4", "default": (1.0, 0.0, 0.0, 0.0)},
            {"name": "usepaintdetail", "type": "bool", "default": False},
        ],
        "textures": [
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
        "parameters": BASE_PBR_PARAMETERS + [
            # Parametry specifické pro Standard_dirt
            {"name": "dirt_strength", "type": "float", "default": 1.0},
        ],
        "textures": [
            {"name": "albedo", "label": "Albedo Texture"},
            {"name": "normal", "label": "Normal Texture"},
            {"name": "dirt", "label": "Dirt Texture"},
        ]
    },
    "Layered4.vfx": {
        "parameters": BASE_PBR_PARAMETERS + [
            # Parametry specifické pro Layered4
            {"name": "global_tint", "type": "vector4", "default": (1.0, 1.0, 1.0, 1.0)},
            {"name": "uv_scale", "type": "vector4", "default": (1.0, 1.0, 1.0, 1.0)}, # Používá se jako vec2, ale pro konzistenci
        ],
        "textures": [
            {"name": "layer1tex", "label": "Layer 1 (Base)"},
            {"name": "layer2tex", "label": "Layer 2 (Red)"},
            {"name": "layer3tex", "label": "Layer 3 (Green)"},
            {"name": "layer4tex", "label": "Layer 4 (Blue)"},
            {"name": "bumptex", "label": "Normal/Bump Texture"},
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
}