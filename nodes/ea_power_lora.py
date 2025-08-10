# nodes/ea_power_lora.py
import json
from typing import List

class EA_PowerLora:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"model": ("MODEL",)},
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
        return (kwargs.get("loras_json", ""),)

    def apply(self, model, clip=None, loras_json="[]"):
        # Lazy imports so CI (no torch/comfy) can still import this module
        try:
            from nodes import LoraLoader as CoreLoraLoader  # Comfy core
        except Exception:
            CoreLoraLoader = None  # CI fallback

        try:
            import folder_paths as _folder_paths
        except Exception:
            _folder_paths = None  # CI fallback

        loras = self._parse_loras_json(loras_json)

        available = set(_folder_paths.get_filename_list("loras")) if _folder_paths else set()

        m, c = model, clip
        loader = CoreLoraLoader() if CoreLoraLoader else None

        for item in loras:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            # If we know the available list, enforce it; otherwise (CI) allow any name.
            if available and name not in available:
                continue

            s_m = float(item.get("strength_model", 1.0))
            s_c = float(item.get("strength_clip", 1.0))

            if loader:
                m, c = loader.load_lora(m, c, name, s_m, s_c)
            # else: CI fallback is a no-op

        return (m, c)


NODE_CLASS_MAPPINGS = {"EA_PowerLora": EA_PowerLora}
NODE_DISPLAY_NAME_MAPPINGS = {"EA_PowerLora": "EA Power LoRA"}
