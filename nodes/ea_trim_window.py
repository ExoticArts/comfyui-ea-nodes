# ea_trim_window.py
#
# EA Trim Window - Manual frame-perfect windowing for training data preparation
# - Specify start frame and duration (frame count)
# - Simple, direct trimming without auto-detection
# - Perfect for curating specific moments from videos

class EA_TrimWindow:
    """
    Extract a fixed-size window from a video sequence.
    Specify exact start frame and frame count for precise control.
    Ideal for training data curation where you need specific moments.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "start_frame": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
                "frame_count": ("INT", {"default": 56, "min": 1, "max": 1000, "step": 1}),
            },
            "optional": {
                "clamp_to_bounds": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "INT", "INT", "INT", "INT")
    RETURN_NAMES = (
        "images",           # trimmed window
        "first_frame",      # preview of first frame
        "last_frame",       # preview of last frame
        "frame_count",      # actual frame count in output
        "start_frame",      # actual start frame used
        "end_frame",        # actual end frame used (inclusive)
        "total_frames",     # total frames in input video
    )
    FUNCTION = "trim_window"
    CATEGORY = "EA / Video"

    def trim_window(
        self,
        images,
        start_frame: int = 0,
        frame_count: int = 56,
        clamp_to_bounds: bool = True,
    ):
        import torch

        # Handle empty/invalid input
        if images is None or not torch.is_tensor(images):
            empty = torch.empty((0, 1, 1, 3))
            return (empty, empty, empty, 0, 0, 0, 0)

        total_frames = int(images.size(0))
        if total_frames == 0:
            empty = torch.empty((0, 1, 1, 3), dtype=images.dtype, device=images.device)
            return (empty, empty, empty, 0, 0, 0, 0)

        # Clamp inputs
        start_frame = max(0, int(start_frame))
        frame_count = max(1, int(frame_count))

        if bool(clamp_to_bounds):
            # Ensure start_frame is within bounds
            start_frame = min(start_frame, total_frames - 1)

            # Clamp frame_count to what's available from start_frame
            available = total_frames - start_frame
            frame_count = min(frame_count, available)
        else:
            # Strict mode - error if out of bounds
            if start_frame >= total_frames:
                raise ValueError(
                    f"start_frame ({start_frame}) >= total_frames ({total_frames}). "
                    f"Enable clamp_to_bounds or adjust start_frame."
                )
            available = total_frames - start_frame
            if frame_count > available:
                raise ValueError(
                    f"frame_count ({frame_count}) exceeds available frames ({available}). "
                    f"Enable clamp_to_bounds or reduce frame_count."
                )

        # Calculate end frame (inclusive)
        end_frame = start_frame + frame_count - 1
        end_frame = min(end_frame, total_frames - 1)

        # Extract window (end_frame+1 because slice is exclusive)
        trimmed = images[start_frame:end_frame+1]

        # Extract preview frames
        if trimmed.size(0) > 0:
            first_frame = trimmed[0:1]
            last_frame = trimmed[-1:]
        else:
            first_frame = images[0:0]
            last_frame = images[0:0]

        actual_frame_count = int(trimmed.size(0))

        return (
            trimmed,
            first_frame,
            last_frame,
            actual_frame_count,
            start_frame,
            end_frame,
            total_frames,
        )


NODE_CLASS_MAPPINGS = {
    "EA_TrimWindow": EA_TrimWindow,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_TrimWindow": "EA Trim Window",
}
