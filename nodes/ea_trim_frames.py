# EA Trim Frames — removes frames from start/end and returns previews + frame count

class EA_TrimFrames:
    """
    Remove frames from the start/end of an image sequence.
    Outputs: (TRIMMED, FIRST_FRAME, LAST_FRAME, FRAME_COUNT)
    Import-safe for CI (no torch at module import time).
    """

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
    RETURN_NAMES = ("images", "first_frame", "last_frame", "frame_count")
    FUNCTION = "trim"
    CATEGORY = "EA / Video"

    def trim(self, images, skip_first: int, skip_last: int):
        # Lazy import torch inside execution so CI can import the module
        import torch  # type: ignore

        # images expected shape: [N, H, W, C]
        if images is None:
            empty = torch.empty((0, 1, 1, 3))
            return (empty, empty, empty, 0)

        if not torch.is_tensor(images):
            raise TypeError("EA_TrimFrames.trim: 'images' must be a torch tensor")

        n = int(images.size(0)) if images.ndim >= 1 else 0
        s = max(0, int(skip_first))
        e = max(0, int(skip_last))

        # Slice indices
        start = min(s, n)
        end = max(0, n - e)
        if end < start:
            end = start

        trimmed = images[start:end]

        # Keep 4D shape [1,H,W,C] for previews
        if trimmed.size(0) > 0:
            first_frame = trimmed[0:1]
            last_frame  = trimmed[-1:]
        else:
            first_frame = images[0:0]
            last_frame  = images[0:0]

        frame_count = int(trimmed.size(0))
        return (trimmed, first_frame, last_frame, frame_count)


NODE_CLASS_MAPPINGS = {
    "EA_TrimFrames": EA_TrimFrames,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_TrimFrames": "EA Trim Frames",
}
