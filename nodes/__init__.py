# nodes/__init__.py

from .ea_trim_images_start_end import EA_TrimImagesStartEnd
from .ea_simple_filename import EA_SimpleFilenameCombine

# Short, stable internal IDs
NODE_CLASS_MAPPINGS = {
    "EA_TrimFrames": EA_TrimImagesStartEnd,
    "EA_FilenameCombine": EA_SimpleFilenameCombine,
}

# Concise display names for the UI header
NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_TrimFrames": "EA Trim Frames",
    "EA_FilenameCombine": "EA Filename → Combine",  # or "EA Filename -> Combine"
}
