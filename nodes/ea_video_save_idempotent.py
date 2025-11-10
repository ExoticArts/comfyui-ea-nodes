# ea_video_save_idempotent.py
#
# EA Video Save (Idempotent) - Save video with deterministic filename
# - Uses input filename stem to create predictable output filename
# - Overwrites existing file (idempotent - same input = same output)
# - Perfect for iterative parameter tuning workflows

import os
from pathlib import Path

class EA_VideoSaveIdempotent:
    """
    Save video with deterministic filename based on input stem.
    Overwrites existing file - running same workflow produces same output filename.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "input_stem": ("STRING", {"default": ""}),
            },
            "optional": {
                "fps": ("FLOAT", {"default": 16.0, "min": 1.0, "max": 120.0, "step": 0.1}),
                "output_dir": ("STRING", {"default": "pretrain"}),
                "suffix": ("STRING", {"default": ""}),
                "format": (["video/h264-mp4", "video/h265-mp4", "video/vp9-webm"], {"default": "video/h264-mp4"}),
                "crf": ("INT", {"default": 16, "min": 0, "max": 51, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("output_path", "filename", "stem")
    FUNCTION = "save"
    CATEGORY = "EA / Video"
    OUTPUT_NODE = True

    def save(
        self,
        images,
        input_stem: str = "",
        fps: float = 16.0,
        output_dir: str = "pretrain",
        suffix: str = "",
        format: str = "video/h264-mp4",
        crf: int = 16,
    ):
        import torch
        import numpy as np
        import cv2

        # Validate input
        if images is None or not torch.is_tensor(images):
            return ("", "", "")

        frame_count = int(images.size(0))
        if frame_count == 0:
            return ("", "", "")

        # Determine output filename
        if not input_stem or input_stem.strip() == "":
            stem = "video"
        else:
            stem = Path(input_stem).stem  # Strip any extension if provided

        # Add suffix if provided
        if suffix and suffix.strip():
            stem = f"{stem}_{suffix.strip()}"

        # Determine extension based on format
        ext_map = {
            "video/h264-mp4": ".mp4",
            "video/h265-mp4": ".mp4",
            "video/vp9-webm": ".webm",
        }
        ext = ext_map.get(format, ".mp4")

        # Build output path (relative to ComfyUI output directory)
        # ComfyUI will handle the base output directory
        output_subdir = Path(output_dir.strip() or "pretrain")
        filename = f"{stem}{ext}"

        # For VHS compatibility, we need to use ComfyUI's output structure
        # Get ComfyUI output directory
        try:
            import folder_paths
            output_base = folder_paths.get_output_directory()
        except Exception:
            # Fallback if folder_paths not available
            output_base = Path.cwd() / "output"

        full_output_dir = Path(output_base) / output_subdir
        full_output_dir.mkdir(parents=True, exist_ok=True)

        output_path = full_output_dir / filename

        # Convert images to numpy for OpenCV
        frames_np = images.cpu().numpy()
        if frames_np.dtype == np.float32 or frames_np.dtype == np.float64:
            frames_np = (frames_np * 255.0).clip(0, 255).astype(np.uint8)

        # Get video dimensions
        height, width = frames_np.shape[1:3]

        # Determine codec
        codec_map = {
            "video/h264-mp4": "mp4v",  # Use mp4v for broader compatibility
            "video/h265-mp4": "hvc1",
            "video/vp9-webm": "VP90",
        }
        fourcc_str = codec_map.get(format, "mp4v")
        fourcc = cv2.VideoWriter_fourcc(*fourcc_str)

        # Remove existing file to ensure idempotency
        if output_path.exists():
            output_path.unlink()

        # Write video
        writer = cv2.VideoWriter(
            str(output_path),
            fourcc,
            float(fps),
            (width, height),
        )

        if not writer.isOpened():
            # Fallback to default codec
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(
                str(output_path),
                fourcc,
                float(fps),
                (width, height),
            )

        for i in range(frame_count):
            frame = frames_np[i]
            # Convert RGB to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            writer.write(frame_bgr)

        writer.release()

        # Return paths for reference
        relative_path = str(output_subdir / filename)
        return (str(output_path), filename, stem)


NODE_CLASS_MAPPINGS = {
    "EA_VideoSaveIdempotent": EA_VideoSaveIdempotent,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_VideoSaveIdempotent": "EA Video Save (Idempotent)",
}
