import boto3
import json
import ssl
import time
from botocore.exceptions import ClientError
from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
import threading

class IoTCertificateS3Uploader:
    def __init__(self, 
                 endpoint, 
                 cert_filepath, 
                 pri_key_filepath, 
                 ca_filepath,
                 thing_name,
                 role_arn,
                 s3_bucket_name,
                 aws_region='us-east-1'):
        
        self.endpoint = endpoint
        self.cert_filepath = cert_filepath
        self.pri_key_filepath = pri_key_filepath
        self.ca_filepath = ca_filepath
        self.thing_name = thing_name
        self.role_arn = role_arn
        self.s3_bucket_name = s3_bucket_name
        self.aws_region = aws_region
        
        self.mqtt_connection = None
        self.s3_client = None
        self.credentials = None
        
    def connect_to_iot(self):
        """Establish MQTT connection to AWS IoT Core"""
        try:
            # Create MQTT connection
            self.mqtt_connection = mqtt_connection_builder.mtls_from_path(
                endpoint=self.endpoint,
                cert_filepath=self.cert_filepath,
                pri_key_filepath=self.pri_key_filepath,
                ca_filepath=self.ca_filepath,
                client_id=self.thing_name,
                clean_session=False,
                keep_alive_secs=6
            )
            
            print("Connecting to AWS IoT Core...")
            connect_future = self.mqtt_connection.connect()
            connect_future.result()
            print("Connected to AWS IoT Core!")
            return True
            
        except Exception as e:
            print(f"Failed to connect to IoT Core: {e}")
            return False
    
    def get_temporary_credentials(self):
        """Get temporary AWS credentials using IoT certificate"""
        try:
            # Create IoT client using certificate
            iot_client = boto3.client(
                'iot',
                region_name=self.aws_region,
                aws_access_key_id='',
                aws_secret_access_key='',
                aws_session_token=''
            )
            
            # Alternative approach: Use STS with certificate-based authentication
            # Create STS client
            sts_client = boto3.client('sts', region_name=self.aws_region)
            
            # Assume role using the certificate identity
            response = sts_client.assume_role_with_web_identity(
                RoleArn=self.role_arn,
                RoleSessionName=f"{self.thing_name}-session",
                WebIdentityToken=self._get_iot_token()
            )
            
            self.credentials = response['Credentials']
            print("Obtained temporary credentials")
            return True
            
        except Exception as e:
            print(f"Failed to get credentials: {e}")
            return False
    
    def _get_iot_token(self):
        """Get IoT token for role assumption"""
        # This is a simplified approach - in practice, you might need to 
        # implement a more sophisticated token exchange
        return "dummy-token"  # Replace with actual token logic
    
    def create_s3_client(self):
        """Create S3 client with temporary credentials"""
        try:
            if not self.credentials:
                # Alternative: Use IoT credentials provider
                session = boto3.Session()
                # Use the certificate for authentication
                self.s3_client = session.client(
                    's3',
                    region_name=self.aws_region,
                    aws_access_key_id=self.credentials['AccessKeyId'],
                    aws_secret_access_key=self.credentials['SecretAccessKey'],
                    aws_session_token=self.credentials['SessionToken']
                )
            else:
                self.s3_client = boto3.client(
                    's3',
                    region_name=self.aws_region,
                    aws_access_key_id=self.credentials['AccessKeyId'],
                    aws_secret_access_key=self.credentials['SecretAccessKey'],
                    aws_session_token=self.credentials['SessionToken']
                )
            
            print("S3 client created successfully")
            return True
            
        except Exception as e:
            print(f"Failed to create S3 client: {e}")
            return False
    
    def upload_file_to_s3(self, local_file_path, s3_key):
        """Upload a file to S3 bucket"""
        try:
            self.s3_client.upload_file(
                local_file_path, 
                self.s3_bucket_name, 
                s3_key
            )
            print(f"Successfully uploaded {local_file_path} to s3://{self.s3_bucket_name}/{s3_key}")
            return True
            
        except ClientError as e:
            print(f"Failed to upload file: {e}")
            return False
    
    def upload_data_to_s3(self, data, s3_key, content_type='text/plain'):
        """Upload data directly to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket_name,
                Key=s3_key,
                Body=data,
                ContentType=content_type
            )
            print(f"Successfully uploaded data to s3://{self.s3_bucket_name}/{s3_key}")
            return True
            
        except ClientError as e:
            print(f"Failed to upload data: {e}")
            return False
    
    def disconnect(self):
        """Clean up connections"""
        if self.mqtt_connection:
            disconnect_future = self.mqtt_connection.disconnect()
            disconnect_future.result()
            print("Disconnected from AWS IoT Core")

# Simplified version using direct certificate authentication
class SimpleIoTCertS3Uploader:
    def __init__(self, cert_path, key_path, ca_path, region='us-east-1'):
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_path = ca_path
        self.region = region
        
    def create_s3_client_with_cert_auth(self, role_arn, bucket_name):
        """Create S3 client using certificate-based authentication"""
        try:
            # Method 1: If you have IoT credentials provider configured
            session = boto3.Session()
            
            # Create custom SSL context with certificates
            ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            ssl_context.load_cert_chain(self.cert_path, self.key_path)
            ssl_context.load_verify_locations(self.ca_path)
            
            # Create STS client to assume role
            sts_client = boto3.client('sts', region_name=self.region)
            
            # Assume the role (this requires the role to trust the certificate)
            assumed_role = sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName='IoTCertificateSession'
            )
            
            # Create S3 client with temporary credentials
            s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
                aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
                aws_session_token=assumed_role['Credentials']['SessionToken']
            )
            
            return s3_client
            
        except Exception as e:
            print(f"Error creating S3 client: {e}")
            return None
    
    def upload_file(self, s3_client, local_file, bucket_name, s3_key):
        """Upload file to S3"""
        try:
