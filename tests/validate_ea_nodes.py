#!/usr/bin/env python3
"""
validate_ea_nodes.py

Run from repo root:
  python ./tests/validate_ea_nodes.py
or from inside tests:
  python validate_ea_nodes.py
"""

from __future__ import annotations
import importlib
import importlib.util
import sys
from pathlib import Path

# ---- What we expect to ship right now ----
EXPECTED_NODES = {
    "EA_TrimFrames": "EA Trim Frames",
    "EA_FilenameCombine": "EA Filename → Combine",
    "EA_PowerLora": "EA Power LoRA",
    "EA_PowerLora_CLIP": "EA Power LoRA +CLIP",
    # Add new ones here when they land, e.g.:
    # "EA_PowerLora_WanVideo": "EA Power LoRA WanVideo",
}

def import_nodes_package(repo_root: Path):
    """
    Import the nodes package whether the repo uses:
      - repo/nodes/__init__.py  -> import 'nodes'
      - repo/__init__.py        -> load file via spec
    """
    nodes_dir = repo_root / "nodes" / "__init__.py"
    root_init = repo_root / "__init__.py"

    if nodes_dir.exists():
        # Package named 'nodes'
        sys.path.insert(0, str(repo_root))
        return importlib.import_module("nodes")

    if root_init.exists():
        # Load the top-level __init__.py as a module
        spec = importlib.util.spec_from_file_location("ea_nodes", root_init)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not create spec for top-level __init__.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    raise RuntimeError(
        "Could not locate nodes package. Expected either 'nodes/__init__.py' "
        "or a top-level '__init__.py' in the repository."
    )

def main():
    here = Path(__file__).resolve()
    repo_root = here.parent
    if repo_root.name.lower() == "tests":
        repo_root = repo_root.parent

    try:
        pkg = import_nodes_package(repo_root)
    except Exception as e:
        print(f"[FAIL] Could not import nodes package: {e}")
        raise

    cls_map = getattr(pkg, "NODE_CLASS_MAPPINGS", {})
    name_map = getattr(pkg, "NODE_DISPLAY_NAME_MAPPINGS", {})

    if not isinstance(cls_map, dict) or not isinstance(name_map, dict):
        print("[FAIL] Mapping dicts missing or wrong type.")
        sys.exit(1)

    print(f"[INFO] Found {len(cls_map)} node classes; {len(name_map)} display names.")

    ok = True
    for key, expected_display in EXPECTED_NODES.items():
        if key not in cls_map:
            print(f"[FAIL] Missing node class: {key}")
            ok = False
        else:
            print(f"[PASS] Found node class: {key}")

        actual_display = name_map.get(key)
        if actual_display != expected_display:
            print(f"[FAIL] Display mismatch for {key}: '{actual_display}' != '{expected_display}'")
            ok = False
        else:
            print(f"[PASS] Display for {key} is correct: '{actual_display}'")

    # Instantiate nodes to ensure they import lazily and don't crash
    for key, cls in cls_map.items():
        try:
            _ = cls()
            print(f"[PASS] Instantiated node: {key}")
        except Exception as e:
            print(f"[FAIL] Could not instantiate {key}: {e}")
            ok = False

    if not ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
