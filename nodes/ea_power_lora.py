# nodes/ea_power_lora.py
import json
from typing import List, Tuple, Union


class EA_PowerLora:
    """
    Apply N LoRAs (in order) to a MODEL (and optional CLIP).

    The web UI packs state into the hidden STRING input `loras_json`.

    Supported shapes (for save/backward-compat):

    1) Legacy list of rows:
        [
            {
                "enabled": true,
                "name": "file.safetensors",
                "strength_model": 1.0,
                "strength_clip": 1.0,
                "clip_enabled": true  # per-row (legacy)
            },
            ...
        ]

    2) New object with global toggle + rows:
        {
            "clip_enabled": true,          # global CLIP apply toggle
            "rows": [
                {
                    "enabled": true,
                    "name": "file.safetensors",
                    "strength_model": 1.0,
                    "strength_clip": 1.0
                    # (per-row clip_enabled is optional / ignored if global is false)
                }
            ]
        }

    CI-safe: no heavy imports at module import time.
    """

    @classmethod
    def INPUT_TYPES(cls):
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
    def _parse_payload(raw: str) -> Tuple[bool, List[dict]]:
        """
        Returns (global_clip_enabled, rows)
        Accepts either a list of rows (legacy) or an object with 'rows' + 'clip_enabled'.
        """
        try:
            data: Union[list, dict] = json.loads(raw or "[]")
        except Exception:
            return True, []

        # legacy: a plain list
        if isinstance(data, list):
            return True, data

        # new: object wrapper
        if isinstance(data, dict):
            rows = data.get("rows", [])
            glb = bool(data.get("clip_enabled", True))
            if isinstance(rows, list):
                return glb, rows

        return True, []

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Rerun when json changes; (model/clip) deps handled by Comfy
        return (kwargs.get("loras_json", ""),)

    def apply(self, model, clip=None, loras_json: str = "[]"):
        """
        Thread the model/clip pair through Comfy's core LoraLoader for each row.
        In CI (no Comfy/torch), it's a no-op and returns (model, clip).
        """
        # Lazy imports for CI-safety
        try:
            from nodes import LoraLoader as CoreLoraLoader
        except Exception:
            CoreLoraLoader = None

        try:
            import folder_paths as _folder_paths
        except Exception:
            _folder_paths = None

        global_clip_enabled, rows = self._parse_payload(loras_json)
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

            s_m = float(item.get("strength_model", 1.0))
            s_c = float(item.get("strength_clip", 1.0))

            # Global override takes precedence; legacy per-row respected otherwise
            if not global_clip_enabled or (item.get("clip_enabled") is False):
                s_c = 0.0

            if loader:
                m, c = loader.load_lora(m, c, name, s_m, s_c)
            # else: CI no-op

        return (m, c)


NODE_CLASS_MAPPINGS = {
    "EA_PowerLora": EA_PowerLora,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_PowerLora": "EA Power LoRA",
}
