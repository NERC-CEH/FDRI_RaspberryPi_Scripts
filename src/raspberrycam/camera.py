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
    def capture_image(self, filepath: Path, vflip: bool = True, hflip: bool = True) -> None:
        """Abstract method defined for capturing an image with the camera

        Args:
            filepath: The output file destination
            vflip: Whether to flip the image vertically (upside down), defaults to False
            hflip: Whether to flip the image horizontally (mirror), defaults to False
        """


class DebugCamera(CameraInterface):
    "Debug camera class used for end to end testing"

    def capture_image(self, filepath: Path, vflip: bool = False, hflip: bool = False) -> None:
        """Captures a fake image and writes dummy text to a file.
        Args:
            filepath: The output file destination
            vflip: Whether to flip the image vertically, defaults to False
            hflip: Whether to flip the image horizontally, defaults to False
        """

        try:
            flip_description = []
            if vflip:
                flip_description.append("vertically flipped")
            if hflip:
                flip_description.append("horizontally flipped")

            flip_text = f"({', '.join(flip_description)})" if flip_description else ""
            logger.info(f"Capturing image{flip_text}")

            with open(filepath, "w") as f:
                content = "Pretend I'm an image"
                if vflip and hflip:
                    content = "Pretend I'm an upside-down and mirrored image"
                elif vflip:
                    content = "Pretend I'm an upside-down image"
                elif hflip:
                    content = "Pretend I'm a mirrored image"

                f.write(content)

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

    def capture_image(self, filepath: Path, vflip: bool = False, hflip: bool = False) -> None:
        """Captures an image and writes it to file
        Args:
            filepath: The output destination
            vflip: Whether to flip the image vertically, defaults to False
            hflip: Whether to flip the image horizontally, defaults to False
        """
        try:
            # Save original orientation settings
            original_vflip = self._camera.vflip
            original_hflip = self._camera.hflip

            # Apply flip settings
            self._camera.vflip = vflip
            self._camera.hflip = hflip

            # Take photo
            self._camera.take_photo(filepath)

            # Restore original orientation settings
            self._camera.vflip = original_vflip
            self._camera.hflip = original_hflip

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

    def capture_image(self, filepath: Path, vflip: bool = False, hflip: bool = False) -> None:
        """Captures an image and writes it to file
        Args:
            filepath: The output destination
            vflip: Whether to flip the image vertically, defaults to False
            hflip: Whether to flip the image horizontally, defaults to False
        """

        try:
            flip_description = []
            if vflip:
                flip_description.append("vertically flipped")
            if hflip:
                flip_description.append("horizontally flipped")

            flip_text = f"({', '.join(flip_description)})" if flip_description else ""
            logger.info(f"Capturing image{flip_text}")

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

            # Add flip parameters if requested
            if vflip:
                cmd.append("--vflip")
            if hflip:
                cmd.append("--hflip")

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
