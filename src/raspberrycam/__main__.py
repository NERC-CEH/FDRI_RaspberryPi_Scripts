"""This file is run when `python -m raspberrycam` is called"""

import argparse
import logging
import os

from dotenv import load_dotenv
from platformdirs import user_data_dir

from raspberrycam.camera import PiCamera
from raspberrycam.core import Raspberrycam
from raspberrycam.image import S3ImageManager
from raspberrycam.location import Location
from raspberrycam.logger import setup_logging
from raspberrycam.s3 import S3Manager
from raspberrycam.scheduler import FdriScheduler
from raspberrycam.face_blur import blur_faces  # Testing face blurring utility

load_dotenv()


def main(debug: bool = True) -> None:
    """Example invocation of the Raspberrycam class"""

    location = Location(latitude=51.66023, longitude=-1.1125)
    scheduler = FdriScheduler(location)
    camera = PiCamera(1024, 768)

    # Option to set these in .env - they will load automatically
    AWS_ROLE_ARN = os.environ["AWS_ROLE_ARN"]
    AWS_BUCKET_NAME = os.environ["AWS_BUCKET_NAME"]
    AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]

    s3_manager = S3Manager(
        role_arn=AWS_ROLE_ARN, access_key_id=AWS_ACCESS_KEY_ID, secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    image_manager = S3ImageManager(AWS_BUCKET_NAME, s3_manager, user_data_dir("raspberrycam"))

    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG
    setup_logging(filename=image_manager.log_file, level=log_level)

    # Add face blurring argument here and handle it in Raspberrycam if needed in the future.
    app = Raspberrycam(
        scheduler=scheduler,
        camera=camera,
        image_manager=image_manager,
        capture_interval=800,
        debug=debug,
        # blur_faces=blur_faces,  # Uncomment and handle in Raspberrycam class if blur_faces is to be used
    )
    app.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    main(debug=args.debug)
