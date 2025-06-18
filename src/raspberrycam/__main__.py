"""This file is run when `python -m raspberrycam` is called"""

import argparse
import logging
import os

from dotenv import load_dotenv
from platformdirs import user_data_dir

from raspberrycam.camera import PiCamera
from raspberrycam.config import load_config
from raspberrycam.core import Raspberrycam
from raspberrycam.image import S3ImageManager
from raspberrycam.location import Location
from raspberrycam.logger import setup_logging
from raspberrycam.s3 import S3Manager
from raspberrycam.scheduler import FdriScheduler

# Read environment variables for AWS connection
load_dotenv()


def main(debug: bool = False, interval: int = 10800) -> None:
    """Example invocation of the RasberryCam class"""

    # This will throw an error and complain if keys aren't set,
    # Or if the config file can't be found.
    config = load_config("config/config.yaml")

    if config.interval:
        interval = config.interval

    location = Location(latitude=config.lat, longitude=config.lon)
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
    # The other config options form part of the filename
    image_manager = S3ImageManager(AWS_BUCKET_NAME, s3_manager, user_data_dir("raspberrycam"), config)

    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG
    setup_logging(filename=image_manager.log_file, level=log_level)
    app = Raspberrycam(
        scheduler=scheduler, camera=camera, image_manager=image_manager, capture_interval=interval, debug=debug
    )
    app.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--interval", type=int, default=10800)

    args = parser.parse_args()
    main(debug=args.debug, interval=args.interval)
