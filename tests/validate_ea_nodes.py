#!/usr/bin/env python3
"""
validate_ea_nodes.py
Run from repo root:
  python ./validate_ea_nodes.py
or from tests/:
  python ./tests/validate_ea_nodes.py
"""
from __future__ import annotations
import importlib.util, sys, types
from pathlib import Path

EXPECTED_NODES = {
    "EA_TrimFrames": "EA Trim Frames",
    "EA_FilenameCombine": "EA Filename → Combine",
    "EA_PowerLora": "EA Power LoRA",
    "EA_PowerLora_CLIP": "EA Power LoRA +CLIP",
    "EA_PowerLora_WanVideo": "EA Power LoRA WanVideo",
}

def import_root_init(repo_root: Path):
    root_init = repo_root / "__init__.py"
    if not root_init.exists():
        raise RuntimeError(f"Top-level __init__.py not found at {root_init}")
    spec = importlib.util.spec_from_file_location("ea_nodes_pkg", root_init)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not create spec for top-level __init__.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    here = Path(__file__).resolve()
    repo_root = here.parent if here.parent.name.lower() != "tests" else here.parent.parent
    print(f"[Validator] Importing nodes from {repo_root}")

    # Light mocks for Comfy-only modules
    sys.modules.setdefault("folder_paths", types.SimpleNamespace(
        get_filename_list=lambda kind: [],
        get_temp_directory=lambda: str(repo_root / "_tmp"),
        get_output_directory=lambda: str(repo_root / "_out"),
    ))

    try:
        pkg = import_root_init(repo_root)
    except Exception as e:
        print(f"[FAIL] Could not import nodes package: {e}")
        raise

    cls_map = getattr(pkg, "NODE_CLASS_MAPPINGS", {})
    name_map = getattr(pkg, "NODE_DISPLAY_NAME_MAPPINGS", {})
    print(f"[Info] {len(cls_map)} classes; {len(name_map)} display names")

    ok = True
    for key, expected in EXPECTED_NODES.items():
        if key not in cls_map:
            print(f"[FAIL] missing class: {key}"); ok = False
        else:
            print(f"[PASS] found class: {key}")
        actual_display = name_map.get(key)
        if actual_display != expected:
            print(f"[FAIL] display mismatch for {key}: '{actual_display}' != '{expected}'"); ok = False
        else:
            print(f"[PASS] display for {key}: '{expected}'")

    # Ensure we can instantiate without heavy deps
    for key, cls in cls_map.items():
        try:
            _ = cls()
            print(f"[PASS] instantiate: {key}")
        except Exception as e:
            print(f"[FAIL] instantiate {key}: {e}"); ok = False

    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
