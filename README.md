[![CI](https://img.shields.io/github/actions/workflow/status/ExoticArts/comfyui-ea-nodes/ci.yml?branch=main&label=CI)](https://github.com/ExoticArts/comfyui-ea-nodes/actions/workflows/ci.yml)

# ComfyUI EA Nodes

Compact, user-friendly **LoRA stacking** nodes for ComfyUI. Designed to work cleanly with **WAN 2.2** (no CLIP path) and with **SD/SDXL** (model + CLIP).

---

## Nodes

### EA Power LoRA

Apply one or more LoRAs to the **MODEL only** (no CLIP path).

**Use this when:** your pipeline has no text-encoder/CLIP path (e.g., **WAN 2.2**).

**Wiring**

```
[Model Loader] → (model) → [EA Power LoRA] → (model) → […]
```

---

### EA Power LoRA +CLIP

Apply one or more LoRAs to **MODEL** and, optionally, **CLIP**. Includes a **global “Apply to CLIP”** toggle at the top.

**Use this when:** your pipeline includes a text encoder (e.g., **SD/SDXL**).

**Wiring**

```
[Checkpoint Loader] → (model, clip) → [EA Power LoRA +CLIP] → (model, clip) → […]
```

**Apply to CLIP**

* **On:** each row’s **CLIP** strength is used.
* **Off:** CLIP strengths are ignored (model-only behavior), but the CLIP socket stays wired for convenience.

---

## UI at a Glance

* **＋ Add LoRA**: add a row.
* **On**: enable/disable a row.
* **LoRA**: dropdown of files in `/models/loras` (falls back to text if the list can’t be fetched).
* **Model**: UNet/model strength (0.0–2.0).
* **CLIP** (only in +CLIP): text-encoder strength (hidden when “Apply to CLIP” is off).
* **✕ Remove**: delete the row.

Rows are top-aligned with a small gap between entries for readability.

---

## Notes & Tips

* **Which node to choose:**

  * **WAN 2.2:** use **EA Power LoRA** (no CLIP path to patch).
  * **SD/SDXL:** use **EA Power LoRA +CLIP** and tune the global toggle + per-row strengths.
* **LoRA order:** runtime LoRA application is a linear sum of deltas; **order does not change the result**.
* **Trigger words:** they act through the text encoder; some LoRAs (character/concept) benefit from CLIP strength, while many style LoRAs work fine with CLIP low or off.
* **Missing files:** unknown LoRA names are safely ignored.

---

## Install

**Comfy Manager / Registry:** search `comfyui-ea-nodes` and install.
**Manual:**

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/ExoticArts/comfyui-ea-nodes
# Restart ComfyUI and hard refresh the browser (Ctrl/Cmd+Shift+R)
```

---

## License

See [LICENSE](LICENSE).
