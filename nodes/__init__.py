# nodes/__init__.py
# Aggregate all node modules in this folder and expose the two mapping dicts.
# Keep each node module CI-safe (no heavy imports at import time).

from importlib import import_module
from pkgutil import iter_modules
from pathlib import Path

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

def _merge(dst: dict, src: dict):
    if not isinstance(src, dict):
        return
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
        # if duplicate keys appear during dev, first one wins silently

def _load_all():
    base = Path(__file__).parent
    for spec in iter_modules([str(base)]):
        if spec.name.startswith("_"):
            continue
        try:
            # relative import so a hyphen in the parent folder name doesn't matter
            mod = import_module(f".{spec.name}", __name__)
        except Exception as e:
            print(f"[EA Nodes] Skipping nodes.{spec.name}: {e}")
            continue
        _merge(NODE_CLASS_MAPPINGS, getattr(mod, "NODE_CLASS_MAPPINGS", {}))
        _merge(NODE_DISPLAY_NAME_MAPPINGS, getattr(mod, "NODE_DISPLAY_NAME_MAPPINGS", {}))

_load_all()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
