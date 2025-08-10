# Root package __init__.py
# Autoload all node modules from ./nodes without requiring 'nodes' to be a Python package.
# IMPORTANT: ComfyUI looks for WEB_DIRECTORY to mount our web assets.
# DO NOT REMOVE WEB_DIRECTORY or its export from __all__ — the web UI will not load without it.

from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path

# --- CRITICAL FOR WEB EXTENSIONS ---
WEB_DIRECTORY = "./web"  # <- ComfyUI scans this. Removing or renaming breaks JS UIs.

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

def _merge(dst: dict, src: dict):
    if not isinstance(src, dict):
        return
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
        # silently keep first value if duplicate during dev

def _load_all():
    base = Path(__file__).parent / "nodes"
    if not base.exists():
        return
    for p in sorted(base.glob("*.py")):
        if p.name.startswith("_"):
            continue
        mod_name = f"ea_nodes.{p.stem}"
        try:
            spec = spec_from_file_location(mod_name, p)
            if spec is None or spec.loader is None:
                raise RuntimeError("no loader")
            mod = module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"[EA Nodes] Skipping nodes.{p.stem}: {e}")
            continue
        _merge(NODE_CLASS_MAPPINGS, getattr(mod, "NODE_CLASS_MAPPINGS", {}))
        _merge(NODE_DISPLAY_NAME_MAPPINGS, getattr(mod, "NODE_DISPLAY_NAME_MAPPINGS", {}))

_load_all()

# --- DO NOT remove WEB_DIRECTORY from exports (see note above) ---
__all__ = ["WEB_DIRECTORY", "NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
