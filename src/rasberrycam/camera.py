import logging 
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from picamzero import Camera

logger = logging.getLogger(__name__)


class CameraInterface(ABC):
    """Abstract implementation of a camera."""

    image_width: int
    """Image capture width in pixels"""

    image_height: int
    """Image capture height in pixels"""

    def __init__(self, image_width: int, image_height: int) -> None:
        """
        Args:
            image_width: Width of image in pixels.
            image_height: Height of image in pixels.
        """
        self.image_width = image_width
        self.image_height = image_height

    @abstractmethod
    def capture_image(self, filepath: Path, flip: bool = False) -> None:
        """Abstract method defined for capturing an image with the camera
        
        Args:
            filepath: The output file destination
            flip: Whether to flip the image vertically (upside down), defaults to False
        """


class DebugCamera(CameraInterface):
    "Debug camera class used for end to end testing"

    def capture_image(self, filepath: Path, flip: bool = False) -> None:
        """Captures a fake image and writes dummy text to a file.
        Args:
            filepath: The output file destination
            flip: Whether to flip the image vertically, defaults to False
        """

        try:
            logger.info(f"Capturing image{'(flipped)' if flip else ''}")

            with open(filepath, "w") as f:
                if flip:
                    f.write("Pretend I'm an upside-down image")
                else:
                    f.write("Pretend I'm an image")

            logger.info(f"Wrote fake image to {filepath}")
        except Exception as e:
            logger.exception("Failed to write image", exc_info=e)


class PiCamera(CameraInterface):
    """Implementation for a Rasberry Pi camera module"""

    _camera: Camera

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._camera = Camera()
        self._camera.still_size = (self.image_width, self.image_height)

    def capture_image(self, filepath: Path, flip: bool = False) -> None:
        """Captures an image and writes it to file
        Args:
            filepath: The output destination
            flip: Whether to flip the image vertically, defaults to False
        """
        try:
            if flip:
                # Save original orientation setting
                original_vflip = self._camera.vflip
                # Set vertical flip
                self._camera.vflip = True
                # Take photo
                self._camera.take_photo(filepath)
                # Restore original orientation setting
                self._camera.vflip = original_vflip
            else:
                self._camera.take_photo(filepath)
        except Exception as e:
            logger.exception("Failed to write image", exc_info=e)


class LibCamera(CameraInterface):
    quality: int
    """Image quality from 1-100"""

    def __init__(self, quality: int, *args, **kwargs) -> None:
        """
        Args:
            quality: The camera quality from 1-100
        """
        super().__init__(*args, **kwargs)

        self.quality = quality

    def capture_image(self, filepath: Path, flip: bool = False) -> None:
        """Captures an image and writes it to file
        Args:
            filepath: The output destination
            flip: Whether to flip the image vertically, defaults to False
        """

        try:
            # Use libcamera-still with reduced resolution and quality
            logger.info(f"Capturing image{'(flipped)' if flip else ''}")
            
            cmd = [
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
            
            # Add vertical flip parameter if requested
            if flip:
                cmd.append("--vflip")
                
            subprocess.call(cmd)

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
            subprocess.run(["sudo", "modprobe", "bcm2835-v4l2"], check=False)
        except Exception as e:
            logger.error(f"Failed to turn on camera: {e}")

    def power_off(self) -> None:
        """Turns off the physical camera"""

        try:
            if os.path.exists("/sys/modules/bcm2835_v4l2"):
                logger.info("Turning off camera module")
                subprocess.run(["sudo", "rmmod", "bcm2835-v4l2"], check=False)
                subprocess.run(["sudo", "rmmod", "bcm2835-isp"], check=False)
        except Exception as e:
            logger.error(f"Failed to turn off camera: {e}")
