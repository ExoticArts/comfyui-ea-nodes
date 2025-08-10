#!/usr/bin/env python3
"""
validate_ea_nodes.py

Run from repo root:
    python ./tests/validate_ea_nodes.py
"""

import importlib
import sys
from pathlib import Path
import types

# --- CONFIG ---
EXPECTED_NODES = {
    "EA_TrimFrames": "EA Trim Frames",
    "EA_FilenameCombine": "EA Filename → Combine",
    "EA_PowerLora": "EA Power LoRA",           # ⬅️ add this
}
# --------------

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Mock ComfyUI-specific imports so they don't break outside of ComfyUI
sys.modules["folder_paths"] = types.SimpleNamespace(
    get_temp_directory=lambda: str(ROOT / "_temp"),
    get_output_directory=lambda: str(ROOT / "_output"),
)

print(f"[Validator] Checking EA Nodes package at {ROOT}")

try:
    pkg = importlib.import_module("nodes")  # "nodes" is the package folder in repo
except Exception as e:
    print(f"[FAIL] Could not import package 'nodes': {e}")
    sys.exit(1)

try:
    cls_map = pkg.NODE_CLASS_MAPPINGS
    name_map = pkg.NODE_DISPLAY_NAME_MAPPINGS
except AttributeError as e:
    print(f"[FAIL] Package missing expected mappings: {e}")
    sys.exit(1)

# Check for missing node keys
missing = set(EXPECTED_NODES.keys()) - set(cls_map.keys())
if missing:
    print(f"[FAIL] Missing nodes: {missing}")
else:
    print(f"[PASS] All expected node keys found: {list(EXPECTED_NODES.keys())}")

# Check display names
for key, expected_display in EXPECTED_NODES.items():
    actual_display = name_map.get(key)
    if actual_display != expected_display:
        print(f"[FAIL] Display name mismatch for {key}: '{actual_display}' != '{expected_display}'")
    else:
        print(f"[PASS] Display name for {key} is correct: '{actual_display}'")

# Instantiate node classes
for key, cls in cls_map.items():
    try:
        node = cls()
        print(f"[PASS] Instantiated node: {key} ({cls.__name__})")
    except Exception as e:
        print(f"[FAIL] Could not instantiate node {key}: {e}")
