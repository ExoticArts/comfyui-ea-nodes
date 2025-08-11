# ea_auto_trim.py
#
# EA Auto Trim (PingPong-friendly)
# - Finds start/end cut points via a smoothed frame-difference curve.
# - Side-specific trimming (trim_start / trim_end).
# - Hard lower-bounds for trimming: min_skip_first / min_skip_last.
# - Debug chart (green=start, red=end).
# - Preview strip that ALWAYS includes boundaries (first & last frames).
#
# Notes (quick reference):
#   metric_size     : Downscale for motion metric (32–96 common; default 64).
#   smooth          : Moving-average window over motion curve (3–7 typical).
#   warmup_guard    : Ignore this many initial diffs so index 0 can’t auto-win.
#   search_first_pct: Start-valley search window (fraction of curve from left).
#   search_last_pct : End-valley search lower bound (fraction from left).
#   warmup_rel      : Early-motion threshold relative to later median (≈1.2).
#   min_keep        : Minimum frames to keep after choosing a span.
#   min_skip_first  : Always trim at least this many frames from the head.
#   min_skip_last   : Always trim at least this many frames from the tail.
#   emit_preview    : If true, emit a boundary-inclusive preview strip.
#   preview_tiles   : How many tiles in the preview strip (0 = disable).
#
# Import-safe: no torch at module import time.

class EA_AutoTrimPingPong:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
            },
            "optional": {
                # Motion metric / search params
                "metric_size": ("INT", {"default": 64, "min": 16, "max": 256, "step": 16}),
                "smooth": ("INT", {"default": 5, "min": 1, "max": 31, "step": 2}),
                "warmup_guard": ("INT", {"default": 6, "min": 0, "max": 120, "step": 1}),
                "search_first_pct": ("FLOAT", {"default": 0.25, "min": 0.0, "max": 0.5, "step": 0.01}),
                "search_last_pct": ("FLOAT", {"default": 0.75, "min": 0.5, "max": 1.0, "step": 0.01}),
                "warmup_rel": ("FLOAT", {"default": 1.2, "min": 0.8, "max": 3.0, "step": 0.05}),
                "min_keep": ("INT", {"default": 32, "min": 2, "max": 240, "step": 1}),

                # Side-specific trimming (+ hard lower bounds)
                "trim_start": ("BOOLEAN", {"default": True}),
                "trim_end":   ("BOOLEAN", {"default": True}),
                "min_skip_first": ("INT", {"default": 0, "min": 0, "max": 240, "step": 1}),
                "min_skip_last":  ("INT", {"default": 0, "min": 0, "max": 240, "step": 1}),

                # Debug + preview
                "emit_debug": ("BOOLEAN", {"default": True}),
                "debug_width": ("INT", {"default": 256, "min": 64, "max": 1024, "step": 32}),

                # Boundary-aware strip (no preview_seq)
                "emit_preview": ("BOOLEAN", {"default": False}),
                "preview_tiles": ("INT", {"default": 8, "min": 0, "max": 64, "step": 1}),

                # For ping-pong previews (just affects preview strip sampling of tail/first)
                "dedupe_apex": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "INT", "INT", "INT", "IMAGE", "IMAGE")
    RETURN_NAMES = (
        "images",        # trimmed sequence
        "first_frame",   # convenience preview
        "last_frame",    # convenience preview
        "frame_count",
        "skip_first",
        "skip_last",
        "debug_image",   # tiny curve chart
        "preview_strip", # boundary-inclusive tiles (first..last)
    )
    FUNCTION = "auto_trim"
    CATEGORY = "EA / Video"

    # ----- internals -----
    @staticmethod
    def _smooth1d(x, win: int):
        import torch
        win = int(win)
        if win <= 1:
            return x
        x = x[None, None, :]  # [1,1,T]
        kernel = torch.ones((1,1,win), dtype=x.dtype, device=x.device) / float(win)
        pad = win // 2
        y = torch.nn.functional.pad(x, (pad, pad), mode="replicate")
        y = torch.nn.functional.conv1d(y, kernel)
        return y[0,0,:x.shape[-1]]

    @staticmethod
    def _motion_curve(images, metric_size: int, smooth: int):
        import torch
        import torch.nn.functional as F
        n = int(images.size(0))
        if n <= 1:
            z = images.new_zeros((0,))
            return z, z
        x = images.permute(0,3,1,2)  # [N,C,H,W]
        ms = max(1, int(metric_size))
        if ms > 0:
            x = F.interpolate(x, size=(ms, ms), mode="area")
        # luminance
        w = torch.tensor([0.299, 0.587, 0.114], dtype=x.dtype, device=x.device)[:,None,None]
        g = (x * w).sum(dim=1)  # [N,H,W]
        diff = (g[1:] - g[:-1]).abs().mean(dim=(1,2))  # [N-1]
        sm = EA_AutoTrimPingPong._smooth1d(diff, max(1, int(smooth)))
        return diff, sm

    @staticmethod
    def _local_minimum_idx(curve, lo: int, hi: int, default_idx: int) -> int:
        import torch
        lo = max(0, int(lo)); hi = min(int(hi), curve.numel())
        if hi <= lo:
            return int(default_idx)
        seg = curve[lo:hi]
        j = int(torch.argmin(seg))
        return lo + j

    @staticmethod
    def _debug_chart(sm, start_idx: int, end_idx: int, width: int = 256, height: int = 48):
        """Tiny bar chart image of the smoothed motion curve with start/end markers."""
        import torch
        width  = max(1, int(width))
        height = max(1, int(height))
        T = int(sm.numel())
        if T <= 1:
            return torch.empty((0, 1, 1, 3), dtype=sm.dtype, device=sm.device)
        try:
            smin = float(sm.min().item()); smax = float(sm.max().item())
            rng = (smax - smin) if (smax > smin) else 1.0
            norm = (sm - smin) / rng  # [T]
            xs = torch.linspace(0, T-1, steps=width, device=sm.device)
            idx = torch.clamp(xs.round().long(), 0, T-1)
            vals = norm[idx]  # [W]

            img = torch.ones((height, width, 3), dtype=sm.dtype, device=sm.device) * 0.08
            bar_col = torch.tensor([0.70, 0.72, 0.75], dtype=sm.dtype, device=sm.device)
            for x in range(width):
                h = int(vals[x].item() * (height - 1))
                if h > 0:
                    img[height-1 - h:height-1, x, :] = bar_col

            def ix_to_x(ix):
                if T <= 1: return 0
                return int(round((ix / (T - 1)) * (width - 1)))
            sx = ix_to_x(max(0, int(start_idx)))
            ex = ix_to_x(max(0, int(end_idx)))
            start_col = torch.tensor([0.25, 0.9, 0.25], dtype=sm.dtype, device=sm.device)
            end_col   = torch.tensor([1.0, 0.3, 0.3], dtype=sm.dtype, device=sm.device)
            img[:, sx:sx+1, :] = start_col
            img[:, ex:ex+1, :] = end_col

            return img.unsqueeze(0)  # [1,H,W,3]
        except Exception:
            return torch.empty((0, 1, 1, 3), dtype=sm.dtype, device=sm.device)

    @staticmethod
    def _preview_strip_boundary(frames, tiles: int):
        """Return [1,H,tiles*W,3] with evenly spaced samples from first..last (boundaries included)."""
        import torch
        tiles = int(tiles)
        n = int(frames.size(0))
        if tiles <= 0 or n <= 0:
            return torch.empty((0,1,1,3), dtype=frames.dtype, device=frames.device)
        tiles = min(tiles, n)
        # Evenly spaced indices from 0..n-1 inclusive, count=tiles
        if tiles == 1:
            sel = [0]
        else:
            xs = torch.linspace(0, n-1, steps=tiles, device=frames.device)
            sel = [int(round(v.item())) for v in xs]
        samples = [frames[i] for i in sel]
        strip = torch.cat(samples, dim=1)  # concat along width
        return strip.unsqueeze(0)

    @staticmethod
    def _empty_like(images):
        import torch
        return torch.empty((0, 1, 1, 3), dtype=images.dtype if hasattr(images, "dtype") else torch.float32)

    # ----- main -----
    def auto_trim(
        self,
        images,
        metric_size: int = 64,
        smooth: int = 5,
        warmup_guard: int = 6,
        search_first_pct: float = 0.25,
        search_last_pct: float = 0.75,
        warmup_rel: float = 1.2,
        min_keep: int = 32,
        trim_start: bool = True,
        trim_end: bool = True,
        min_skip_first: int = 0,
        min_skip_last: int = 0,
        emit_debug: bool = True,
        debug_width: int = 256,
        emit_preview: bool = False,
        preview_tiles: int = 8,
        dedupe_apex: bool = True,   # kept for API stability; not used directly here
    ):
        import torch

        # Defensive clamps
        metric_size    = max(1, int(metric_size))
        smooth         = max(1, int(smooth))
        warmup_guard   = max(0, int(warmup_guard))
        search_first_pct = float(search_first_pct)
        search_last_pct  = float(search_last_pct)
        warmup_rel     = float(warmup_rel)
        min_keep       = max(2, int(min_keep))
        min_skip_first = max(0, int(min_skip_first))
        min_skip_last  = max(0, int(min_skip_last))
        debug_width    = max(1, int(debug_width))
        preview_tiles  = max(0, int(preview_tiles))

        if images is None or not torch.is_tensor(images):
            empty = torch.empty((0, 1, 1, 3))
            return (empty, empty, empty, 0, 0, 0, empty, empty)

        N = int(images.size(0))
        if N <= 1:
            first = images[0:0]
            empty = torch.empty((0, 1, 1, 3), dtype=images.dtype, device=images.device)
            return (images, first, first, N, 0, 0, empty, empty)

        # Build motion curve
        diff, sm = self._motion_curve(images, metric_size, smooth)

        # Windows in curve space (T = N-1). Keep them non-degenerate.
        T = max(1, int(diff.numel()))
        first_hi = max(1, int(search_first_pct * T))
        last_lo  = min(T - 1, int(search_last_pct * T))
        # Encourage real search spans (>= 5 samples when possible)
        if first_hi < 5 and T >= 5:
            first_hi = 5
        if T - last_lo < 5 and T >= 5:
            last_lo = max(0, T - 5)

        # Warmup threshold → proposed start default
        if sm.numel() > warmup_guard + 3:
            later_med = torch.median(sm[warmup_guard:])
            thresh = float(later_med) * float(warmup_rel)
            warm_idx = int((sm <= thresh).nonzero(as_tuple=True)[0][0].item()) if (sm <= thresh).any() else 0
        else:
            warm_idx = 0

        # Default valley choices
        start_lo = max(0, min(warm_idx, first_hi - 1))
        start_idx = self._local_minimum_idx(sm, 0, first_hi, default_idx=start_lo)
        end_idx   = self._local_minimum_idx(sm, last_lo, sm.numel(), default_idx=sm.numel()-1)

        # Map diff indices to frame span [S..L]
        S = int(start_idx) if bool(trim_start) else 0
        L = int(end_idx + 1) if bool(trim_end) else (N - 1)

        # Enforce hard lower-bounds on trimming
        if bool(trim_start):
            S = max(S, min_skip_first)
        if bool(trim_end):
            L = min(L, N - 1 - min_skip_last)

        # Enforce min_keep (try to expand symmetrically inside bounds)
        if L - S + 1 < int(min_keep):
            need = int(min_keep) - (L - S + 1)
            take_left  = min(S, need // 2)
            take_right = min(N - 1 - L, need - take_left)
            S = max(0, S - take_left)
            L = min(N - 1, L + take_right)
        if L < S:
            S, L = 0, N - 1

        trimmed = images[S:L+1]
        first_frame = trimmed[0:1] if trimmed.size(0) > 0 else images[0:0]
        last_frame  = trimmed[-1:]  if trimmed.size(0) > 0 else images[0:0]
        frame_count = int(trimmed.size(0))
        skip_first = int(S)
        skip_last  = int(N - 1 - L)

        # Debug chart
        dbg = self._debug_chart(sm, int(start_idx), int(end_idx), width=debug_width, height=48) if bool(emit_debug) else self._empty_like(images)

        # Boundary-inclusive preview strip
        if bool(emit_preview) and int(preview_tiles) > 0 and frame_count > 0:
            strip = self._preview_strip_boundary(trimmed, int(preview_tiles))
        else:
            strip = self._empty_like(images)

        return (
            trimmed, first_frame, last_frame, frame_count, skip_first, skip_last,
            dbg, strip
        )


NODE_CLASS_MAPPINGS = {
    "EA_AutoTrimPingPong": EA_AutoTrimPingPong,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_AutoTrimPingPong": "EA Auto Trim (PingPong)",
}
