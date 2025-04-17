from platformdirs import user_data_dir
from pathlib import Path
from abc import ABC, abstractmethod
import logging
import subprocess
import os

logger = logging.getLogger(__name__)


class CameraInterface(ABC):
    image_width: int
    image_height: int
    quality: int

    def __init__(self, quality: int, image_width: int, image_height: int) -> None:
        self.image_width = image_width
        self.image_height = image_height
        self.quality = quality

    @abstractmethod
    def capture_image(self, *args, **kwargs) -> None:
        pass

class DebugCamera(CameraInterface):

    def capture_image(self, filepath: Path) -> None:
        try:
            logger.info(f"Capturing image")

            with open(filepath, "w") as f:
                f.write("Pretend I'm an image")
            
            logger.info(f"Wrote fake image to {filepath}")
        except Exception as e:
            logger.exception("Failed to write image", exc_info=e)


class LibCamera(CameraInterface):
    def capture_image(self, filepath: Path) -> None:
        """Capture an image using libcamera with lower resolution directly"""
        try:
            # Use libcamera-still with reduced resolution and quality
            logger.info(f"Capturing image")
            subprocess.call(
                [
                    "libcamera-still",
                    "--width",
                    str(self.image_width),
                    "--height",
                    str(self.image_height),
                    "--quality",
                    str(self.quality),
                    "-o",
                    filepath,
                ]
            )

            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath) / 1024  # KB
                logger.info(f"Image captured: {filepath} ({file_size:.2f}KB)")
            else:
                logger.error("Image capture failed: file not created")
        except Exception as e:
            logger.error(f"Error capturing image: {e}")

    def power_on(self) -> None:
        try:
            logger.info("Ensuring camera module is on")
            subprocess.run(["sudo", "modprobe", "bcm2835-v4l2"], shell=True)
        except Exception as e:
            logger.error(f"Failed to turn on camera: {e}")

    def power_off(self) -> None:
        try:
            if os.path.exists("/sys/modules/bcm2835_v4l2"):
                logger.info("Turning off camera module")
                subprocess.run("sudo rmmod bcm2835-v4l2", shell=True)
                subprocess.run("sudo rmmod bcm2835-isp", shell=True)
        except Exception as e:
            logger.error(f"Failed to turn off camera: {e}")
