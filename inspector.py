from pygltflib import GLTF2
import json

def read_extras(gltf):
    try:
        # Extras bývají jako JSON string v gltf.extras
        extras_data = gltf.extras
        if isinstance(extras_data, str):
            extras = json.loads(extras_data)
        elif isinstance(extras_data, dict):
            extras = extras_data
        else:
            extras = {}
        return extras
    except Exception as e:
        print(f"[!] Chyba při čtení extras: {e}")
        return {}

def print_vmdl_metadata(extras):
    print("🧠 VMDL Metadata:")
    print(f"- VMDL verze: {extras.get('vmdl_version', 'neznámá')}")

    print("\n🎨 Materiály:")
    for mat_name, mat_data in extras.get("materials", {}).items():
        print(f"  • {mat_name}")
        print(f"    - Shader: {mat_data.get('shader_name')}")
        for param, value in mat_data.get("parameters", {}).items():
            print(f"      Param: {param} = {value}")
        for tex, tex_file in mat_data.get("textures", {}).items():
            print(f"      Textura: {tex} -> {tex_file}")

    print("\n📦 Objekty:")
    for obj_name, obj_data in extras.get("objects", {}).items():
        print(f"  • {obj_name}")
        print(f"    - Typ: {obj_data.get('vmdl_type')}")
        if obj_data.get('vmdl_type') == 'COLLIDER':
            print(f"    - Collider typ: {obj_data.get('collider_type')}")
        elif obj_data.get('vmdl_type') == 'MOUNTPOINT':
            print(f"    - Forward: {obj_data.get('forward_vector')}")
            print(f"    - Up: {obj_data.get('up_vector')}")

def main():
    path = input("Zadej cestu k .glb souboru: ").strip()
    try:
        gltf = GLTF2().load(path)
        extras = read_extras(gltf)
        if not extras:
            print("⚠️  Žádné VMDL metadata ('extras') nebyly nalezeny.")
            return
        print_vmdl_metadata(extras)
    except Exception as e:
        print(f"❌ Chyba při načítání .glb: {e}")

if __name__ == "__main__":
    main()
