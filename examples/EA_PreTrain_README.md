# EA_PreTrain Workflow - Training Data Curation

**Purpose**: Manual frame-perfect video windowing for LoRA training data preparation.

**When to use**: When you need to select specific moments from videos that showcase the exact composition, poses, or details you want to train.

---

## Workflow Overview

```
Batch Video Loading → Manual Window Selection → Preview & Verification → Save Output
```

### Node Flow

1. **EA_ListVideos** → Scan directory for videos
2. **EA_ManifestIndex** → Select video by index (increment to navigate)
3. **EA_VideoLoad** → Load current video
4. **EA_TrimWindow** → Extract exact frame window
5. **Preview** → Verify selection (first/last frames + animation)
6. **EA_VideoSaveIdempotent** → Save trimmed clip (idempotent, based on input filename)

---

## Key Node: EA_TrimWindow

**New node created specifically for training data curation.**

### Inputs

- **images**: Video tensor from EA_VideoLoad
- **start_frame**: First frame of selection (0-indexed)
- **frame_count**: Number of frames to extract
- **clamp_to_bounds**: Auto-adjust if window exceeds video length (default: true)

### Outputs

- **images**: Trimmed video sequence (exactly frame_count frames)
- **first_frame**: Preview of first frame
- **last_frame**: Preview of last frame
- **frame_count**: Actual frames in output (should match input)
- **start_frame**: Actual start frame used
- **end_frame**: Actual end frame used (inclusive)
- **total_frames**: Total frames in input video

---

## Key Node: EA_VideoSaveIdempotent

**New node created for deterministic, idempotent video saving.**

### Inputs

- **images**: Video tensor to save
- **input_stem**: Filename stem from EA_VideoLoad (e.g., "video_001")
- **fps**: Frame rate (default: 16.0)
- **output_dir**: Output subdirectory (default: "pretrain")
- **suffix**: Optional suffix to add to filename (default: "")
- **format**: Video format (default: "video/h264-mp4")
- **crf**: Compression quality 0-51, lower=better (default: 16)

### Outputs

- **output_path**: Full path to saved file
- **filename**: Just the filename
- **stem**: Filename without extension

### Key Features

✅ **Idempotent**: Same input always produces same output filename
✅ **Overwrites**: Automatically replaces existing file with same name
✅ **Input-based naming**: Uses input video stem for predictable naming
✅ **No auto-numbering**: Unlike VHS_VideoCombine, doesn't add counters

### Example Behavior

```
Input: /path/to/video_001.mp4
Input stem: "video_001"
Suffix: "trimmed"
Output: ComfyUI/output/pretrain/spreadass/video_001_trimmed.mp4

Running again with different start_frame:
→ Overwrites: video_001_trimmed.mp4 (same filename!)
```

This is perfect for iterative tuning - adjust `start_frame` in EA_TrimWindow and rerun, output file always has the same name.

---

## Standard WAN 2.2 Training Parameters

For WAN 2.2 LoRA training (standard EA Forge configuration):

- **Frame count**: 56 frames
- **FPS**: 16 fps
- **Duration**: 3.5 seconds
- **Resolution**: 544×960 (gold standard)

**Configuration in workflow**:
```
EA_TrimWindow:
  start_frame: [adjust to find best moment]
  frame_count: 56
  clamp_to_bounds: true
```

---

## Usage Instructions

### Initial Setup

1. Load `EA_PreTrain.json` in ComfyUI
2. Configure EA_ListVideos:
   - **root_dir**: `/home/exoticarts/ai/io/input/video/training/[project]`
   - **patterns**: `*.mp4;*.mov;*.mkv;*.webm;*.avi`
   - **recursive**: true
   - **sort**: true

### Per-Video Workflow

1. **Navigate to video**:
   - Increment EA_ManifestIndex → index (0, 1, 2, ...)
   - Run workflow to load video

2. **Find best moment**:
   - Adjust EA_TrimWindow → start_frame
   - Preview animation shows selected window
   - Check first/last frame previews for composition

3. **Verify selection**:
   - Output Frame Count shows 56 (for WAN training)
   - Total Input Frames shows source video length
   - Preview Animation loops selected window

4. **Save output**:
   - VHS_VideoCombine → filename_prefix: `pretrain/[project]/clip_`
   - Output saved to ComfyUI/output/pretrain/[project]/

5. **Move to next video**:
   - Increment EA_ManifestIndex → index
   - Repeat process

---

## Tips & Best Practices

### Finding the Best Frame

**For training data quality**:
- Avoid warmup frames (motion blur, poor composition)
- Avoid cooldown frames (motion settling artifacts)
- Look for clean, stable motion that showcases desired features
- Check finger positions, facial expressions, body composition

**Keyboard workflow** (in ComfyUI):
- Use number scrubber on start_frame to seek frame-by-frame
- Preview Animation shows real-time window update
- First/Last Frame previews confirm boundaries

### Frame Count Guidelines

| Duration | FPS | Frame Count | Use Case |
|----------|-----|-------------|----------|
| 3.5s | 16 | 56 | WAN 2.2 standard (default) |
| 2.0s | 16 | 32 | Short motion clips |
| 5.0s | 16 | 80 | Extended sequences |

### Output Organization

**Recommended structure**:
```
ComfyUI/output/
└── pretrain/
    ├── project1/
    │   ├── clip_00001.mp4
    │   ├── clip_00002.mp4
    │   └── ...
    └── project2/
        ├── clip_00001.mp4
        └── ...
```

**Then move to EA Forge dataset structure**:
```bash
# After curation in ComfyUI, move to datasets
mv ~/ai/src/comfyui/output/pretrain/[project]/*.mp4 \
   ~/ai/datasets/[project]/staging/
```

---

## Difference from EA_PostProcess

| Feature | EA_PreTrain | EA_PostProcess |
|---------|-------------|----------------|
| **Purpose** | Training data curation | Content publishing |
| **Selection** | Manual (frame-perfect) | Automatic (motion-based) |
| **Output** | Single trimmed clip | Ping-pong loop |
| **Interpolation** | None | STMFNet 2× |
| **Use case** | Dataset preparation | Social media posts |
| **Control** | High (exact frames) | Low (algorithmic) |

---

## Troubleshooting

### "start_frame exceeds total_frames"
- **Cause**: start_frame >= video length
- **Fix**: Enable clamp_to_bounds or reduce start_frame

### "Output frame count doesn't match expected"
- **Cause**: Window extends past video end
- **Fix**: Enable clamp_to_bounds (auto-adjusts frame_count)

### "Can't find specific moment"
- **Tip**: Use Total Input Frames to understand video length
- **Tip**: Start at frame 0, increment by 10-20 to scan quickly
- **Tip**: Fine-tune with single-frame increments once close

### "Preview Animation not looping smoothly"
- **Expected**: Training clips don't need to loop perfectly
- **Note**: This is training data, not content for posting

---

## Next Steps After Curation

1. **Move clips to staging**:
   ```bash
   mv ~/ai/src/comfyui/output/pretrain/[project]/*.mp4 \
      ~/ai/datasets/[project]/staging/
   ```

2. **Prepare for training** (use EA dataset tools):
   ```bash
   # Convert to training format with captions
   ai-dataset-intake [project]
   ```

3. **Train LoRA**:
   ```bash
   ai-train run [project] high
   ```

---

**Created**: October 26, 2025
**Node**: EA_TrimWindow (new)
**Workflow**: EA_PreTrain.json
