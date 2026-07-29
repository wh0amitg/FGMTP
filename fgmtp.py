import sys
import os
import argparse
import json


PNG_SIG_LINES = [b"137", b"80", b"78", b"71", b"13", b"10", b"26", b"10"]
FIELDS_PER_OBJECT = 15


def to_float(s):
    try:
        return float(s)
    except ValueError:
        return 0.0


def b64_to_bytes(b64_str):
    import base64
    return base64.b64decode(b64_str)


def decimal_lines_to_bytes(lines_list):
    nums = [int(x) for x in lines_list if x not in (b"", b"~")]
    b = bytes(nums)
    iend = b.rfind(b"IEND")
    return b[:iend + 8] if iend != -1 else b


def extract_named_textures(section_bytes, line_ending):
    lines = section_bytes.split(line_ending)

    starts = []
    i = 0
    while i < len(lines) - 8:
        if lines[i:i + 8] == PNG_SIG_LINES:
            starts.append(i)
            i += 8
        else:
            i += 1

    results = []
    for idx, s in enumerate(starts):
        name_idx = s - 1
        name = lines[name_idx].decode("utf-8", errors="ignore") if name_idx >= 0 else f"texture_{idx}"
        end = starts[idx + 1] - 2 if idx + 1 < len(starts) else len(lines)
        try:
            results.append((name, decimal_lines_to_bytes(lines[s:end])))
        except ValueError:
            continue
    return results


def parse_v1(path, data):
    sep_idx = data.find("§".encode("utf-8"))
    if sep_idx == -1:
        raise ValueError("no '§' section separator found")

    after_sep = data[sep_idx + len("§".encode("utf-8")):]
    line_ending = b"\r\n" if after_sep[:2] == b"\r\n" else b"\n"
    sep = "§".encode("utf-8") + line_ending

    sections = data.split(sep)
    if len(sections) < 7:
        raise ValueError(f"expected >=7 sections, found {len(sections)}")

    def lines(section):
        return [x for x in section.decode("utf-8", errors="ignore").split(line_ending.decode("utf-8")) if x]

    header, meta, sky = lines(sections[0]), lines(sections[1]), lines(sections[2])

    spawn_points = []
    for i in range(0, len(meta[3:]) - 5, 6):
        chunk = meta[3:][i:i + 6]
        if len(chunk) < 6:
            break
        spawn_points.append({
            "position": {"x": to_float(chunk[0]), "y": to_float(chunk[1]), "z": to_float(chunk[2])},
            "rotation": {"x": to_float(chunk[3]), "y": to_float(chunk[4]), "z": to_float(chunk[5])},
        })
    spawn = spawn_points[0] if spawn_points else {
        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
        "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
    }

    sky_info = {
        "skyboxIndex": int(sky[0]) if len(sky) > 0 else 0,
        "lightRotation": {
            "x": to_float(sky[1]) if len(sky) > 1 else 0.0,
            "y": to_float(sky[2]) if len(sky) > 2 else 0.0,
            "z": to_float(sky[3]) if len(sky) > 3 else 0.0,
        },
        "lightIntensity": to_float(sky[4]) if len(sky) > 4 else 1.0,
        "fogStart": to_float(sky[5]) if len(sky) > 5 else 0.0,
        "fogEnd": to_float(sky[6]) if len(sky) > 6 else 0.0,
        "fogColorHex": sky[7] if len(sky) > 7 else "FFFFFF",
    }

    obj_lines = lines(sections[6])
    objects = []
    for i in range(0, len(obj_lines), FIELDS_PER_OBJECT):
        chunk = obj_lines[i:i + FIELDS_PER_OBJECT]
        if len(chunk) < FIELDS_PER_OBJECT:
            break
        objects.append({
            "material": chunk[0],
            "tileMode": chunk[1],
            "visible": chunk[2] == "True",
            "collisions": chunk[3] == "True",
            "physics": chunk[4] == "True",
            "texture": chunk[5],
            "position": {"x": to_float(chunk[6]), "y": to_float(chunk[7]), "z": to_float(chunk[8])},
            "rotation": {"x": to_float(chunk[9]), "y": to_float(chunk[10]), "z": to_float(chunk[11])},
            "scale": {"x": to_float(chunk[12]), "y": to_float(chunk[13]), "z": to_float(chunk[14])},
        })

    previews = []
    for idx in (3, 4):
        try:
            previews.append((f"preview_{idx}.png", decimal_lines_to_bytes(sections[idx].split(line_ending))))
        except Exception:
            pass

    return {
        "map_name": header[1] if len(header) > 1 else "unknown",
        "description": header[2] if len(header) > 2 else "",
        "date": meta[2] if len(meta) > 2 else "",
        "spawn": spawn,
        "sky": sky_info,
        "objects": objects,
        "previews": previews,
        "textures": extract_named_textures(sections[5], line_ending),
        "format": "V1",
    }


def parse_v2(path, data):
    doc = json.loads(data)

    spawn_points = doc.get("spawnPoints", [])
    spawn = spawn_points[0] if spawn_points else {
        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
        "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
    }

    sky = doc.get("skySettings", {})
    sky_info = {
        "skyboxIndex": sky.get("skyboxIndex", doc.get("selectedAmbience", 0)),
        "lightRotation": sky.get("lightRotation", {"x": 0.0, "y": 0.0, "z": 0.0}),
        "lightIntensity": sky.get("lightIntensity", 1.0),
        "fogStart": sky.get("fogStart", 0.0),
        "fogEnd": sky.get("fogEnd", 0.0),
        "fogColorHex": sky.get("fogColorHex", "FFFFFF"),
    }

    objects = [{
        "material": cube.get("tag", ""),
        "tileMode": cube.get("tileMode", 0),
        "visible": cube.get("visible", True),
        "collisions": cube.get("collisions", True),
        "physics": cube.get("physics", False),
        "texture": cube.get("materialName", ""),
        "position": cube.get("position", {"x": 0.0, "y": 0.0, "z": 0.0}),
        "rotation": cube.get("rotation", {"x": 0.0, "y": 0.0, "z": 0.0}),
        "scale": cube.get("scale", {"x": 1.0, "y": 1.0, "z": 1.0}),
    } for cube in doc.get("mapCubes", [])]

    textures = []
    for tex in doc.get("customTextures", []):
        try:
            textures.append((tex.get("name", "texture"), b64_to_bytes(tex.get("base64Data", ""))))
        except Exception:
            pass

    previews = []
    for key, name in (("iconBase64", "preview_icon.png"), ("bannerBase64", "preview_banner.png")):
        if doc.get(key):
            try:
                previews.append((name, b64_to_bytes(doc[key])))
            except Exception:
                pass

    return {
        "map_name": doc.get("name", "unknown"),
        "description": doc.get("description", ""),
        "date": doc.get("exportDate", ""),
        "spawn": spawn,
        "sky": sky_info,
        "objects": objects,
        "previews": previews,
        "textures": textures,
        "format": "V2",
    }


def parse_gbmap(path):
    with open(path, "rb") as f:
        data = f.read()

    if data.lstrip()[:1] == b"{":
        return parse_v2(path, data)
    return parse_v1(path, data)


def build_project(map_data, outdir):
    os.makedirs(outdir, exist_ok=True)
    tex_dir = os.path.join(outdir, "CustomTextures")
    os.makedirs(tex_dir, exist_ok=True)

    project_file = {
        "version": 4,
        "name": map_data["map_name"],
        "description": map_data["description"],
        "lastModified": map_data["date"],
        "selectedAmbience": map_data["sky"]["skyboxIndex"],
        "spawnPoints": [map_data["spawn"]],
        "skySettings": map_data["sky"],
    }

    cubes = [{
        "name": "MapCube",
        "tag": obj["material"],
        "tileMode": int(obj["tileMode"]),
        "visible": obj["visible"],
        "collisions": obj["collisions"],
        "physics": obj["physics"],
        "materialName": obj["texture"],
        "position": obj["position"],
        "rotation": obj["rotation"],
        "scale": obj["scale"],
    } for obj in map_data["objects"]]

    with open(os.path.join(outdir, "ProjectFile.json"), "w", encoding="utf-8") as f:
        json.dump(project_file, f, indent=4, ensure_ascii=False)

    with open(os.path.join(outdir, "MapData.json"), "w", encoding="utf-8") as f:
        json.dump({"version": 4, "cubes": cubes}, f, indent=2, ensure_ascii=False)

    for name, png_bytes in map_data["textures"]:
        with open(os.path.join(tex_dir, f"{name}.png"), "wb") as f:
            f.write(png_bytes)

    previews = map_data["previews"]
    if len(previews) >= 2:
        with open(os.path.join(outdir, "Icon.png"), "wb") as f:
            f.write(previews[0][1])
        with open(os.path.join(outdir, "Banner.png"), "wb") as f:
            f.write(previews[1][1])
    elif len(previews) == 1:
        with open(os.path.join(outdir, "Icon.png"), "wb") as f:
            f.write(previews[0][1])


def print_summary(map_data):
    sp = map_data["spawn"]["position"]
    print(f"[*] Map:      {map_data['map_name']}")
    print(f"[*] Format:   {map_data['format']}")
    print(f"[*] Objects:  {len(map_data['objects'])}")
    print(f"[*] Textures: {len(map_data['textures'])}")
    print(f"[*] Previews: {len(map_data['previews'])}")
    print(f"[*] Spawn:    {sp['x']:.2f}, {sp['y']:.2f}, {sp['z']:.2f}")


def main():
    parser = argparse.ArgumentParser(description="GoreBox .gbmap -> V2 project converter (V1 binary / V2 JSON)")
    parser.add_argument("gbmap_path", help="path to .gbmap file")
    parser.add_argument("--outdir", default=None, help="output folder (default: <name>_project next to input)")
    args = parser.parse_args()

    if not os.path.isfile(args.gbmap_path):
        print(f"[!] File not found: {args.gbmap_path}")
        sys.exit(1)

    print(f"[*] Reading: {args.gbmap_path}")
    try:
        map_data = parse_gbmap(args.gbmap_path)
    except Exception as e:
        print(f"[!] Parse failed: {e}")
        sys.exit(1)

    base = os.path.splitext(os.path.basename(args.gbmap_path))[0]
    src_dir = os.path.dirname(os.path.abspath(args.gbmap_path))

    outdir = args.outdir
    if outdir is None:
        outdir = os.path.join(src_dir, f"{base}_project")
        try:
            os.makedirs(outdir, exist_ok=True)
        except OSError:
            outdir = os.path.join(os.getcwd(), f"{base}_project")
            print(f"[!] No write access to source folder, using: {outdir}")

    print_summary(map_data)
    build_project(map_data, outdir)
    print(f"[+] Project written to: {outdir}")
    print(r"[*] Created By GBSKibidi\Ketam1n\wh0ami\@csharpdecompile.")


if __name__ == "__main__":
    main()
