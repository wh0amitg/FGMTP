# FGMTP
### From GBMAP To Project

> **DISCLAIMER:** This map decompiler is NOT intended for copying other players' maps. If you upload a map fork/copy to the mod.io workshop, prepare to receive a permanent ban from the workshop for copyright infringement! This tool was and will be created for entertainment purposes only.

---

A lightweight Python CLI tool to decompile and convert **GoreBox** map files (`.gbmap` / legacy formats) into structured project files.

## Features

- **Multi-format support:** Parses modern JSON-based `.gbmap` (v2), binary `.gbmap` formats, and legacy project folders (`projectFile.gbi`).
- **Data extraction:** Extracts map metadata, sky/fog settings, spawn points, and full object data (materials, collision, physics, position, rotation, scale).
- **Asset dumping:** Automatically exports custom textures, map icons, and banners to `.png`.
- **Zero dependencies:** Uses standard Python libraries only (`sys`, `os`, `argparse`, `json`, `base64`).

---

## Usage

Just run the script with Python pointing to your map file or folder:

```bash
python fgmtp.py <path_to_gbmap_or_folder>
```
