# comfyui-ea-nodes/nodes/__init__.py
# Explicitly import and merge the nodes you ship.

from .ea_trim_images_start_end import (
    NODE_CLASS_MAPPINGS as _TRIM_MAP,
    NODE_DISPLAY_NAME_MAPPINGS as _TRIM_DISP,
)
from .ea_simple_filename import (
    NODE_CLASS_MAPPINGS as _NAME_MAP,
    NODE_DISPLAY_NAME_MAPPINGS as _NAME_DISP,
)

NODE_CLASS_MAPPINGS = {}
NODE_CLASS_MAPPINGS.update(_TRIM_MAP)
NODE_CLASS_MAPPINGS.update(_NAME_MAP)

NODE_DISPLAY_NAME_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS.update(_TRIM_DISP)
NODE_DISPLAY_NAME_MAPPINGS.update(_NAME_DISP)

print(f"[EA Nodes] Loaded {len(NODE_CLASS_MAPPINGS)} node(s) from comfyui-ea-nodes")
