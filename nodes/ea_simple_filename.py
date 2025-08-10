# EA Filename → Combine (with trigger to avoid caching issues)
import os
import re
import folder_paths


class EA_SimpleFilenameCombine:
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
                "video_info": ("VHS_VIDEOINFO",),
                "ensure_folder": ("BOOLEAN", {"default": True}),
                "delete_numbered_variants": ("BOOLEAN", {"default": True}),
                # Wire FRAME_COUNT here so the node re-runs when the trim changes
                "trigger": ("INT", {"default": 0, "min": 0}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prefix_for_combine", "fullpath_stub")
    CATEGORY = "EA / Video"
    FUNCTION = "build"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # include trigger so deletion runs when trim settings change
        return (
            kwargs.get("subfolder"),
            kwargs.get("stem"),
            kwargs.get("suffix"),
            kwargs.get("use_video_info"),
            kwargs.get("ensure_folder"),
            kwargs.get("delete_numbered_variants"),
            kwargs.get("trigger"),
        )

    def _stem_from_videoinfo(self, video_info):
        try:
            if isinstance(video_info, dict):
                if "filename" in video_info and isinstance(video_info["filename"], str):
                    return os.path.splitext(os.path.basename(video_info["filename"]))[0]
                if "filenames" in video_info and isinstance(video_info["filenames"], (list, tuple)) and video_info["filenames"]:
                    p = video_info["filenames"][0]
                    return os.path.splitext(os.path.basename(p))[0]
        except Exception:
            pass
        return None

    def _delete_variants(self, folder_abs, basename_no_ext):
        if not os.path.isdir(folder_abs):
            return
        pat = re.compile(rf"^{re.escape(basename_no_ext)}_\d+\D*\..+$", re.IGNORECASE)
        try:
            for fname in os.listdir(folder_abs):
                if pat.match(fname):
                    try:
                        os.remove(os.path.join(folder_abs, fname))
                    except Exception:
                        pass
        except Exception:
            pass

    def build(
        self,
        subfolder,
        stem,
        suffix,
        use_video_info=False,
        video_info=None,
        ensure_folder=True,
        delete_numbered_variants=True,
        trigger=0,  # not used directly; forces re-exec when changed
    ):
        # 1) choose stem
        final_stem = stem
        if use_video_info and video_info is not None:
            vi_stem = self._stem_from_videoinfo(video_info)
            if isinstance(vi_stem, str) and vi_stem.strip():
                final_stem = vi_stem

        # 2) paths
        out_root = folder_paths.get_output_directory()
        sub_rel = subfolder.strip("/\\")
        folder_abs = os.path.join(out_root, sub_rel) if sub_rel else out_root

        # 3) ensure folder
        try:
            os.makedirs(folder_abs, exist_ok=True)
        except Exception as e:
            print("[EA FilenameCombine] os.makedirs failed:", folder_abs, e)

        basename_no_ext = f"{final_stem}{suffix}"

        # 4) delete old numbered variants so Combine restarts counter
        if delete_numbered_variants:
            self._delete_variants(folder_abs, basename_no_ext)

        # 5) outputs
        if sub_rel:
            prefix_for_combine = f"{sub_rel}/{basename_no_ext}"
        else:
            prefix_for_combine = basename_no_ext
        prefix_for_combine = prefix_for_combine.replace("\\", "/")

        fullpath_stub = os.path.join(folder_abs, basename_no_ext)
        return (prefix_for_combine, fullpath_stub)


# Keep the internal ID stable & concise
NODE_CLASS_MAPPINGS = {
    "EA_FilenameCombine": EA_SimpleFilenameCombine,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_FilenameCombine": "EA Filename → Combine",
}
