#!/usr/bin/env python3
"""
AWS IoT Core Certificate-based S3 Upload Script for Raspberry Pi
"""

import boto3
import json
import logging
from pathlib import Path
from botocore.exceptions import ClientError, NoCredentialsError
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IoTCertificateS3Uploader:
    def __init__(self, config_file='config.json'):
        """
        Initialize the uploader with configuration
        
        Args:
            config_file (str): Path to configuration file
        """
        self.config = self.load_config(config_file)
        self.s3_client = None
        self.iot_client = None
        
    def load_config(self, config_file):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Validate required fields
            required_fields = [
                'aws_region', 'iot_endpoint', 'certificate_path', 
                'private_key_path', 'ca_cert_path', 's3_bucket_name'
            ]
            
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field: {field}")
                    
            return config
            
        except FileNotFoundError:
            logger.error(f"Configuration file {config_file} not found")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in configuration file {config_file}")
            raise
    
    def setup_iot_credentials(self):
        """
        Set up AWS credentials using IoT Core certificate
        This assumes you have IoT policies that allow AssumeRole or direct S3 access
        """
        try:
            # Create IoT client with certificate
            self.iot_client = boto3.client(
                'iot',
                region_name=self.config['aws_region'],
                # For certificate-based auth, you'll need to use STS with certificate
                # This is a simplified example - you may need to implement certificate-based STS
            )
            
            # Alternative: Use AWS IoT Device SDK for certificate-based authentication
            # and then assume a role that has S3 access
            
            logger.info("IoT client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup IoT credentials: {str(e)}")
            raise
    
    def assume_role_with_certificate(self):
        """
        Assume an IAM role using the IoT certificate
        This requires proper IoT policies and IAM role trust relationships
        """
        try:
            # This is where you'd implement the certificate-based role assumption
            # For now, we'll use standard boto3 client
            # In production, you'd use AWS IoT Device SDK or implement custom STS calls
            
            self.s3_client = boto3.client(
                's3',
                region_name=self.config['aws_region']
            )
            
            logger.info("S3 client initialized successfully")
            
        except NoCredentialsError:
            logger.error("No AWS credentials found. Ensure your IoT certificate has proper permissions.")
            raise
        except Exception as e:
            logger.error(f"Failed to assume role: {str(e)}")
            raise
    
    def upload_file_to_s3(self, local_file_path, s3_key=None):
        """
        Upload a file to S3 bucket
        
        Args:
            local_file_path (str): Path to local file
            s3_key (str): S3 object key (optional, defaults to filename with timestamp)
        """
        if not self.s3_client:
            self.assume_role_with_certificate()
        
        local_path = Path(local_file_path)
        
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_file_path}")
        
        # Generate S3 key if not provided
        if not s3_key:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_key = f"raspberry-pi-uploads/{timestamp}_{local_path.name}"
        
        try:
            # Upload file
            self.s3_client.upload_file(
                str(local_path),
                self.config['s3_bucket_name'],
                s3_key,
                ExtraArgs={
                    'Metadata': {
                        'uploaded_by': 'raspberry-pi',
                        'upload_time': datetime.now().isoformat(),
                        'device_id': self.config.get('device_id', 'unknown')
                    }
                }
            )
            
            logger.info(f"Successfully uploaded {local_file_path} to s3://{self.config['s3_bucket_name']}/{s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Failed to upload file: {str(e)}")
            raise
    
    def upload_directory(self, local_dir_path, s3_prefix=""):
        """
        Upload all files in a directory to S3
        
        Args:
            local_dir_path (str): Path to local directory
            s3_prefix (str): S3 prefix for uploaded files
        """
        local_dir = Path(local_dir_path)
        
        if not local_dir.exists() or not local_dir.is_dir():
            raise ValueError(f"Directory not found: {local_dir_path}")
        
        uploaded_files = []
        
        for file_path in local_dir.rglob('*'):
            if file_path.is_file():
                # Create relative path for S3 key
                rel_path = file_path.relative_to(local_dir)
                s3_key = f"{s3_prefix}/{rel_path}".strip('/')
                
                try:
                    self.upload_file_to_s3(str(file_path), s3_key)
                    uploaded_files.append(s3_key)
                except Exception as e:
                    logger.error(f"Failed to upload {file_path}: {str(e)}")
        
        return uploaded_files
    
    def list_s3_objects(self, prefix=""):
        """List objects in the S3 bucket"""
        if not self.s3_client:
            self.assume_role_with_certificate()
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config['s3_bucket_name'],
                Prefix=prefix
            )
            
            objects = response.get('Contents', [])
            return [obj['Key'] for obj in objects]
            
        except ClientError as e:
            logger.error(f"Failed to list S3 objects: {str(e)}")
            raise

def create_sample_config():
    """Create a sample configuration file"""
    sample_config = {
        "aws_region": "us-east-1",
        "iot_endpoint": "your-iot-endpoint.iot.us-east-1.amazonaws.com",
        "certificate_path": "/home/pi/certs/certificate.pem.crt",
        "private_key_path": "/home/pi/certs/private.pem.key",
        "ca_cert_path": "/home/pi/certs/AmazonRootCA1.pem",
        "s3_bucket_name": "your-s3-bucket-name",
        "device_id": "raspberry-pi-001",
        "iot_role_arn": "arn:aws:iam::123456789012:role/IoTDeviceRole"
    }
    
    with open('config.json', 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    print("Sample configuration file created: config.json")
    print("Please update it with your actual values.")

def main():
    """Main function for testing"""
    try:
        # Create sample config if it doesn't exist
        if not Path('config.json').exists():
            create_sample_config()
            return
        
        # Initialize uploader
        uploader = IoTCertificateS3Uploader()
        
        # Setup credentials
        uploader.setup_iot_credentials()
        
        # Example usage
        
        # Upload a single file
        # uploader.upload_file_to_s3('/path/to/your/file.txt')
        
        # Upload directory
        # uploader.upload_directory('/path/to/your/directory', 'sensor-data')
        
        # List uploaded files
        # files = uploader.list_s3_objects('raspberry-pi-uploads')
        # print(f"Uploaded files: {files}")
        
        logger.info("Script completed successfully")
        
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
