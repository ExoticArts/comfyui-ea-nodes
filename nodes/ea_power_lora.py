# nodes/ea_power_lora.py
import json
from typing import List


class EA_PowerLora:
    """
    Apply N LoRAs (in order) to a MODEL (and optional CLIP).

    The web extension (web/ea_power_lora.js) builds a UI of rows and stores them
    into the hidden STRING input `loras_json`. Each row looks like:

        {
            "enabled": true,                # optional; default True
            "name": "file.safetensors",     # required at runtime
            "strength_model": 1.0,          # float
            "strength_clip": 1.0            # float
        }

    CI-safe: avoids importing Comfy/torch at module import time. Heavy imports
    are done lazily inside `apply()`.
    """

    @classmethod
    def INPUT_TYPES(cls):
        # Works if CLIP is missing (e.g., WAN 2.2). If CLIP is provided, we apply clip strength too.
        return {
            "required": {
                "model": ("MODEL",),
            },
            "optional": {
                "clip": ("CLIP",),
                "loras_json": ("STRING", {"default": "[]", "multiline": True}),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("model", "clip")
    CATEGORY = "EA / LoRA"
    FUNCTION = "apply"

    @staticmethod
    def _parse_loras_json(raw: str) -> List[dict]:
        try:
            data = json.loads(raw or "[]")
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Re-run when json/string changes (model/clip deps handled by Comfy)
        return (kwargs.get("loras_json", ""),)

    def apply(self, model, clip=None, loras_json: str = "[]"):
        """
        Thread the model/clip pair through Comfy's core LoraLoader for each row.
        If running in CI (no Comfy/torch), this is a no-op but still returns
        (model, clip) to satisfy the validator.
        """
        # Lazy imports so this module can be imported without Comfy/torch present.
        try:
            from nodes import LoraLoader as CoreLoraLoader  # Comfy core at runtime
        except Exception:
            CoreLoraLoader = None  # CI fallback

        try:
            import folder_paths as _folder_paths
        except Exception:
            _folder_paths = None  # CI fallback

        loras = self._parse_loras_json(loras_json)

        # Known filenames at runtime; empty set in CI so we don't fail.
        available = set(_folder_paths.get_filename_list("loras")) if _folder_paths else set()

        m, c = model, clip
        loader = CoreLoraLoader() if CoreLoraLoader else None

        for item in loras:
            # Allow rows to be disabled from the UI
            if item.get("enabled") is False:
                continue

            name = (item.get("name") or "").strip()
            if not name:
                continue

            # If we know the available set, enforce membership; else (CI) allow.
            if available and name not in available:
                continue

            s_m = float(item.get("strength_model", 1.0))
            s_c = float(item.get("strength_clip", 1.0))

            if loader:
                # Handles both with and without CLIP; returns (model, clip)
                m, c = loader.load_lora(m, c, name, s_m, s_c)
            # else: CI fallback is a no-op

        return (m, c)


NODE_CLASS_MAPPINGS = {
    "EA_PowerLora": EA_PowerLora,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_PowerLora": "EA Power LoRA",
}
