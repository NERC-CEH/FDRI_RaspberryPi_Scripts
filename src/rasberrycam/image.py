from pathlib import Path
from typing import List
from PIL import Image
import os
import logging
from datetime import datetime

from rasberrycam.s3 import S3Manager

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

class ImageManager:

    base_directory: Path
    pending_directory: Path
    log_directory: Path

    def __init__(self, base_directory: Path) -> None:

        if not isinstance(base_directory, Path):
            base_directory = Path(base_directory)

        self.base_directory = base_directory
        self.pending_directory = base_directory / "pending_uploads"
        self.log_directory = base_directory / "logs"
        self.log_file = self.log_directory / "log.log"

        self._initialize_directories()

    def _initialize_directories(self) -> None:

        for path in [self.base_directory, self.pending_directory, self.log_directory]:
            if not path.exists():
                os.makedirs(path)

    def get_pending_image_path(self, *args, **kwargs) -> Path:
        return self.pending_directory / self.get_image_name(*args, **kwargs)

    def get_pending_images(self) -> List[Path]:
        return [self.pending_directory / x for x in os.listdir(self.pending_directory.absolute())]

    @staticmethod
    def get_image_name(prefix: str="", suffix: str="") -> str:
        return f"{prefix}{datetime.now().isoformat()}{suffix}"

class S3ImageManager(ImageManager):

    bucket_name: str
    s3_manager: S3Manager

    def __init__(self, bucket_name, s3_manager: S3Manager, *args) -> None:
        self.bucket_name = bucket_name
        self.s3_manager = s3_manager
        super().__init__(*args)

    def upload_pending(self, debug: bool=False) -> None:
        pending_images = self.get_pending_images()
        if len(pending_images) > 0:
            self.s3_manager.assume_role()
            for image in pending_images:
                try: 
                    if debug:
                        logger.info(f"Pretended to upload image {image} to bucket {self.bucket_name}")
                    else:
                        self.s3_manager.upload(image, self.bucket_name)
                    os.remove(image)
                except Exception as e:
                    logger.exception(f"Failed to upload image: {image}", exc_info=e)
        else:
            logger.info("No images to upload")