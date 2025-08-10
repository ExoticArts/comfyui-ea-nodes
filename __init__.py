# comfyui-ea-nodes/__init__.py
# Auto-discover node modules in ./nodes and re-export their mappings.
# Keep node modules CI-safe by deferring heavy imports to runtime.

from importlib import import_module
from pkgutil import iter_modules
from pathlib import Path

# Let ComfyUI load our web extensions
WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}


def _merge(dst: dict, src: dict):
    if not isinstance(src, dict):
        return
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
        else:
            # keep the first; avoids accidental collisions during dev
            pass


def _load_all_nodes():
    base = Path(__file__).parent / "nodes"
    if not base.exists():
        return
    # Discover sibling modules under ./nodes (not packages elsewhere)
    for spec in iter_modules([str(base)]):
        if spec.name.startswith("_"):
            continue
        try:
            # IMPORTANT: relative import so folder name can contain a hyphen
            mod = import_module(f".nodes.{spec.name}", __name__)
        except Exception as e:
            print(f"[EA Nodes] Skipping nodes.{spec.name}: {e}")
            continue

        _merge(NODE_CLASS_MAPPINGS, getattr(mod, "NODE_CLASS_MAPPINGS", {}))
        _merge(NODE_DISPLAY_NAME_MAPPINGS, getattr(mod, "NODE_DISPLAY_NAME_MAPPINGS", {}))


_load_all_nodes()

__all__ = ["WEB_DIRECTORY", "NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
