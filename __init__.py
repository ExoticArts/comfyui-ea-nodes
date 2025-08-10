# comfyui-ea-nodes/__init__.py
# Single entry-point that exposes node mappings from the nodes/ package.

from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# Tell ComfyUI where to find web extensions for this package
WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
