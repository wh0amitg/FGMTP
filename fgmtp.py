import sys
import os
import argparse
import json


SEP = "§\r\n".encode("utf-8")
PNG_SIG_LINES = [b"137", b"80", b"78", b"71", b"13", b"10", b"26", b"10"]


def to_float(s):
    try:
        return float(s)
    except ValueError:
        return 0.0


def _b64_to_bytes(b64_str):
    import base64
    return base64.b64decode(b64_str)


def parse_gbmap_v1_folder(folder_path):
    gbi_path = os.path.join(folder_path, "projectFile.gbi")
    mapdata_dir = os.path.join(folder_path, "MapData")
    tex_dir = os.path.join(folder_path, "CustomTextures")

    if not os.path.isfile(gbi_path):
        raise ValueError(f"projectFile.gbi not found in: {folder_path}")

    with open(gbi_path, "rb") as f:
        gbi_data = f.read()
    fields = [x for x in gbi_data.decode("utf-8", errors="ignore").split("\r\n") if x != ""]

    map_name = fields[1] if len(fields) > 1 else "unknown"
    description = fields[2] if len(fields) > 2 else ""
    date = fields[3] if len(fields) > 3 else ""

    sep_idx = fields.index("§") if "§" in fields else 4
    sky_fields = fields[sep_idx + 1:]
    sky_info = {
        "skyboxIndex": int(sky_fields[0]) if len(sky_fields) > 0 else 0,
        "lightRotation": {
            "x": to_float(sky_fields[1]) if len(sky_fields) > 1 else 0.0,
            "y": to_float(sky_fields[2]) if len(sky_fields) > 2 else 0.0,
            "z": to_float(sky_fields[3]) if len(sky_fields) > 3 else 0.0,
        },
        "lightIntensity": to_float(sky_fields[4]) if len(sky_fields) > 4 else 1.0,
        "fogStart": to_float(sky_fields[5]) if len(sky_fields) > 5 else 0.0,
        "fogEnd": to_float(sky_fields[6]) if len(sky_fields) > 6 else 0.0,
        "fogColorHex": sky_fields[7] if len(sky_fields) > 7 else "FFFFFF",
    }

    spawn_points = []
    spawn_pos = {"x": 0.0, "y": 0.0, "z": 0.0}
    spawn_rot = {"x": 0.0, "y": 0.0, "z": 0.0}

    objects = []
    if os.path.isdir(mapdata_dir):
        cube_files = sorted(
            [f for f in os.listdir(mapdata_dir) if f.endswith(".mapCube")],
            key=lambda n: (len(n), n),
        )
        for fname in cube_files:
            with open(os.path.join(mapdata_dir, fname), "rb") as f:
                cube_data = f.read()
            chunk = [x for x in cube_data.decode("utf-8", errors="ignore").split("\r\n") if x != ""]
            if len(chunk) < 15:
                continue
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

    textures = []
    if os.path.isdir(tex_dir):
        for fname in sorted(os.listdir(tex_dir)):
            if fname.lower().endswith(".png"):
                with open(os.path.join(tex_dir, fname), "rb") as f:
                    textures.append((os.path.splitext(fname)[0], f.read()))

    previews = []
    icon_path = os.path.join(folder_path, "icon.png")
    banner_path = os.path.join(folder_path, "banner.png")
    if os.path.isfile(icon_path):
        with open(icon_path, "rb") as f:
            previews.append(("preview_icon.png", f.read()))
    if os.path.isfile(banner_path):
        with open(banner_path, "rb") as f:
            previews.append(("preview_banner.png", f.read()))

    return {
        "map_name": map_name,
        "description": description,
        "date": date,
        "num_objects": len(objects),
        "spawn_pos": spawn_pos,
        "spawn_rot": spawn_rot,
        "spawn_points": spawn_points,
        "sky": sky_info,
        "objects": objects,
        "previews": previews,
        "textures": textures,
        "source_format": "v1_folder",
    }


def parse_gbmap_v4(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    spawn_points_raw = data.get("spawnPoints", [])
    spawn_points = []
    for sp in spawn_points_raw:
        spawn_points.append({
            "position": sp.get("position", {"x": 0.0, "y": 0.0, "z": 0.0}),
            "rotation": sp.get("rotation", {"x": 0.0, "y": 0.0, "z": 0.0}),
        })
    if spawn_points:
        spawn_pos = spawn_points[0]["position"]
        spawn_rot = spawn_points[0]["rotation"]
    else:
        spawn_pos = {"x": 0.0, "y": 0.0, "z": 0.0}
        spawn_rot = {"x": 0.0, "y": 0.0, "z": 0.0}

    sky = data.get("skySettings", {})
    sky_info = {
        "skyboxIndex": sky.get("skyboxIndex", data.get("selectedAmbience", 0)),
        "lightRotation": sky.get("lightRotation", {"x": 0.0, "y": 0.0, "z": 0.0}),
        "lightIntensity": sky.get("lightIntensity", 1.0),
        "fogStart": sky.get("fogStart", 0.0),
        "fogEnd": sky.get("fogEnd", 0.0),
        "fogColorHex": sky.get("fogColorHex", "FFFFFF"),
    }

    objects = []
    for cube in data.get("mapCubes", []):
        objects.append({
            "material": cube.get("tag", ""),
            "tileMode": cube.get("tileMode", 0),
            "visible": cube.get("visible", True),
            "collisions": cube.get("collisions", True),
            "physics": cube.get("physics", False),
            "texture": cube.get("materialName", ""),
            "position": cube.get("position", {"x": 0.0, "y": 0.0, "z": 0.0}),
            "rotation": cube.get("rotation", {"x": 0.0, "y": 0.0, "z": 0.0}),
            "scale": cube.get("scale", {"x": 1.0, "y": 1.0, "z": 1.0}),
        })

    textures = []
    for tex in data.get("customTextures", []):
        name = tex.get("name", "texture")
        b64 = tex.get("base64Data", "")
        try:
            textures.append((name, _b64_to_bytes(b64)))
        except Exception:
            pass

    previews = []
    if data.get("iconBase64"):
        try:
            previews.append(("preview_icon.png", _b64_to_bytes(data["iconBase64"])))
        except Exception:
            pass
    if data.get("bannerBase64"):
        try:
            previews.append(("preview_banner.png", _b64_to_bytes(data["bannerBase64"])))
        except Exception:
            pass

    return {
        "map_name": data.get("name", "unknown"),
        "description": data.get("description", ""),
        "date": data.get("exportDate", ""),
        "num_objects": data.get("objectCount", len(objects)),
        "spawn_pos": spawn_pos,
        "spawn_rot": spawn_rot,
        "spawn_points": spawn_points,
        "sky": sky_info,
        "objects": objects,
        "previews": previews,
        "textures": textures,
        "source_format": "v4_json",
    }


def parse_gbmap(path):
    with open(path, "rb") as f:
        data = f.read()

    stripped = data.lstrip()
    if stripped[:1] == b"{":
        return parse_gbmap_v4(path)

    sep_idx = data.find("§".encode("utf-8"))
    if sep_idx == -1:
        raise ValueError("Unrecognized format: no '§' section separator found")
    after_sep = data[sep_idx + len("§".encode("utf-8")):]
    line_ending = b"\r\n" if after_sep[:2] == b"\r\n" else b"\n"
    SEP_DYNAMIC = "§".encode("utf-8") + line_ending

    sections = data.split(SEP_DYNAMIC)
    if len(sections) < 7:
        raise ValueError(f"Unrecognized format: expected >=7 sections, found {len(sections)}")

    def split_lines(section_bytes):
        return [x for x in section_bytes.decode("utf-8", errors="ignore").split(line_ending.decode("utf-8")) if x]

    header = split_lines(sections[0])
    meta = split_lines(sections[1])
    sky = split_lines(sections[2])

    map_name = header[1] if len(header) > 1 else "unknown"
    description = header[2] if len(header) > 2 else ""

    FIELDS_PER_OBJECT = 15

    num_objects = int(meta[0]) if len(meta) > 0 else None
    fields_per_object = FIELDS_PER_OBJECT
    date = meta[2] if len(meta) > 2 else ""

    spawn_entries = meta[3:]
    spawn_points = []
    for i in range(0, len(spawn_entries) - 5, 6):
        chunk = spawn_entries[i:i + 6]
        if len(chunk) < 6:
            break
        spawn_points.append({
            "position": {"x": to_float(chunk[0]), "y": to_float(chunk[1]), "z": to_float(chunk[2])},
            "rotation": {"x": to_float(chunk[3]), "y": to_float(chunk[4]), "z": to_float(chunk[5])},
        })

    if spawn_points:
        spawn_pos = spawn_points[0]["position"]
        spawn_rot = spawn_points[0]["rotation"]
    else:
        spawn_pos = {"x": 0.0, "y": 0.0, "z": 0.0}
        spawn_rot = {"x": 0.0, "y": 0.0, "z": 0.0}

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
    lines = split_lines(sections[6])

    objects = []
    for i in range(0, len(lines), fields_per_object):
        chunk = lines[i:i + fields_per_object]
        if len(chunk) < fields_per_object:
            break
        obj = {
            "material": chunk[0],
            "tileMode": chunk[1],
            "visible": chunk[2] == "True",
            "collisions": chunk[3] == "True",
            "physics": chunk[4] == "True",
            "texture": chunk[5],
            "position": {"x": to_float(chunk[6]), "y": to_float(chunk[7]), "z": to_float(chunk[8])},
            "rotation": {"x": to_float(chunk[9]), "y": to_float(chunk[10]), "z": to_float(chunk[11])},
            "scale": {"x": to_float(chunk[12]), "y": to_float(chunk[13]), "z": to_float(chunk[14])},
        }
        objects.append(obj)
    previews = []
    for idx in (3, 4):
        try:
            png_bytes = _decimal_lines_to_bytes(sections[idx].split(line_ending))
            previews.append((f"preview_{idx}.png", png_bytes))
        except Exception:
            pass

    textures = _extract_named_textures(sections[5], line_ending)

    return {
        "map_name": map_name,
        "description": description,
        "date": date,
        "num_objects": num_objects,
        "spawn_pos": spawn_pos,
        "spawn_rot": spawn_rot,
        "spawn_points": spawn_points,
        "sky": sky_info,
        "objects": objects,
        "previews": previews,
        "textures": textures,
        "source_format": "v1_binary",
    }


def _decimal_lines_to_bytes(lines_list):
    nums = [int(x) for x in lines_list if x not in (b"", b"~")]
    b = bytes(nums)
    iend = b.rfind(b"IEND")
    if iend != -1:
        b = b[:iend + 8]
    return b


def _extract_named_textures(section_bytes, line_ending=b"\r\n"):
    lines = section_bytes.split(line_ending)

    def is_png_start(i):
        return lines[i:i + 8] == PNG_SIG_LINES

    starts = []
    i = 0
    while i < len(lines) - 8:
        if is_png_start(i):
            starts.append(i)
            i += 8
        else:
            i += 1

    results = []
    for idx, s in enumerate(starts):
        name_idx = s - 1
        name = lines[name_idx].decode("utf-8", errors="ignore") if name_idx >= 0 else f"texture_{idx}"
        end_line = starts[idx + 1] - 2 if idx + 1 < len(starts) else len(lines)
        region = lines[s:end_line]
        try:
            png_bytes = _decimal_lines_to_bytes(region)
        except ValueError:
            continue
        results.append((name, png_bytes))
    return results


def build_v4_project(map_data, outdir):
    os.makedirs(outdir, exist_ok=True)
    tex_dir = os.path.join(outdir, "CustomTextures")
    os.makedirs(tex_dir, exist_ok=True)

    project_file = {
        "version": 4,
        "name": map_data["map_name"],
        "description": map_data["description"],
        "lastModified": map_data["date"],
        "selectedAmbience": map_data["sky"]["skyboxIndex"],
        "spawnPoints": [
            {
                "position": map_data["spawn_pos"],
                "rotation": map_data["spawn_rot"],
            }
        ],
        "skySettings": map_data["sky"],
    }

    cubes = []
    for obj in map_data["objects"]:
        cubes.append({
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
        })
    map_json = {"version": 4, "cubes": cubes}

    with open(os.path.join(outdir, "ProjectFile.json"), "w", encoding="utf-8") as f:
        json.dump(project_file, f, indent=4, ensure_ascii=False)

    with open(os.path.join(outdir, "MapData.json"), "w", encoding="utf-8") as f:
        json.dump(map_json, f, indent=2, ensure_ascii=False)

    for name, png_bytes in map_data["textures"]:
        with open(os.path.join(tex_dir, f"{name}.png"), "wb") as f:
            f.write(png_bytes)

    preview_list = list(map_data["previews"])
    if len(preview_list) >= 2:
        icon_name, icon_bytes = preview_list[0]
        banner_name, banner_bytes = preview_list[1]
        with open(os.path.join(outdir, "Icon.png"), "wb") as f:
            f.write(icon_bytes)
        with open(os.path.join(outdir, "Banner.png"), "wb") as f:
            f.write(banner_bytes)
    elif len(preview_list) == 1:
        with open(os.path.join(outdir, "Icon.png"), "wb") as f:
            f.write(preview_list[0][1])

    print(f"[+] Project written to: {outdir}")


def print_summary(map_data):
    print(f"[*] Map:      {map_data['map_name']}")
    print(f"[*] Format:   {map_data.get('source_format', 'unknown')}")
    print(f"[*] Objects:  {len(map_data['objects'])}")
    print(f"[*] Textures: {len(map_data['textures'])}")
    print(f"[*] Previews: {len(map_data['previews'])}")
    print(f"[*] Spawn:    {map_data['spawn_pos']['x']:.2f}, "
          f"{map_data['spawn_pos']['y']:.2f}, {map_data['spawn_pos']['z']:.2f}")


def main():
    parser = argparse.ArgumentParser(description="GoreBox map -> V2 project converter (V1 folder / V2 .gbmap)")
    parser.add_argument("input_path", help=".gbmap file (V2) or V1 project folder (containing projectFile.gbi)")
    parser.add_argument("--outdir", default=None, help="output folder (default: <name>_project next to input)")
    args = parser.parse_args()

    is_dir = os.path.isdir(args.input_path)
    is_file = os.path.isfile(args.input_path)

    if not is_dir and not is_file:
        print(f"[!] Path not found: {args.input_path}")
        sys.exit(1)

    if is_dir:
        print(f"[*] Reading V1 project: {args.input_path}")
        map_data = parse_gbmap_v1_folder(args.input_path)
        base = os.path.basename(os.path.normpath(args.input_path))
        src_dir = os.path.dirname(os.path.abspath(args.input_path))
    else:
        print(f"[*] Reading file: {args.input_path}")
        map_data = parse_gbmap(args.input_path)
        base = os.path.splitext(os.path.basename(args.input_path))[0]
        src_dir = os.path.dirname(os.path.abspath(args.input_path))

    outdir = args.outdir
    if outdir is None:
        preferred = os.path.join(src_dir, f"{base}_project")
        try:
            os.makedirs(preferred, exist_ok=True)
            outdir = preferred
        except OSError:
            outdir = os.path.join(os.getcwd(), f"{base}_project")
            print(f"[!] No write access to source folder, using: {outdir}")

    print_summary(map_data)
    build_v4_project(map_data, outdir)


if __name__ == "__main__":
    main()