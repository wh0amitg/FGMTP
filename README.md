# FGMTP
### From GBMAP To Project

> **DISCLAIMER:** This map decompiler is NOT intended for copying other players' maps. If you upload a map fork/copy to the mod.io workshop, prepare to receive a permanent ban from the workshop for copyright infringement! This tool was and will be created for entertainment purposes only.

---

A lightweight Python CLI tool to decompile and convert **GoreBox** map files (`.gbmap`) into structured project files.

## Features

- **Multi-format support:** Parses both `.gbmap` formats — the legacy binary format (V1, `§`-delimited sections) and the modern JSON format (V2, `mapCubes` + base64 assets). Format is detected automatically, no flags needed.
- **Data extraction:** Extracts map metadata, sky/fog settings, spawn point, and full object data (materials, collision, physics, position, rotation, scale).
- **Asset dumping:** Automatically exports custom textures, map icon, and banner to `.png`.
- **Zero dependencies:** Uses standard Python libraries only (`sys`, `os`, `argparse`, `json`, `base64`).

---

## Usage

Just run the script with Python pointing to your `.gbmap` file:

```bash
python fgmtp.py <path_to_gbmap>
```

Optional custom output folder:

```bash
python fgmtp.py <path_to_gbmap> --outdir <folder>
```

By default, the output is written next to the input file as `<map_name>_project/`.

## Output

```
<map_name>_project/
├── ProjectFile.json    # name, description, spawn point, sky settings
├── MapData.json        # all map objects (cubes)
├── CustomTextures/      # extracted custom textures
├── Icon.png             # map icon (if present)
└── Banner.png           # map banner (if present)
```

Drop the resulting folder into `MapProjects` and open it in the map editor.

## Example

```
$ python fgmtp.py Map.gbmap
[*] Reading: Map.gbmap
[*] Map:      Testing Map
[*] Format:   V1
[*] Objects:  1017
[*] Textures: 33
[*] Previews: 2
[*] Spawn:    -18.61, -4.40, 48.94
[+] Project written to: Map_project
```
