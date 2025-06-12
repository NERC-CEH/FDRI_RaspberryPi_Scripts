import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

from raspberrycam.s3 import S3Manager

logger = logging.getLogger(__name__)


class ImageManager:
    """Class for managing images"""

    base_directory: Path
    """Base directory of program"""

    pending_directory: Path
    """Directory of images to be uploaded"""

    log_directory: Path
    """Directory for logs"""

    def __init__(self, base_directory: Path) -> None:
        """
        Args:
            base_directory: Base directory of the program
        """

        if not isinstance(base_directory, Path):
            base_directory = Path(base_directory)

        self.base_directory = base_directory
        self.pending_directory = base_directory / "pending_uploads"
        self.log_directory = base_directory / "logs"
        self.log_file = self.log_directory / "log.log"

        self._initialize_directories()

    def _initialize_directories(self) -> None:
        """Creates app directories if they don't exist already"""

        for path in [self.base_directory, self.pending_directory, self.log_directory]:
            if not path.exists():
                os.makedirs(path)

    def get_pending_image_path(self, *args, **kwargs) -> Path:
        """Gets a new image filepath with a timestamp
        Returns:
            A path in the pending image folder
        """
        return self.pending_directory / self.get_image_name(*args, **kwargs)

    def get_pending_images(self) -> List[Path]:
        """Get a list of pending paths
        Returns:
            A list of Path objects
        """
        return [self.pending_directory / x for x in os.listdir(self.pending_directory.absolute())]

    @staticmethod
    def get_image_name(prefix: str = "", suffix: str = "") -> str:
        """Gets a filename using an ISO format timestamp
        Args:
            prefix: Adds a prefix to the timestamp
            suffix: Adds a suffix or file extension to the timestamp
        Returns:
            A filename string
        """
        return f"{prefix}{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"


class S3ImageManager(ImageManager):
    """Image manager that writes to S3"""

    bucket_name: str
    """S3 bucket that gets written"""

    s3_manager: S3Manager
    """S3 manager object for handling credentials and uploads"""

    def __init__(self, bucket_name: str, s3_manager: S3Manager, *args) -> None:
        """
        Args:
            bucket_name: S3 bucket that is written to
            s3_manager: The S3 management object
        """

        self.bucket_name = bucket_name
        self.s3_manager = s3_manager
        super().__init__(*args)

    def upload_pending(self, debug: bool = False) -> None:
        """Upload files from the pending directory to S3
        Args:
            debug: Flag to enable debugging mode
        """

        pending_images = self.get_pending_images()
        if len(pending_images) > 0:
            self.s3_manager.assume_role()
            for image in pending_images:
                try:
                    upload_successful = False
                    if debug:
                        logger.info(f"Pretended to upload image {image} to bucket {self.bucket_name}")
                    else:
                        upload_successful = self.s3_manager.upload(image, self.bucket_name)
                    if upload_successful:
                        os.remove(image)
                except Exception as e:
                    logger.exception(f"Failed to upload image: {image}", exc_info=e)
                # Not considered removing images due to size constraint as images are <200 kb with 10 gb it would take
                # ~20 years to fill
        else:
            logger.info("No images to upload")
