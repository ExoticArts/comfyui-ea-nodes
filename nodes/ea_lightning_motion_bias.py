# EA Motion Bias (Lightning) with Presets + CFG hints
# One dial → steps/split/sigmas + Lightning weights + add-noise hints.
# Import-safe (no heavy deps at import time).

from typing import List, Tuple

def _clamp(x, lo, hi): return lo if x < lo else hi if x > hi else x
def _lerp(a: float, b: float, t: float): return a + (b - a) * t
def _round5(x: float) -> float: return float(f"{x:.5f}")

def _strictly_decreasing(vals: List[float]) -> List[float]:
    out, prev = [], 10.0
    for v in vals:
        v = min(v, prev - 1e-6); out.append(v); prev = v
    return out

def _sigmas_hold_high(steps: int, bias: float) -> List[float]:
    p = _lerp(1.1, 3.0, _clamp(bias, 0.0, 1.0))
    vals = []
    for i in range(steps):
        t = i / float(steps); vals.append(1.0 - (t ** p))
    vals.append(0.0)
    vals = _strictly_decreasing(vals)
    vals[0], vals[-1] = 1.0, 0.0
    return [_round5(v) for v in vals]

def _sigmas_big_drop(steps: int, bias: float) -> List[float]:
    q = _lerp(0.8, 1.4, _clamp(bias, 0.0, 1.0))
    vals = []
    for i in range(steps):
        t = i / float(steps); vals.append((1.0 - t) ** q)
    vals.append(0.0)
    vals = _strictly_decreasing(vals)
    vals[0], vals[-1] = 1.0, 0.0
    return [_round5(v) for v in vals]

# Presets: exact outputs (independent of Custom controls)
_PRESETS = {
    # Stock Lightning workflow defaults: Euler, 4 steps, 2/2 split, CFG 1/1, LoRA 1/1, no extra noise
    "Lightning Default 2/2": {
        "steps": 4,
        "split_step": 2,
        "sigmas": [1.0, 0.9375, 0.83333, 0.625, 0.0],
        "high_weight": 1.0,
        "low_weight": 1.0,
        "cfg_high": 1.0,
        "cfg_low": 1.0,
        "add_noise_high": False,
        "add_noise_low": False,
        "scheduler_hint": "euler",
    },

    # Your “B” preset
    "Aggressive 3/2": {
        "steps": 5,
        "split_step": 3,
        "sigmas": [1.0, 0.95, 0.85, 0.70, 0.55, 0.0],
        "high_weight": 1.25,
        "low_weight": 1.00,
        "cfg_high": 0.80,
        "cfg_low": 1.00,
        "add_noise_high": True,
        "add_noise_low": False,
        "scheduler_hint": "dpm++_sde",
    },

    "Balanced 3/2": {
        "steps": 5,
        "split_step": 3,
        "sigmas": [1.0, 0.97, 0.92, 0.78, 0.60, 0.0],
        "high_weight": 1.22,
        "low_weight": 1.05,
        "cfg_high": 0.85,
        "cfg_low": 1.02,
        "add_noise_high": True,
        "add_noise_low": False,
        "scheduler_hint": "dpm++_sde/beta",
    },

    "Speedrun 4/1": {
        "steps": 5,
        "split_step": 4,
        "sigmas": [1.0, 0.94, 0.80, 0.64, 0.50, 0.0],
        "high_weight": 1.28,
        "low_weight": 0.95,
        "cfg_high": 0.78,
        "cfg_low": 0.98,
        "add_noise_high": True,
        "add_noise_low": False,
        "scheduler_hint": "dpm++_sde",
    },

    "Detail 6/2": {
        "steps": 6,
        "split_step": 4,
        "sigmas": [1.0, 0.97, 0.93, 0.80, 0.62, 0.50, 0.0],
        "high_weight": 1.20,
        "low_weight": 1.08,
        "cfg_high": 0.85,
        "cfg_low": 1.05,
        "add_noise_high": True,
        "add_noise_low": False,
        "scheduler_hint": "dpm++_sde/beta",
    },
}

def _noise_hints(bias: float) -> Tuple[bool, bool]:
    b = _clamp(bias, 0.0, 1.0)
    return (b >= 0.65, False)

def _choose_scheduler(bias: float, profile: str) -> str:
    b = _clamp(bias, 0.0, 1.0)
    if b < 0.55:
        return "euler/beta"
    if b < 0.75:
        return "dpm++_sde/beta" if profile == "hold_high" else "dpm++_sde"
    return "dpm++_sde"

class EA_LightningMotionBias:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # Default remains Aggressive 3/2
                "preset": (["Aggressive 3/2", "Balanced 3/2", "Speedrun 4/1", "Detail 6/2", "Lightning Default 2/2", "Custom"], {"default": "Aggressive 3/2"}),
                # Custom controls (ignored when preset != Custom)
                "steps": ("INT", {"default": 5, "min": 3, "max": 12}),
                "motion_bias": ("FLOAT", {"default": 0.80, "min": 0.0, "max": 1.0, "step": 0.01}),
                "profile": (["hold_high", "big_drop"], {"default": "big_drop"}),
                # Bases chosen so Custom @ bias=0.8 lands near 1.25/1.00
                "base_high": ("FLOAT", {"default": 1.04, "min": 0.0, "max": 2.0, "step": 0.01}),
                "base_low":  ("FLOAT", {"default": 1.14, "min": 0.0, "max": 2.0, "step": 0.01}),
            },
            "optional": {
                "min_low_steps": ("INT", {"default": 2, "min": 1, "max": 4}),
            },
        }

    RETURN_TYPES = ("INT","INT","STRING","FLOAT","FLOAT","BOOLEAN","BOOLEAN","FLOAT","FLOAT","STRING")
    RETURN_NAMES  = ("steps","split_step","sigmas_str","lightning_high_weight","lightning_low_weight","add_noise_high","add_noise_low","cfg_high","cfg_low","scheduler_hint")
    CATEGORY = "EA / Schedules"
    FUNCTION = "compute"

    @staticmethod
    def compute(preset: str, steps: int, motion_bias: float, profile: str, base_high: float, base_low: float, min_low_steps: int = 2):
        # Preset path: emit exact values
        if preset in _PRESETS and preset != "Custom":
            cfg = _PRESETS[preset]
            sigmas_str = ", ".join(f"{float(v):.5f}".rstrip("0").rstrip(".") for v in cfg["sigmas"])
            return (
                int(cfg["steps"]),
                int(cfg["split_step"]),
                sigmas_str,
                float(cfg["high_weight"]),
                float(cfg["low_weight"]),
                bool(cfg["add_noise_high"]),
                bool(cfg["add_noise_low"]),
                float(cfg["cfg_high"]),
                float(cfg["cfg_low"]),
                str(cfg["scheduler_hint"]),
            )

        # Custom path
        steps = int(max(3, steps))
        bias = float(_clamp(motion_bias, 0.0, 1.0))
        min_low_steps = int(_clamp(min_low_steps, 1, max(1, steps - 1)))

        split_f = 0.5 + 0.2 * bias
        split_step = int(round(steps * split_f))
        split_step = max(1, min(split_step, steps - min_low_steps))

        sigmas = _sigmas_big_drop(steps, bias) if profile == "big_drop" else _sigmas_hold_high(steps, bias)
        sigmas_str = ", ".join(f"{v:.5f}".rstrip("0").rstrip(".") for v in sigmas)

        high_weight = _round5(base_high * (1.0 + 0.25 * bias))
        low_weight  = _round5(base_low  * (1.0 - 0.15 * bias))

        # Extra outputs to match presets
        cfg_high = max(0.75, min(1.0, 1.0 - 0.25 * bias))
        cfg_low  = max(1.0, min(1.1, 1.0 + 0.05 * bias))
        scheduler_hint = _choose_scheduler(bias, profile)

        add_noise_high, add_noise_low = _noise_hints(bias)

        return (
            int(steps),
            int(split_step),
            sigmas_str,
            float(high_weight),
            float(low_weight),
            bool(add_noise_high),
            bool(add_noise_low),
            float(_round5(cfg_high)),
            float(_round5(cfg_low)),
            str(scheduler_hint),
        )

NODE_CLASS_MAPPINGS = {"EA_LightningMotionBias": EA_LightningMotionBias}
NODE_DISPLAY_NAME_MAPPINGS = {"EA_LightningMotionBias": "EA Motion Bias (Lightning)"}
