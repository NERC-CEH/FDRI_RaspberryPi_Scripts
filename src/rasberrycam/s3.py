import logging
from pathlib import Path
from typing import TypedDict
import boto3
import boto3.session
import os
from datetime import datetime
from botocore import credentials
from botocore.exceptions import NoCredentialsError

logger = logging.getLogger(__name__)

class AWSCredentials(TypedDict):
    access_key_id: str
    secret_access_key: str
    session_token: str

def assume_role(
    role_arn: str, access_key_id: str, secret_access_key: str, region: str, session_name: str = "rasberrycam-session"
) -> AWSCredentials | None:
    """
    Assume the AWS IAM role for S3 access
    Returns session credentials dictionary or None if failed
    """
    try:
        logger.info(f"Attempting to assume role: {role_arn}")

        # Create a boto3 STS client with initial credentials
        sts_client = boto3.client(
            "sts",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

        # Assume the role
        assumed_role = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName="rasberrycam-upload",
            DurationSeconds=3600,  # 1 hour
        )

        credentials = assumed_role["Credentials"]
        logger.info("Successfully assumed role")

        return {
            "access_key_id": credentials["AccessKeyId"],
            "secret_access_key": credentials["SecretAccessKey"],
            "session_token": credentials["SessionToken"],
        }
    except Exception as e:
        logger.error(f"Error assuming role: {e}")
        return None

def upload_to_s3(file_path, bucket_name, region: str, credentials: AWSCredentials, object_name=None):
    """
    Upload a file to an S3 bucket with minimal data usage
    """
    # If S3 object_name was not specified, use file_path
    if object_name is None:
        object_name = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = f"images/{timestamp}_{object_name}"

    try:

        # Create S3 client with role credentials and reduced part size for multipart uploads
        s3_client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=credentials["access_key_id"],
            aws_secret_access_key=credentials["secret_access_key"],
            aws_session_token=credentials["session_token"],
            config=boto3.session.Config(
                s3={
                    "multipart_threshold": 10 * 1024 * 1024
                }  # Only use multipart for files >10MB
            ),
        )

        # Upload the file
        file_size = os.path.getsize(file_path) / 1024
        logger.info(f"Uploading file to S3 ({file_size:.2f}KB): {file_path}")

        s3_client.upload_file(
            file_path,
            bucket_name,
            object_name,
            ExtraArgs={"StorageClass": "STANDARD"},  # Use standard storage class
        )
        logger.info(f"File uploaded to S3: s3://{bucket_name}/{object_name}")
        return True
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return False
    except NoCredentialsError:
        logger.error("AWS credentials not available or incorrect")
        return False
    except Exception as e:
        logger.error(f"Error uploading to S3: {e}")
        return False


class S3Manager:

    access_key_id: str
    secret_access_key: str
    region: str
    role_arn: str

    credentials: AWSCredentials | None = None
    def __init__(self, access_key_id: str, secret_access_key: str, region: str, role_arn: str) -> None:

        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        self.role_arn = role_arn
    
    def assume_role(self) -> None:
        self.credentials = assume_role(self.role_arn, self.access_key_id, self.secret_access_key, self.region)

    def upload(self, file_path: Path, bucket_name: str, object_name: str|None = None) -> bool:
        return upload_to_s3(file_path, bucket_name, self.region, self.credentials, object_name=object_name) #type:ignore