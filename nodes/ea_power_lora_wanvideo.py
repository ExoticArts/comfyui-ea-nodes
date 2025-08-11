# nodes/ea_power_lora_wanvideo.py
import json
import sys
import importlib
from typing import Iterable, Optional, Tuple, Dict, Any, List

def _safe_float(x, default=0.0):
    try:
        f = float(x)
        if f != f:
            return default
        return f
    except Exception:
        return default

def _parse_rows(raw: str) -> List[dict]:
    try:
        data = json.loads(raw or "{}")
    except Exception:
        return []
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return data["rows"]
    if isinstance(data, list):
        out = []
        for it in data:
            if isinstance(it, str):
                out.append({"enabled": True, "name": it, "strength_model": 1.0})
            elif isinstance(it, dict):
                out.append({
                    "enabled": it.get("enabled", True) is not False,
                    "name": (it.get("name") or "").strip(),
                    "strength_model": _safe_float(it.get("strength_model", 1.0), 1.0),
                })
        return out
    return []

# -------- robust discovery of the real node class --------

# plausible import paths (minus any dashes; Python can't import those)
_CANDIDATE_MODULES: Tuple[str, ...] = (
    "ComfyUI_WanVideoWrapper.nodes",
    "ComfyUI_WanVideoWrapper",
    "WanVideoWrapper.nodes",
    "WanVideoWrapper",
)

_LORASELECT_HINTS: Tuple[str, ...] = (
    "wanvideoloraselect",
    "wanvideolora_select",
    "wanloraselect",
    "loraselect",
    "lora select",
)

def _iter_node_classes_from_module(mod: Any) -> Iterable[type]:
    """Yield node classes from NODE_CLASS_MAPPINGS on a module and its .nodes child."""
    # Top-level
    mappings = getattr(mod, "NODE_CLASS_MAPPINGS", {})
    if isinstance(mappings, dict):
        for cls in mappings.values():
            if isinstance(cls, type):
                yield cls
    # Nested 'nodes' module
    sub = getattr(mod, "nodes", None)
    if sub is not None:
        mappings = getattr(sub, "NODE_CLASS_MAPPINGS", {})
        if isinstance(mappings, dict):
            for cls in mappings.values():
                if isinstance(cls, type):
                    yield cls

def _looks_like_comfy_node_class(cls: Any) -> bool:
    # Comfy node classes normally have INPUT_TYPES and a process()
    return (
        isinstance(cls, type)
        and hasattr(cls, "INPUT_TYPES")
        and callable(getattr(cls, "INPUT_TYPES"))
        and hasattr(cls, "process")
        and callable(getattr(cls, "process"))
    )

def _score_loraselect_candidate(cls: type) -> int:
    """Higher score means 'more likely' to be the WanVideo LoRA select node."""
    name = getattr(cls, "__name__", "")
    lname = name.lower()
    score = 0
    for h in _LORASELECT_HINTS:
        if h in lname:
            score += 10
    return score

def _find_lora_select_class() -> type:
    # 1) First scan already-loaded modules to avoid import-path guessing
    best: Optional[type] = None
    best_score = -1
    for name, mod in list(sys.modules.items()):
        try:
            for cls in _iter_node_classes_from_module(mod):
                if not _looks_like_comfy_node_class(cls):
                    continue
                s = _score_loraselect_candidate(cls)
                if s > best_score:
                    best, best_score = cls, s
        except Exception:
            pass
    if best is not None and best_score >= 10:  # found something explicitly lora-select-ish
        return best

    # 2) Try importing a few plausible modules, then scan their mappings
    last_err = None
    for path in _CANDIDATE_MODULES:
        try:
            m = importlib.import_module(path)
            for cls in _iter_node_classes_from_module(m):
                if not _looks_like_comfy_node_class(cls):
                    continue
                s = _score_loraselect_candidate(cls)
                if s > best_score:
                    best, best_score = cls, s
            if best is not None:
                return best
        except Exception as e:
            last_err = e

    raise RuntimeError(
        "EA Power LoRA WanVideo: couldn't locate the wrapper's LoRA-select node class. "
        "Make sure ComfyUI-WanVideoWrapper is installed and enabled. "
        f"Last import error: {last_err}"
    )

# ---------------- node ----------------

class EA_PowerLora_WanVideo:
    """
    Stack WanVideo LoRAs by delegating to the wrapper’s own LoRA-select node class.
    Sockets match WanVideo so links are compatible.
    """

    CATEGORY = "EA / LoRA"
    RETURN_TYPES = ("WANVIDLORA",)
    RETURN_NAMES = ("lora",)
    FUNCTION = "process"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "loras_json": ("STRING", {"default": "{}", "multiline": True}),
            },
            "optional": {
                "prev_lora": ("WANVIDLORA",),
                "blocks": ("SELECTEDBLOCKS",),
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return (kwargs.get("loras_json", ""), kwargs.get("blocks", ""))

    def process(self, loras_json: str = "{}", prev_lora=None, blocks=None):
        rows = _parse_rows(loras_json)

        # optional: filter to existing files
        try:
            import folder_paths as _fp
            available = set(_fp.get_filename_list("loras"))
        except Exception:
            available = None

        LoraSelectCls = _find_lora_select_class()
        acc = prev_lora

        for item in rows:
            if item.get("enabled") is False:
                continue
            name = (item.get("name") or "").strip()
            if not name:
                continue
            if available is not None and name not in available:
                continue
            strength = _safe_float(item.get("strength_model", 1.0), 1.0)
            if abs(strength) <= 1e-9:
                continue

            # Instantiate the real Comfy node class and call its process()
            node = LoraSelectCls()
            (acc,) = node.process(prev_lora=acc, blocks=blocks, lora=name, strength=strength)

        return (acc,)


NODE_CLASS_MAPPINGS = {
    "EA_PowerLora_WanVideo": EA_PowerLora_WanVideo,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_PowerLora_WanVideo": "EA Power LoRA WanVideo",
}
