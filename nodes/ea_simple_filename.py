# EA Filename → Combine (with trigger to avoid caching issues)
import os
import re

class EA_SimpleFilenameCombine:
    """
    Build a ComfyUI-friendly filename prefix and absolute path stub.
    Designed to be import-safe in CI (no ComfyUI/torch at import time).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "subfolder": ("STRING", {"default": "trim/6_belle"}),
                "stem": ("STRING", {"default": "my_video"}),
                "suffix": ("STRING", {"default": "_trim"}),
                "use_video_info": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                # Optional blob to mix into the filename to avoid cache collisions.
                # Typically something like FPS/WH/hash – any string is accepted.
                "video_info": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prefix_for_combine", "fullpath_stub")
    FUNCTION = "combine"
    CATEGORY = "EA / IO"

    @staticmethod
    def _slug(s: str, max_len: int = 64) -> str:
        s = str(s or "").strip()
        s = re.sub(r"\s+", "_", s)                 # whitespace → underscore
        s = re.sub(r"[^a-zA-Z0-9._-]", "", s)     # keep safe chars
        return s[:max_len]

    @staticmethod
    def _clean_subfolder(s: str) -> str:
        s = str(s or "")
        s = s.replace("\\", "/").strip().strip("/")
        # remove parent traversal pieces like ../../
        s = re.sub(r"(\.{2,}/)+", "", s)
        return s

    def combine(self, subfolder: str, stem: str, suffix: str,
                use_video_info: bool = False, video_info: str = ""):
        # Lazy import: present at runtime, absent in CI
        try:
            import folder_paths  # type: ignore
        except Exception:
            folder_paths = None  # CI fallback

        subfolder = self._clean_subfolder(subfolder)
        stem = self._slug(stem, 96)
        suffix = self._slug(suffix, 96)

        token = ""
        if use_video_info and video_info:
            token_slug = self._slug(video_info, 96)
            if token_slug:
                token = f"_{token_slug}"

        basename_no_ext = f"{stem}{suffix}{token}"

        # prefix_for_combine uses POSIX-style separators so SaveImage works cross-platform
        prefix_for_combine = f"{subfolder}/{basename_no_ext}" if subfolder else basename_no_ext
        prefix_for_combine = prefix_for_combine.replace("\\", "/")

        # Resolve absolute output base
        if folder_paths and hasattr(folder_paths, "get_output_directory"):
            out_base = folder_paths.get_output_directory()
        else:
            out_base = os.path.join(os.getcwd(), "output")

        folder_abs = os.path.join(out_base, subfolder) if subfolder else out_base
        fullpath_stub = os.path.join(folder_abs, basename_no_ext)

        return (prefix_for_combine, fullpath_stub)


# Keep the internal ID stable & concise
NODE_CLASS_MAPPINGS = {
    "EA_FilenameCombine": EA_SimpleFilenameCombine,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_FilenameCombine": "EA Filename → Combine",
}
