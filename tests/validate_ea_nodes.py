#!/usr/bin/env python3
import importlib, sys, types
from pathlib import Path

EXPECTED_NODES = {
    "EA_TrimFrames": "EA Trim Frames",
    "EA_FilenameCombine": "EA Filename → Combine",
    "EA_PowerLora": "EA Power LoRA",
    "EA_PowerLora_CLIP": "EA Power LoRA +CLIP",
    "EA_PowerLora_WanVideo": "EA Power LoRA WanVideo",
}

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# light mocks for Comfy-specific imports
sys.modules["folder_paths"] = types.SimpleNamespace(
    get_filename_list=lambda kind: [],
    get_temp_directory=lambda: str(ROOT / "_tmp"),
    get_output_directory=lambda: str(ROOT / "_out"),
)

print(f"[Validator] Importing nodes from {ROOT}")
pkg = importlib.import_module("__init__")

cls_map = getattr(pkg, "NODE_CLASS_MAPPINGS", {})
name_map = getattr(pkg, "NODE_DISPLAY_NAME_MAPPINGS", {})

print(f"[Info] {len(cls_map)} classes; {len(name_map)} display names")

ok = True
for k, disp in EXPECTED_NODES.items():
    if k not in cls_map:
        print(f"[FAIL] missing class: {k}"); ok = False
    elif name_map.get(k) != disp:
        print(f"[FAIL] display mismatch for {k}: '{name_map.get(k)}' != '{disp}'"); ok = False
    else:
        print(f"[PASS] {k} -> {disp}")

for k, cls in cls_map.items():
    try:
        cls()
        print(f"[PASS] instantiate: {k}")
    except Exception as e:
        print(f"[FAIL] instantiate {k}: {e}"); ok = False

sys.exit(0 if ok else 1)
