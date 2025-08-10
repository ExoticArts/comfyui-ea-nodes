# nodes/ea_power_lora.py
import json
from typing import List, Tuple

# Comfy built-ins
import folder_paths
import nodes as comfy_nodes  # to reuse core LoraLoader

class EA_PowerLora:
    """
    Apply N LoRAs (in order) to a MODEL (and optional CLIP).
    The list of LoRAs is passed as JSON from the client component (loras_json).
    Each entry: {"name": "<filename.safetensors>", "strength_model": float, "strength_clip": float}
    """

    @classmethod
    def INPUT_TYPES(cls):
        # NOTE:
        #  - The dynamic UI packs rows into the hidden STRING "loras_json"
        #  - Works if CLIP is missing (WAN 2.2). If CLIP is provided, we'll apply clip strength too.
        return {
            "required": {
                "model": ("MODEL",),
            },
            "optional": {
                "clip": ("CLIP",),
                "loras_json": ("STRING", {"default": "[]", "multiline": True}),
            }
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
        # Re-run when json/string changes (or model/clip changes – handled by Comfy)
        return (kwargs.get("loras_json", ""),)

    def apply(self, model, clip=None, loras_json="[]"):
        # Load core LoraLoader for chaining
        core_loader = comfy_nodes.LoraLoader()

        loras = self._parse_loras_json(loras_json)

        # Resolve which lora names are valid
        available = set(folder_paths.get_filename_list("loras"))
        # Example: "example.safetensors" items are returned; we’ll match on those

        m, c = model, clip

        for item in loras:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            if name not in available:
                # ignore unknown names (or you can raise)
                continue

            s_m = float(item.get("strength_model", 1.0))
            s_c = float(item.get("strength_clip", 1.0))

            # Chain through the Comfy core loader; it handles both with/without clip
            # NOTE: If c is None, core_loader.load_lora returns (m, None)
            m, c = core_loader.load_lora(
                m,
                c,
                name,
                s_m,
                s_c
            )

        return (m, c)


NODE_CLASS_MAPPINGS = {
    "EA_PowerLora": EA_PowerLora,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_PowerLora": "EA Power LoRA",
}
