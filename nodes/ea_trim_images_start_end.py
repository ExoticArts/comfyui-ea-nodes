# Trim Images (Start/End + Previews) — now with FRAME_COUNT
import torch

class EA_TrimImagesStartEnd:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "skip_first": ("INT", {"default": 0, "min": 0, "step": 1}),
                "skip_last":  ("INT", {"default": 0, "min": 0, "step": 1}),
            }
        }

    # TRIMMED, FIRST_FRAME, LAST_FRAME, FRAME_COUNT
    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "INT")
    RETURN_NAMES = ("TRIMMED", "FIRST_FRAME", "LAST_FRAME", "FRAME_COUNT")
    FUNCTION = "trim"
    CATEGORY = "EA / Video"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # force re-run when any of these change
        return (kwargs.get("skip_first"), kwargs.get("skip_last"))

    def trim(self, images, skip_first=0, skip_last=0):
        if not isinstance(images, torch.Tensor):
            raise ValueError("images must be a torch.Tensor")

        n = images.size(0)
        start = max(0, min(skip_first, n))
        end   = n - max(0, min(skip_last, max(0, n - start)))

        if end < start:
            end = start

        trimmed = images[start:end]

        # First/last frame previews as 1-image batches (keep IMAGE type)
        if trimmed.size(0) > 0:
            first_frame = trimmed[0:1]
            last_frame  = trimmed[-1: ]
        else:
            # Return empty batches to satisfy type
            c, h, w = images.size(-1), images.size(-2), images.size(-1)
            first_frame = images[0:0]
            last_frame  = images[0:0]

        frame_count = trimmed.size(0)
        return (trimmed, first_frame, last_frame, frame_count)


NODE_CLASS_MAPPINGS = {
    "EA_TrimImagesStartEnd": EA_TrimImagesStartEnd,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_TrimImagesStartEnd": "Trim Images (Start/End + Previews)",
}
