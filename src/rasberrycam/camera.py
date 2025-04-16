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
    def capture_image(self, *args, **kwargs) -> bool:
        pass

    @abstractmethod
    def power_on(self) -> None:
        pass

    @abstractmethod
    def power_off(self) -> None:
        pass


class LibCamera(CameraInterface):
    def capture_image(self, filepath: Path) -> bool:
        """Capture an image using libcamera with lower resolution directly"""
        try:
            # Turn on camera if needed
            self.power_on()

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
                return True
            else:
                logger.error("Image capture failed: file not created")
                return False
        except Exception as e:
            logger.error(f"Error capturing image: {e}")
            return False

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


# class RaspberryCameraOptions:

#     base_directory = Path(user_data_dir(rasberrycam.__name__))
#     save_directory = base_directory / "photos"
#     pending_directory = base_directory / "pending_uploads"
#     capture_interval: int
#     image_quality: int # 1-100
#     image_max_width: int
#     image_max_height: int
#     auto_shutdown: bool
#     immediate_upload: bool

#     def __init__(
#         self,
#         base_directory: Path|None = None,
#         capture_interval: int = 300,
#         image_quality: int = 85, # 1-100
#         image_max_width: int = 1024,
#         image_max_height: int = 768,
#         auto_shutdown: bool = True,
#         immediate_upload: bool = True
#     ) -> None:

#         if base_directory:
#             self.base_directory = base_directory

#         self.capture_interval_day = capture_interval_day
#         self.capture_interval_night = capture_interval_night
#         self.image_quality = image_quality
#         self.image_max_height = image_max_height
#         self.image_max_width = image_max_width
#         self.auto_shutdown = auto_shutdown
#         self.immediate_upload = immediate_upload
