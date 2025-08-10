# comfyui-ea-nodes/__init__.py
# Auto-discovers nodes from the local "nodes" package and re-exports mappings.
# Keep node modules CI-safe by deferring heavy imports (torch, comfy internals) to runtime.

from importlib import import_module
from pkgutil import iter_modules
from pathlib import Path

# Let ComfyUI know where to find our web extension(s)
WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

def _merge(dst: dict, src: dict, modname: str, attr: str):
    if not isinstance(src, dict):
        return
    for k, v in src.items():
        if k in dst and dst[k] is not v:
            # Keep the first; warn on duplicates so we spot collisions while developing
            print(f"[EA Nodes] Warning: duplicate node key '{k}' from {modname}.{attr}; keeping the first")
            continue
        dst[k] = v

def _load_all_nodes():
    base = Path(__file__).parent / "nodes"
    if not base.exists():
        return
    for spec in iter_modules([str(base)]):
        if spec.name.startswith("_"):  # skip private modules
            continue
        modname = f"{__name__}.nodes.{spec.name}"
        try:
            mod = import_module(modname)
        except Exception as e:
            print(f"[EA Nodes] Skipping {modname}: {e}")
            continue
        _merge(NODE_CLASS_MAPPINGS, getattr(mod, "NODE_CLASS_MAPPINGS", {}), modname, "NODE_CLASS_MAPPINGS")
        _merge(NODE_DISPLAY_NAME_MAPPINGS, getattr(mod, "NODE_DISPLAY_NAME_MAPPINGS", {}), modname, "NODE_DISPLAY_NAME_MAPPINGS")

_load_all_nodes()
