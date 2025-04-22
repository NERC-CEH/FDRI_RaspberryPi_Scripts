import logging
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class CameraInterface(ABC):
    """Abstract implementation of a camera."""

    image_width: int
    """Image capture width in pixels"""

    image_height: int
    """Image capture height in pixels"""

    quality: int
    """Image quality from 1-100"""

    def __init__(self, quality: int, image_width: int, image_height: int) -> None:
        """
        Args:
            quality: Picture quality from 1-100.
            image_width: Width of image in pixels.
            image_height: Height of image in pixels.
        """
        self.image_width = image_width
        self.image_height = image_height
        self.quality = quality

    @abstractmethod
    def capture_image(self, *args, **kwargs) -> None:
        """Abstract method defined for capturing an image with the camera"""


class DebugCamera(CameraInterface):
    "Debug camera class used for end to end testing"

    def capture_image(self, filepath: Path) -> None:
        """Captures a fake image and writes dummy text to a file.
        Args:
            filepath: The output file destination
        """

        try:
            logger.info("Capturing image")

            with open(filepath, "w") as f:
                f.write("Pretend I'm an image")

            logger.info(f"Wrote fake image to {filepath}")
        except Exception as e:
            logger.exception("Failed to write image", exc_info=e)


class LibCamera(CameraInterface):
    def capture_image(self, filepath: Path) -> None:
        """Captures an image and writes it to file
        Args:
            filepath: The output destination
        """

        try:
            # Use libcamera-still with reduced resolution and quality
            logger.info("Capturing image")
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
        """Turns on the physical camera"""

        try:
            logger.info("Ensuring camera module is on")
            subprocess.run(["sudo", "modprobe", "bcm2835-v4l2"], shell=True, check=False)
        except Exception as e:
            logger.error(f"Failed to turn on camera: {e}")

    def power_off(self) -> None:
        """Turns off the physical camera"""

        try:
            if os.path.exists("/sys/modules/bcm2835_v4l2"):
                logger.info("Turning off camera module")
                subprocess.run("sudo rmmod bcm2835-v4l2", shell=True, check=False)
                subprocess.run("sudo rmmod bcm2835-isp", shell=True, check=False)
        except Exception as e:
            logger.error(f"Failed to turn off camera: {e}")
