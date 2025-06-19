# vmdl_plugin/constants.py

SHADER_TYPES = [
    "ShipStandard",
    "ShipGlass",
    "Layered4"
]

COLLIDER_TYPES = [
    {'name': 'Metal Hollow', 'id': 'COL_METAL_HOLLOW'},
    {'name': 'Metal Solid', 'id': 'COL_METAL_SOLID'},
    {'name': 'Wood Hollow', 'id': 'COL_WOOD_HOLLOW'},
    {'name': 'Wood Solid', 'id': 'COL_WOOD_SOLID'},
    {'name': 'Plastic', 'id': 'COL_PLASTIC'},
    {'name': 'Glass', 'id': 'COL_GLASS'},
]

COLLIDER_MATERIALS = {
    'COL_METAL_HOLLOW': (0.8, 0.8, 0.9, 1.0), # Světle modrá
    'COL_METAL_SOLID': (0.3, 0.3, 0.9, 1.0),  # Tmavě modrá
    'COL_WOOD_HOLLOW': (0.8, 0.6, 0.2, 1.0), # Světle hnědá
    'COL_WOOD_SOLID': (0.5, 0.3, 0.1, 1.0),  # Tmavě hnědá
    'COL_PLASTIC': (0.9, 0.2, 0.9, 1.0),     # Růžová
    'COL_GLASS': (0.5, 0.9, 0.9, 1.0),       # Tyrkysová
}