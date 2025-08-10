[![CI](https://img.shields.io/github/actions/workflow/status/ExoticArts/comfyui-ea-nodes/ci.yml?branch=main&label=CI)](https://github.com/ExoticArts/comfyui-ea-nodes/actions/workflows/ci.yml)

# comfyui-ea-nodes (ExoticArts)

Custom nodes for ComfyUI focused on quality-of-life workflows, WAN/Flux-friendly LoRA stacking, and simple IO utilities.

> **Current nodes**
>
> * **EA Power LoRA** (`EA_PowerLora`) — Apply N LoRAs (in order) to a `MODEL` and optional `CLIP`.
> * **Trim Images (Start/End + Previews)** (`EA_TrimImagesStartEnd`) — Trim image sequences and expose first/last-frame previews and count.
> * **EA Filename → Combine** (`EA_FilenameCombine`) — Build safe filename prefixes and absolute path stubs for Save nodes.

---

## Installation

### Comfy Registry (recommended)

1. In **ComfyUI-Manager**, open **Custom Nodes → Registry**.
2. Search for **EA Comfy Nodes** (Publisher: `ExoticArts`) and install.
3. **Restart ComfyUI**.

> If you see “Install Missing Nodes” complaining about `EA_PowerLora`, update ComfyUI-Manager to the latest and/or install via URL as below.

### Manual / via URL

* **Manager → Install via URL:** paste the repo URL.
* **Git:**

  ```bash
  cd ComfyUI/custom_nodes
  git clone https://github.com/ExoticArts/comfyui-ea-nodes
  ```

  Restart ComfyUI.

---

## Nodes

### EA Power LoRA

**ID:** `EA_PowerLora`  •  **Category:** `EA / LoRA`

Apply multiple LoRAs, **in order**, onto a `MODEL` (and **optionally** a `CLIP`). The node ships with a small web UI that lets you add/remove rows and set strengths per LoRA.

**Inputs**

* `model` **(MODEL)** — Required base model.
* `clip` **(CLIP)** — Optional. If present, LoRA **clip** deltas will be applied.
* `loras_json` **(STRING)** — Hidden; the web UI maintains this. Format:

  ```json
  [
    {"name": "example.safetensors", "strength_model": 0.8, "strength_clip": 0.8},
    {"name": "hands_fix.safetensors", "strength_model": 0.6, "strength_clip": 0.0}
  ]
  ```

**Outputs**

* `model` **(MODEL)** — Model with all LoRAs applied.
* `clip` **(CLIP)** — Updated CLIP (or `None` if no CLIP was provided).

**Behavior & notes**

* LoRAs are resolved against the ComfyUI **`/models/loras`** list; unknown names are skipped.
* If your workflow has no CLIP (e.g., **WAN 2.2**), only `strength_model` applies; `strength_clip` is ignored.
* The node re-executes whenever `loras_json` changes.

**Quick usage**

1. Drop **EA Power LoRA** after your **CheckpointLoaderSimple**.
2. Click **＋ Add LoRA**, select a filename from the dropdown, set strengths.
3. Continue into your sampler/vae/decode stack.

**Minimal WAN template**
A ready-to-load blank graph is included:

* `examples/wan/ea_wan_power_lora_blank.json`

It wires: `CheckpointLoaderSimple → EA_PowerLora` and waits for the rest of your pipeline.

---

### Trim Images (Start/End + Previews)

**ID:** `EA_TrimImagesStartEnd`  •  **Category:** `EA / Video`

Trim leading/trailing frames from an image batch **\[N, H, W, C]** and expose **first frame**, **last frame**, and **frame count** for convenient previews and diagnostics.

**Inputs**

* `images` **(IMAGE)** — A batch of images (e.g., from Load Images, VAE decode, or a video frames node).
* `skip_first` **(INT)** — Number of frames to remove from the start (default 0).
* `skip_last` **(INT)** — Number of frames to remove from the end (default 0).

**Outputs**

* `images` **(IMAGE)** — Trimmed sequence.
* `first_frame` **(IMAGE)** — First frame after trimming (shape `[1, H, W, C]`).
* `last_frame` **(IMAGE)** — Last frame after trimming (shape `[1, H, W, C]`).
* `frame_count` **(INT)** — Number of frames remaining.

**Example**

* `LoadImages → EA_TrimImagesStartEnd(skip_first=2, skip_last=2) → SaveAnimatedImage`
* Use `first_frame`/`last_frame` to quickly preview edges with `Preview Image` or a separate save.

---

### EA Filename → Combine

**ID:** `EA_FilenameCombine`  •  **Category:** `EA / IO`

Builds a safe filename prefix (POSIX-style) plus an absolute path **stub** you can feed to save nodes or other IO steps. Helpful when you want reproducible naming for multi-step pipelines.

**Inputs**

* `subfolder` **(STRING)** — e.g., `trim/6_belle`. Will be normalized (no `..`).
* `stem` **(STRING)** — Base name, e.g., `my_video`.
* `suffix` **(STRING)** — Extra piece appended after stem, e.g., `_trim`.
* `use_video_info` **(BOOLEAN)** — Whether to append `video_info`.
* `video_info` **(STRING, optional)** — Extra token (e.g., `fps24_1920x1080`).

**Outputs**

* `prefix_for_combine` **(STRING)** — For `SaveImage.filename_prefix` (e.g., `trim/6_belle/my_video_trim_fps24`).
* `fullpath_stub` **(STRING)** — Absolute path without extension, useful for scripted saver nodes.

**Example**

* `EA_FilenameCombine → SaveImage(filename_prefix)`
* `EA_FilenameCombine → SaveAnimatedImage(filename)` (append extension in that node as needed)

---

## Example Workflows

### 1) WAN + Power LoRA (blank starter)

* `examples/wan/ea_wan_power_lora_blank.json`
* Steps to complete:

  1. Install/point to your WAN checkpoint in **CheckpointLoaderSimple**.
  2. Add your usual conditioning/sampler/vae/decode chain.
  3. In **EA Power LoRA**, add rows and strengths.

### 2) Trim a sequence and save

```
LoadImages → EA_TrimImagesStartEnd(skip_first=8, skip_last=8)
           ↘ first_frame → SaveImage(prefix="debug/edges/first")
             last_frame  → SaveImage(prefix="debug/edges/last")
           → SaveAnimatedImage(filename="output/clip_trimmed.mp4")
```

### 3) Build a stable filename prefix

```
EA_FilenameCombine(subfolder="runs/0420", stem="my_clip", suffix="_trim",
                   use_video_info=true, video_info="fps24_1920x1080")
   → SaveAnimatedImage(filename_prefix)
```

---

## Developer notes

* The nodes are designed to be **import-safe in CI** (no `torch`/Comfy required at import time). Heavy deps are **lazy-imported** inside the node methods.
* A simple validator lives in `tests/validate_ea_nodes.py`.

  * Locally: `python tests/validate_ea_nodes.py`
  * CI: GitHub Action runs on each push.
* Web component for **EA Power LoRA** lives at `web/ea_power_lora.js`. It fetches LoRA filenames from `/object_info` and stores all rows in the hidden `loras_json` widget.

---

## Troubleshooting

* **“Install Missing Nodes can’t find EA\_PowerLora”**

  * Make sure the pack is published in the Comfy Registry, or install via URL.
* **WAN without CLIP**

  * The node works fine; only `strength_model` applies.
* **LoRA not in dropdown**

  * Ensure the file is in `ComfyUI/models/loras` and restart ComfyUI.

---

## License

MIT — see `LICENSE`.
