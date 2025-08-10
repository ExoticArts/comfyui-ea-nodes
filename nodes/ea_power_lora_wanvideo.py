# nodes/ea_power_lora_wanvideo.py
import json

def _safe_float(x, default=0.0):
    try:
        f = float(x)
        if f != f:
            return default
        return f
    except Exception:
        return default


class EA_PowerLora_WanVideo:
    """Build a WANVIDLORA stack from a JSON list of rows using WanVideoWrapper.

    JSON matches EA Power LoRA (non-CLIP):

        { "rows": [
            { "enabled": true, "name": "file.safetensors", "strength_model": 1.0 }
        ]}

    Inputs:
      - prev_lora (WANVIDLORA, optional): existing chain to extend
      - blocks (SELECTEDBLOCKS, optional): block filter from Wan wrapper
      - loras_json (STRING): json payload as above

    Output:
      - lora (WANVIDLORA): connect to WanVideo model loader or Set LoRAs
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
        return (kwargs.get("loras_json", ""),)

    @staticmethod
    def _parse_rows(raw: str):
        try:
            data = json.loads(raw or "{}")
        except Exception:
            return []
        if isinstance(data, dict) and isinstance(data.get("rows"), list):
            return data["rows"]
        return []

    def _import_wan_select(self):
        # Lazy import; works across typical install paths
        candidates = [
            "custom_nodes.ComfyUI_WanVideoWrapper.nodes",
            "ComfyUI_WanVideoWrapper.nodes",
        ]
        last_err = None
        for mod in candidates:
            try:
                m = __import__(mod, fromlist=["WanVideoLoraSelect"])
                return getattr(m, "WanVideoLoraSelect")
            except Exception as e:
                last_err = e
        raise RuntimeError(
            "WanVideoWrapper not found; install/enable ComfyUI-WanVideoWrapper. "
            f"Last error: {last_err}"
        )

    def process(self, loras_json: str = "{}", prev_lora=None, blocks=None):
        rows = self._parse_rows(loras_json)

        # Skip missing files if folder_paths is available
        try:
            import folder_paths as _fp
            available = set(_fp.get_filename_list("loras"))
        except Exception:
            available = None

        WanVideoLoraSelect = self._import_wan_select()

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

            builder = WanVideoLoraSelect()
            # Keep WAN defaults for low_mem_load / merge_loras by not overriding them here
            (acc,) = builder.process(prev_lora=acc, blocks=blocks, lora=name, strength=strength)

        return (acc,)


NODE_CLASS_MAPPINGS = {
    "EA_PowerLora_WanVideo": EA_PowerLora_WanVideo,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_PowerLora_WanVideo": "EA Power LoRA WanVideo",
}
