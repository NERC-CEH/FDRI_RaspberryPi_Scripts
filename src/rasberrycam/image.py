from PIL import Image
import os
import logging

logger = logging.getLogger(__name__)


def optimize_image(input_path, max_width: int, max_height: int, quality: int, output_path=None):
    """
    Optimize image for lower data usage
    Returns the path to the optimized image
    """
    if output_path is None:
        # Create a filename for the optimized image
        filename, ext = os.path.splitext(input_path)
        output_path = f"{filename}_optimized{ext}"

    try:
        # Open the image
        with Image.open(input_path) as img:
            # Convert to RGB if it's not already (to ensure JPEG compatibility)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Calculate new dimensions while maintaining aspect ratio
            width, height = img.size
            if width > max_width or height > max_height:
                # Calculate ratio to resize
                ratio = min(max_width / width, max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.LANCZOS)

            # Save with compression
            img.save(output_path, "JPEG", quality=quality, optimize=True)

            # Get file size for logging
            original_size = os.path.getsize(input_path) / 1024  # KB
            optimized_size = os.path.getsize(output_path) / 1024  # KB
            logger.info(
                f"Image optimized: {original_size:.2f}KB → {optimized_size:.2f}KB ({(1 - optimized_size / original_size) * 100:.1f}% reduction)"
            )

            return output_path
    except Exception as e:
        logger.error(f"Error optimizing image: {e}")
        return input_path  # Return original path if optimization fails
