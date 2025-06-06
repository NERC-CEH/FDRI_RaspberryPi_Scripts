"""This file is run when `python -m rasberrycam` is called"""

import os

from dotenv import load_dotenv
from platformdirs import user_data_dir

from rasberrycam.camera import PiCamera
from rasberrycam.core import Rasberrycam
from rasberrycam.image import S3ImageManager
from rasberrycam.location import Location
from rasberrycam.logger import setup_logging
from rasberrycam.s3 import S3Manager
from rasberrycam.scheduler import FdriScheduler

load_dotenv()


def main() -> None:
    """Example invocation of the RasberryCam class"""

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
    image_manager = S3ImageManager(AWS_BUCKET_NAME, s3_manager, user_data_dir("rasberrycam"))

    setup_logging(filename=image_manager.log_file)
    app = Rasberrycam(scheduler=scheduler, camera=camera, image_manager=image_manager, capture_interval=5, debug=False)
    app.run()


if __name__ == "__main__":
    main()
