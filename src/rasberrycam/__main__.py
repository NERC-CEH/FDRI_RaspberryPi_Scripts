"""This file is run when `python -m rasberrycam` is called. Put your client code here if you have any."""

import os
from rasberrycam import image
from rasberrycam.logger import setup_logging
from platformdirs import user_data_dir

from rasberrycam.camera import DebugCamera, CameraInterface
from rasberrycam.core import Rasberrycam
from rasberrycam.image import S3ImageManager
from rasberrycam.s3 import S3Manager
from rasberrycam.scheduler import FdriScheduler
from rasberrycam.temporal import TemporalLocation


def main():
    location = TemporalLocation(
        latitude=51.66023,
        longitude=-1.1125,
        region="Europe/London",
        city="Wallingford"
    )
    scheduler = FdriScheduler(location)
    camera = DebugCamera(85, 1024,768)

    AWS_ROLE_ARN=os.environ["AWS_ROLE_ARN"]
    AWS_BUCKET_NAME=os.environ["AWS_BUCKET_NAME"]
    AWS_REGION=os.environ["AWS_REGION"]
    AWS_ACCESS_KEY_ID=os.environ["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY=os.environ["AWS_SECRET_ACCESS_KEY"]

    s3_manager = S3Manager(
        access_key_id=AWS_ACCESS_KEY_ID,
        secret_access_key=AWS_SECRET_ACCESS_KEY,
        region=AWS_REGION,
        role_arn=AWS_ROLE_ARN
    )
    image_manager = S3ImageManager(AWS_BUCKET_NAME, s3_manager, user_data_dir("rasberrycam"))

    setup_logging(filename=image_manager.log_file)
    app = Rasberrycam(
        scheduler = scheduler,
        camera=camera,
        image_manager=image_manager,
        capture_interval=5,
        debug=True
    )
    app.run()


if __name__ == "__main__":
    main()
