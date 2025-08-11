# ea_pingpong.py
# EA PingPong (lean): build a ping-pong loop with optional holds/cycles.
# Outputs only the full sequence + a boundary-aware preview strip.

class EA_PingPong:
    """
    Build a ping-pong loop from an IMAGE sequence.

    Options:
      cycles       : repeat the ping-pong once built (>=1)
      dedupe_apex  : don't duplicate the turnaround frame
      hold_first   : repeat first frame N times before forward pass
      hold_last    : repeat last frame N times before mirroring
      preview_tiles: 0 disables preview; otherwise tiles K frames evenly
                     from the start..end of the *final* ping-pong result.

    Outputs:
      images        (full ping-pong sequence)
      preview_strip (one IMAGE: tiles across boundaries, first..last)
      frame_count   (INT)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
            },
            "optional": {
                "cycles": ("INT", {"default": 1, "min": 1, "max": 100, "step": 1}),
                "dedupe_apex": ("BOOLEAN", {"default": True}),
                "hold_first": ("INT", {"default": 0, "min": 0, "max": 240, "step": 1}),
                "hold_last": ("INT", {"default": 0, "min": 0, "max": 240, "step": 1}),
                "preview_tiles": ("INT", {"default": 12, "min": 0, "max": 64, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "INT")
    RETURN_NAMES = ("images", "preview_strip", "frame_count")
    FUNCTION = "make"
    CATEGORY = "EA / Video"

    # ---------- helpers ----------
    @staticmethod
    def _pingpong_once(frames, dedupe_apex: bool):
        import torch
        n = int(frames.size(0))
        if n <= 1:
            return frames
        if bool(dedupe_apex) and n > 2:
            tail = frames[1:-1].flip(0)   # exclude first & apex
        elif bool(dedupe_apex) and n == 2:
            tail = frames[0:0]            # nothing to mirror without dupe
        else:
            tail = frames.flip(0)
        return torch.cat([frames, tail], dim=0)

    @staticmethod
    def _preview_strip_boundary(frames, tiles: int):
        import torch
        tiles = int(tiles)
        n = int(frames.size(0))
        if tiles <= 0 or n <= 0:
            return torch.empty((0,1,1,3), dtype=frames.dtype, device=frames.device)
        tiles = min(tiles, n)
        if tiles == 1:
            idx = [0]
        else:
            xs = torch.linspace(0, n - 1, steps=tiles, device=frames.device)
            idx = [int(round(v.item())) for v in xs]
        samples = [frames[i] for i in idx]
        strip = torch.cat(samples, dim=1)  # tile horizontally
        return strip.unsqueeze(0)

    # ---------- main ----------
    def make(self, images, cycles: int = 1, dedupe_apex: bool = True,
             hold_first: int = 0, hold_last: int = 0, preview_tiles: int = 12):
        import torch

        cycles       = max(1, int(cycles))
        hold_first   = max(0, int(hold_first))
        hold_last    = max(0, int(hold_last))
        preview_tiles = max(0, int(preview_tiles))

        if images is None or not torch.is_tensor(images) or images.numel() == 0:
            empty = torch.empty((0,1,1,3))
            return (empty, empty, 0)

        seq = images
        if hold_first > 0:
            seq = torch.cat([seq[0:1].repeat(hold_first, 1, 1, 1), seq], dim=0)
        if hold_last > 0:
            seq = torch.cat([seq, seq[-1:].repeat(hold_last, 1, 1, 1)], dim=0)

        base = self._pingpong_once(seq, bool(dedupe_apex))
        out  = torch.cat([base] * cycles, dim=0)

        strip = self._preview_strip_boundary(out, preview_tiles) if preview_tiles > 0 else \
                torch.empty((0,1,1,3), dtype=out.dtype, device=out.device)

        return (out, strip, int(out.size(0)))


NODE_CLASS_MAPPINGS = {
    "EA_PingPong": EA_PingPong,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_PingPong": "EA PingPong",
}
