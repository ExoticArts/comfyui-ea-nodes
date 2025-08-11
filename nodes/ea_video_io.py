# ea_video_io.py
from typing import List, Tuple
from pathlib import Path

def _as_str(x) -> str:
    try:
        return str(x)
    except Exception:
        return ""

def _path_parts(p: Path):
    name = p.name
    stem = p.stem
    ext = p.suffix.lower()
    parent = _as_str(p.parent)
    full = _as_str(p)
    return full, name, stem, parent, ext

class EA_VideoLoad:
    """
    Load a video file into an IMAGE tensor and expose filename metadata.
    Import-safe: heavy deps are imported inside .load().

    Outputs:
      images (IMAGE)       -- [N,H,W,3] in 0..1
      fps (FLOAT)
      frame_count (INT)
      width (INT)
      height (INT)
      duration_s (FLOAT)
      fullpath (STRING)
      filename (STRING)
      stem (STRING)
      parent (STRING)
      ext (STRING)
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "every_n": ("INT", {"default": 1, "min": 1, "max": 1000, "step": 1}),
                "max_frames": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "to_float": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("IMAGE","FLOAT","INT","INT","INT","FLOAT","STRING","STRING","STRING","STRING","STRING")
    RETURN_NAMES = ("images","fps","frame_count","width","height","duration_s","fullpath","filename","stem","parent","ext")
    FUNCTION = "load"
    CATEGORY = "EA / Video"

    def _load_cv2(self, path: Path, every_n: int, max_frames: int, to_float: bool):
        import cv2
        import numpy as np
        frames = []
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            return None
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        take = 0
        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if (idx % every_n) == 0:
                # BGR -> RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if to_float:
                    frame = frame.astype(np.float32) / 255.0
                frames.append(frame)
                take += 1
                if max_frames > 0 and take >= max_frames:
                    break
            idx += 1
        cap.release()
        return frames, fps, width, height, total

    def _load_imageio(self, path: Path, every_n: int, max_frames: int, to_float: bool):
        import imageio.v3 as iio
        import numpy as np
        frames = []
        meta_fps = 0.0
        try:
            it = iio.imiter(path)
            for idx, frame in enumerate(it):
                if (idx % every_n) != 0:
                    continue
                if to_float:
                    frame = frame.astype(np.float32) / 255.0
                frames.append(frame)
                if max_frames > 0 and len(frames) >= max_frames:
                    break
        except Exception:
            return None
        if frames:
            h, w = frames[0].shape[:2]
        else:
            h = w = 0
        return frames, float(meta_fps), w, h, len(frames)

    def load(self, path: str, every_n: int = 1, max_frames: int = 0, to_float: bool = True):
        # Lazy torch import to stay CI-safe
        import torch

        if not path:
            empty = torch.empty((0,1,1,3))
            return (empty, 0.0, 0, 0, 0, 0.0, "", "", "", "", "")

        p = Path(path)
        full, name, stem, parent, ext = _path_parts(p)
        if not p.exists():
            empty = torch.empty((0,1,1,3))
            return (empty, 0.0, 0, 0, 0, 0.0, full, name, stem, parent, ext)

        frames = None
        fps = 0.0
        width = height = total = 0

        # Try OpenCV first
        try:
            res = self._load_cv2(p, int(every_n), int(max_frames), bool(to_float))
            if res is not None:
                frames, fps, width, height, total = res
        except Exception:
            frames = None

        # Fallback to imageio if cv2 failed
        if frames is None:
            try:
                res = self._load_imageio(p, int(every_n), int(max_frames), bool(to_float))
                if res is not None:
                    frames, fps, width, height, total = res
            except Exception:
                frames = None

        if not frames:
            empty = torch.empty((0,1,1,3))
            return (empty, 0.0, 0, 0, 0, 0.0, full, name, stem, parent, ext)

        # Stack to torch [N,H,W,3]
        arr = torch.from_numpy(__import__('numpy').stack(frames, axis=0))
        if arr.dtype != torch.float32:
            arr = arr.to(torch.float32) / 255.0
        N, H, W = int(arr.size(0)), int(arr.size(1)), int(arr.size(2))
        duration = float(N / fps) if fps > 0.0 else 0.0
        return (arr, float(fps), int(N), int(W), int(H), float(duration), full, name, stem, parent, ext)

class EA_ListVideos:
    """
    List video files in a directory (optionally recursive) and output a JSON manifest.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"root_dir": ("STRING", {"default": "", "multiline": False})},
            "optional": {
                "patterns": ("STRING", {"default": "*.mp4;*.mov;*.mkv;*.webm;*.avi", "multiline": False}),
                "recursive": ("BOOLEAN", {"default": True}),
                "sort": ("BOOLEAN", {"default": True}),
            }
        }
    RETURN_TYPES = ("STRING","INT")
    RETURN_NAMES  = ("manifest_json","count")
    FUNCTION = "list"
    CATEGORY = "EA / Video"

    def list(self, root_dir: str, patterns: str = "*.mp4;*.mov;*.mkv;*.webm;*.avi", recursive: bool = True, sort: bool = True):
        import json
        p = Path(root_dir or ".")
        pats = [s.strip() for s in (patterns or "").split(";") if s.strip()]
        files: List[str] = []
        if p.exists():
            for pat in pats or ["*.*"]:
                it = p.rglob(pat) if recursive else p.glob(pat)
                for f in it:
                    if f.is_file():
                        files.append(str(f))
        if sort:
            files.sort()
        return (json.dumps(files), len(files))

class EA_ManifestIndex:
    """
    Pick a path from a manifest JSON by index (wraps around). Also returns parts.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "manifest_json": ("STRING", {"default": "[]"}),
                "index": ("INT", {"default": 0, "min": 0, "max": 1_000_000, "step": 1}),
            }
        }
    RETURN_TYPES = ("STRING","STRING","STRING","STRING","STRING")
    RETURN_NAMES = ("fullpath","filename","stem","parent","ext")
    FUNCTION = "pick"
    CATEGORY = "EA / Video"

    def pick(self, manifest_json: str, index: int):
        import json
        try:
            arr = json.loads(manifest_json or "[]")
        except Exception:
            arr = []
        if not isinstance(arr, list) or not arr:
            return ("", "", "", "", "")
        idx = int(index) % len(arr)
        full = str(arr[idx])
        p = Path(full)
        full, name, stem, parent, ext = _path_parts(p)
        return (full, name, stem, parent, ext)

NODE_CLASS_MAPPINGS = {
    "EA_VideoLoad": EA_VideoLoad,
    "EA_ListVideos": EA_ListVideos,
    "EA_ManifestIndex": EA_ManifestIndex,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_VideoLoad": "EA Video Load",
    "EA_ListVideos": "EA List Videos",
    "EA_ManifestIndex": "EA Manifest Pick",
}
