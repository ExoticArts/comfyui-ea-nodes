"""
EA Image Compare - Side-by-side image comparison with captions
"""
import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import folder_paths
import os

def get_fonts():
    """Get available fonts from KJNodes or use default"""
    font_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "comfyui-kjnodes",
        "fonts"
    )

    fonts = []
    if os.path.exists(font_dir):
        fonts = [f for f in os.listdir(font_dir) if f.endswith(('.ttf', '.otf'))]

    if not fonts:
        fonts = ["default"]

    return fonts


class EAImageCompareBase:
    """Base class with shared functionality for image comparison nodes"""

    def create_caption(self, text, width, height, font_size, font_color, bg_color, font_name):
        """Create a caption image with centered text"""
        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # Try to load font
        try:
            if font_name != "default":
                font_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "comfyui-kjnodes",
                    "fonts"
                )
                font_path = os.path.join(font_dir, font_name)
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        # Get text bounding box for centering
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            # Fallback for older Pillow
            text_width, text_height = draw.textsize(text, font=font)

        # Center the text
        x = (width - text_width) // 2
        y = (height - text_height) // 2

        draw.text((x, y), text, fill=font_color, font=font)

        return img

    def tensor_to_pil(self, tensor):
        """Convert ComfyUI IMAGE tensor to PIL Image"""
        # ComfyUI images are [B, H, W, C] in 0-1 range
        img = tensor[0]  # Take first image from batch
        img = (img.cpu().numpy() * 255).astype(np.uint8)
        return Image.fromarray(img)

    def pil_to_tensor(self, pil_image):
        """Convert PIL Image to ComfyUI IMAGE tensor"""
        img = np.array(pil_image).astype(np.float32) / 255.0
        img = torch.from_numpy(img).unsqueeze(0)  # Add batch dimension
        return img

    def compose_comparison(self, images, captions, scale, font_size, caption_height,
                          font_color, background_color, spacing, font="default"):
        """Compose multiple images into a comparison layout"""
        # Convert all tensors to PIL and apply scale
        pil_images = []
        for img_tensor in images:
            pil_img = self.tensor_to_pil(img_tensor)

            # Apply scale if not 1.0
            if scale != 1.0:
                new_width = int(pil_img.width * scale)
                new_height = int(pil_img.height * scale)
                pil_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            pil_images.append(pil_img)

        # Validate all images have the same dimensions (after scaling)
        first_size = pil_images[0].size
        for i, img in enumerate(pil_images[1:], start=2):
            if img.size != first_size:
                raise ValueError(
                    f"All images must have the same dimensions. "
                    f"Image 1: {first_size}, Image {i}: {img.size}"
                )

        # Use actual image dimensions (after scaling, preserves aspect ratio)
        width, height = first_size

        # Create caption images for each
        caption_images = []
        for caption in captions:
            cap_img = self.create_caption(
                caption, width, caption_height, font_size,
                font_color, background_color, font
            )
            caption_images.append(cap_img)

        # Calculate dimensions for final image
        num_images = len(pil_images)
        total_width = width * num_images + spacing * (num_images - 1)
        total_height = caption_height + height

        # Create composite image
        composite = Image.new('RGB', (total_width, total_height), background_color)

        # Paste each image with its caption
        x_offset = 0
        for img, cap_img in zip(pil_images, caption_images):
            composite.paste(cap_img, (x_offset, 0))
            composite.paste(img, (x_offset, caption_height))
            x_offset += width + spacing

        # Convert back to ComfyUI tensor
        return self.pil_to_tensor(composite)


class EAImageCompare(EAImageCompareBase):
    """
    Compare two images side-by-side with custom captions.
    Perfect for LoRA before/after comparisons.
    """

    @classmethod
    def INPUT_TYPES(cls):
        fonts = get_fonts()

        return {
            "required": {
                "image_1": ("IMAGE",),
                "caption_1": ("STRING", {"default": "Without LoRA", "multiline": False}),
                "image_2": ("IMAGE",),
                "caption_2": ("STRING", {"default": "With LoRA", "multiline": False}),
                "scale": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 2.0, "step": 0.05}),
                "font_size": ("INT", {"default": 32, "min": 12, "max": 200, "step": 1}),
                "caption_height": ("INT", {"default": 60, "min": 20, "max": 200, "step": 1}),
                "font_color": ("STRING", {"default": "white"}),
                "background_color": ("STRING", {"default": "black"}),
                "spacing": ("INT", {"default": 4, "min": 0, "max": 50, "step": 1}),
            },
            "optional": {
                "font": (fonts, {"default": fonts[0] if fonts else "default"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("comparison",)
    FUNCTION = "compare_images"
    CATEGORY = "EA / IO"
    DESCRIPTION = """
Compare 2 images side-by-side with captions.
Scale parameter resizes all images proportionally (1.0 = original size).
"""

    def compare_images(self, image_1, caption_1, image_2, caption_2,
                      scale, font_size, caption_height, font_color,
                      background_color, spacing, font="default"):
        return (self.compose_comparison(
            [image_1, image_2],
            [caption_1, caption_2],
            scale, font_size, caption_height,
            font_color, background_color, spacing, font
        ),)


class EAImageCompare3Way(EAImageCompareBase):
    """
    Compare three images side-by-side with custom captions.
    Perfect for LoRA strength comparisons.
    """

    @classmethod
    def INPUT_TYPES(cls):
        fonts = get_fonts()

        return {
            "required": {
                "image_1": ("IMAGE",),
                "caption_1": ("STRING", {"default": "Base Model", "multiline": False}),
                "image_2": ("IMAGE",),
                "caption_2": ("STRING", {"default": "LoRA 0.5", "multiline": False}),
                "image_3": ("IMAGE",),
                "caption_3": ("STRING", {"default": "LoRA 1.0", "multiline": False}),
                "scale": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 2.0, "step": 0.05}),
                "font_size": ("INT", {"default": 32, "min": 12, "max": 200, "step": 1}),
                "caption_height": ("INT", {"default": 60, "min": 20, "max": 200, "step": 1}),
                "font_color": ("STRING", {"default": "white"}),
                "background_color": ("STRING", {"default": "black"}),
                "spacing": ("INT", {"default": 4, "min": 0, "max": 50, "step": 1}),
            },
            "optional": {
                "font": (fonts, {"default": fonts[0] if fonts else "default"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("comparison",)
    FUNCTION = "compare_images"
    CATEGORY = "EA / IO"
    DESCRIPTION = """
Compare 3 images side-by-side with captions.
Scale parameter resizes all images proportionally (1.0 = original size).
"""

    def compare_images(self, image_1, caption_1, image_2, caption_2,
                      image_3, caption_3, scale, font_size, caption_height,
                      font_color, background_color, spacing, font="default"):
        return (self.compose_comparison(
            [image_1, image_2, image_3],
            [caption_1, caption_2, caption_3],
            scale, font_size, caption_height,
            font_color, background_color, spacing, font
        ),)


class EAImageCompare4Way(EAImageCompareBase):
    """
    Compare four images side-by-side with custom captions.
    Perfect for comprehensive LoRA strength comparisons.
    """

    @classmethod
    def INPUT_TYPES(cls):
        fonts = get_fonts()

        return {
            "required": {
                "image_1": ("IMAGE",),
                "caption_1": ("STRING", {"default": "Base Model", "multiline": False}),
                "image_2": ("IMAGE",),
                "caption_2": ("STRING", {"default": "LoRA 0.5", "multiline": False}),
                "image_3": ("IMAGE",),
                "caption_3": ("STRING", {"default": "LoRA 1.0", "multiline": False}),
                "image_4": ("IMAGE",),
                "caption_4": ("STRING", {"default": "LoRA 1.5", "multiline": False}),
                "scale": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 2.0, "step": 0.05}),
                "font_size": ("INT", {"default": 32, "min": 12, "max": 200, "step": 1}),
                "caption_height": ("INT", {"default": 60, "min": 20, "max": 200, "step": 1}),
                "font_color": ("STRING", {"default": "white"}),
                "background_color": ("STRING", {"default": "black"}),
                "spacing": ("INT", {"default": 4, "min": 0, "max": 50, "step": 1}),
            },
            "optional": {
                "font": (fonts, {"default": fonts[0] if fonts else "default"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("comparison",)
    FUNCTION = "compare_images"
    CATEGORY = "EA / IO"
    DESCRIPTION = """
Compare 4 images side-by-side with captions.
Scale parameter resizes all images proportionally (1.0 = original size).
"""

    def compare_images(self, image_1, caption_1, image_2, caption_2,
                      image_3, caption_3, image_4, caption_4,
                      scale, font_size, caption_height, font_color,
                      background_color, spacing, font="default"):
        return (self.compose_comparison(
            [image_1, image_2, image_3, image_4],
            [caption_1, caption_2, caption_3, caption_4],
            scale, font_size, caption_height,
            font_color, background_color, spacing, font
        ),)


NODE_CLASS_MAPPINGS = {
    "EAImageCompare": EAImageCompare,
    "EAImageCompare3Way": EAImageCompare3Way,
    "EAImageCompare4Way": EAImageCompare4Way,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EAImageCompare": "EA Image Compare",
    "EAImageCompare3Way": "EA 3-Way Image Compare",
    "EAImageCompare4Way": "EA 4-Way Image Compare",
}
