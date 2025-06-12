import os
from pathlib import Path

from dotenv import load_dotenv

from raspberrycam.image import ImageManager, S3ImageManager
from raspberrycam.s3 import S3Manager

# There are two of these Image Managers, one local and one S3 based


# This stores images locally
def test_image_manager(tmp_path: Path) -> None:
    im = ImageManager(tmp_path)
    assert im.pending_directory == tmp_path / "pending_uploads"


# This wraps around ImageManager and uploads to s3, deletes the original
# If upload fails deletion is skipped, we should see a log message
def test_s3_image_manager(tmp_path: Path) -> None:
    load_dotenv()
    AWS_ROLE_ARN = os.environ["AWS_ROLE_ARN"]
    AWS_BUCKET_NAME = os.environ["AWS_BUCKET_NAME"]
    AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]

    s3 = S3Manager(role_arn=AWS_ROLE_ARN, access_key_id=AWS_ACCESS_KEY_ID, secret_access_key=AWS_SECRET_ACCESS_KEY)
    im = S3ImageManager(AWS_BUCKET_NAME, s3, tmp_path)
    assert im.pending_directory == tmp_path / "pending_uploads"
