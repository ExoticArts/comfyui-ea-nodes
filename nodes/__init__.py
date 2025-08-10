from .ea_trim_images_start_end import EA_TrimImagesStartEnd
from .ea_simple_filename import EA_SimpleFilenameCombine
from .ea_power_lora import EA_PowerLora  # ⬅️ new

NODE_CLASS_MAPPINGS = {
    "EA_TrimFrames": EA_TrimImagesStartEnd,
    "EA_FilenameCombine": EA_SimpleFilenameCombine,
    "EA_PowerLora": EA_PowerLora,  # ⬅️ new
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EA_TrimFrames": "EA Trim Frames",
    "EA_FilenameCombine": "EA Filename → Combine",
    "EA_PowerLora": "EA Power LoRA",  # ⬅️ new
}
