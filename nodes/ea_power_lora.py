# nodes/ea_power_lora.py
import json
from typing import List, Tuple


def _safe_float(x, default=0.0):
    try:
        f = float(x)
        if f != f:  # NaN guard
            return default
        return f
    except Exception:
        return default


# ---------------- EA Power LoRA (no CLIP) ----------------

class EA_PowerLora:
    """
    Apply N LoRAs (in order) to MODEL only (no CLIP path).

    loras_json (canonical v0.2.0 shape):
        {
          "rows": [
            { "enabled": true, "name": "file.safetensors", "strength_model": 1.0 }
          ]
        }
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"model": ("MODEL",)},
            "optional": {"loras_json": ("STRING", {"default": "[]", "multiline": True})},
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    CATEGORY = "EA / LoRA"
    FUNCTION = "apply"

    @staticmethod
    def _parse_rows(raw: str) -> List[dict]:
        try:
            data = json.loads(raw or "{}")
        except Exception:
            return []
        if isinstance(data, dict) and isinstance(data.get("rows"), list):
            return data["rows"]
        return []

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return (kwargs.get("loras_json", ""),)

    def apply(self, model, loras_json: str = "{}"):
        # Lazy imports so CI can import without Comfy/torch
        try:
            from nodes import LoraLoader as CoreLoraLoader
        except Exception:
            CoreLoraLoader = None
        try:
            import folder_paths as _folder_paths
        except Exception:
            _folder_paths = None

        rows = self._parse_rows(loras_json)
        available = set(_folder_paths.get_filename_list("loras")) if _folder_paths else set()

        m = model
        loader = CoreLoraLoader() if CoreLoraLoader else None

        for item in rows:
            if item.get("enabled") is False:
                continue
            name = (item.get("name") or "").strip()
            if not name:
                continue
            if available and name not in available:
                continue
            s_m = _safe_float(item.get("strength_model", 1.0), 1.0)

            if loader:
                # CLIP is None for this node; clip strength irrelevant (0.0)
                m, _ = loader.load_lora(m, None, name, s_m, 0.0)

        return (m,)


# ---------------- EA Power LoRA +CLIP ----------------

class EA_PowerLora_CLIP:
    """
    Apply N LoRAs (in order) to MODEL and optionally CLIP.

    loras_json (canonical v0.2.0 shape):
        {
          "clip_enabled": true,
          "rows": [
            {
              "enabled": true,
              "name": "file.safetensors",
              "strength_model": 1.0,
              "strength_clip": 1.0
            }
          ]
        }
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"model": ("MODEL",)},
            "optional": {
                "clip": ("CLIP",),
                "loras_json": ("STRING", {"default": "{}", "multiline": True}),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("model", "clip")
    CATEGORY = "EA / LoRA"
    FUNCTION = "apply"

    @staticmethod
    def _parse_payload(raw: str) -> Tuple[bool, List[dict]]:
        """Return (global_clip_enabled, rows)."""
        try:
            data = json.loads(raw or "{}")
        except Exception:
            return True, []
        if not isinstance(data, dict):
            return True, []
        clip_enabled = bool(data.get("clip_enabled", True))
        rows = data.get("rows", [])
        return clip_enabled, rows if isinstance(rows, list) else []

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return (kwargs.get("loras_json", ""),)

    def apply(self, model, clip=None, loras_json: str = "{}"):
        try:
            from nodes import LoraLoader as CoreLoraLoader
        except Exception:
            CoreLoraLoader = None
        try:
            import folder_paths as _folder_paths
        except Exception:
            _folder_paths = None

        global_clip, rows = self._parse_payload(loras_json)
        available = set(_folder_paths.get_filename_list("loras")) if _folder_paths else set()

        m, c = model, clip
        loader = CoreLoraLoader() if CoreLoraLoader else None

        for item in rows:
            if item.get("enabled") is False:
                continue
            name = (item.get("name") or "").strip()
            if not name:
                continue
            if available and name not in available:
                continue

            s_m = _safe_float(item.get("strength_model", 1.0), 1.0)
            s_c = _safe_float(item.get("strength_clip", 1.0), 1.0)

            if not global_clip:
                s_c = 0.0

            if loader:
                m, c = loader.load_lora(m, c, name, s_m, s_c)

        return (m, c)


# ---------------- mappings ----------------

NODE_CLASS_MAPPINGS = {
    "EA_PowerLora": EA_PowerLora,
    "EA_PowerLora_CLIP": EA_PowerLora_CLIP,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_PowerLora": "EA Power LoRA",
    "EA_PowerLora_CLIP": "EA Power LoRA +CLIP",
}
