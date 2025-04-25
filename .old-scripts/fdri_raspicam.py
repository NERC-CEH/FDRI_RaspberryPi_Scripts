Python 3.13.2 (tags/v3.13.2:4f8bb39, Feb  4 2025, 15:23:48) [MSC v.1942 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license()" for more information.
>>> import time
... import os
... import subprocess
... import boto3
... from botocore.exceptions import NoCredentialsError
... from datetime import datetime, timedelta
... import pytz
... from PIL import Image
... import io
... import glob
... import logging
... import math
... 
... # Configure logging
... logging.basicConfig(
...     level=logging.INFO,
...     format='%(asctime)s - %(levelname)s - %(message)s',
...     handlers=[
...         logging.FileHandler("/home/fdri/photo_uploader.log"),
...         logging.StreamHandler()
...     ]
... )
... logger = logging.getLogger()
... 
... # Configuration
... SAVE_DIRECTORY = "/home/fdri/test_photos"
... PENDING_DIRECTORY = "/home/fdri/pending_uploads"
... BUCKET_NAME = "fdriraspibucket"
... CAPTURE_INTERVAL = 300 # Capture interval in seconds
... UPLOAD_CHECK_INTERVAL = 1800 # Check for uploads every 30 minutes
... AWS_REGION = "eu-west-2" # Set your AWS region here
... AWS_ROLE_ARN = "arn:aws:iam::841162678585:role/AssumeRoleDriRaspberrycamUploader"
... 
... # Initial AWS Credentials (only used to assume role)
... # IMPORTANT: Replace these with your actual credentials
... # NOTE: You should use more secure methods in production
INITIAL_ACCESS_KEY = "AKIA4HWJT4E42JY5VE7S"
INITIAL_SECRET_KEY = "CeYu4+0L8pv/LyjLU+gPI4I1uS2wBACjck5iR++/"

# Image optimization settings
IMAGE_QUALITY = 85 # JPEG quality (1-100, lower means more compression)
MAX_IMAGE_WIDTH = 1024 # Maximum width of image in pixels
MAX_IMAGE_HEIGHT = 768 # Maximum height of image in pixels

# Location settings for sunrise/sunset calculation
# Replace with your actual location coordinates
LATITUDE = 51.6023  # Wallingford, England
LONGITUDE = -1.1125
TIMEZONE = "Europe/London"

def ensure_directory_exists(directory):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def check_internet_connection():
    """
    Check if internet connection is available
    Returns True if connected, False otherwise
    """
    try:
        # Verify internet access
        ping_result = subprocess.run(['ping', '-c', '2', '-W', '5', '8.8.8.8'],
                                    capture_output=True, text=True)
       
        if ping_result.returncode == 0:
            logger.info("Internet connection is active")
            return True
        else:
            logger.info("No internet access")
            return False
   
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking internet connection: {e}")
        return False

def ensure_internet_connection():
    """
    Attempt to ensure an internet connection is available
    Returns True if successful, False otherwise
    """
    # First check if we already have a connection
    if check_internet_connection():
        return True
        
    # Log information about network devices
    try:
        logger.info("No internet connection available. Gathering network information...")
        
        # Log active connections
        result = subprocess.run(['nmcli', 'device', 'status'],
                              capture_output=True, text=True)
        logger.info(f"Network devices:\n{result.stdout}")
        
        # List available connections
        result = subprocess.run(['nmcli', 'connection', 'show'],
                              capture_output=True, text=True)
        logger.info(f"Available connections:\n{result.stdout}")
        
        # Wait for a bit to let any auto-connections happen
        logger.info("Waiting 30 seconds for connection to establish...")
        time.sleep(30)
        
        # Check again
        if check_internet_connection():
            logger.info("Internet connection now available")
            return True
        else:
            logger.warning("Failed to establish internet connection")
            return False
            
    except Exception as e:
        logger.error(f"Error trying to establish internet connection: {e}")
        return False

def calculate_sunrise_sunset(latitude, longitude, timezone_str):
    """
    Calculate sunrise and sunset times using a simple algorithm
    Returns a dictionary with sunrise and sunset datetime objects
    """
    try:
        # Get the current date in the local timezone
        timezone = pytz.timezone(timezone_str)
        today = datetime.now(timezone).date()
        
        # Calculate day of year (1-366)
        day_of_year = today.timetuple().tm_yday
        
        # Convert latitude and longitude to radians
        lat_rad = math.radians(latitude)
        
        # Calculate solar declination
        declination = 0.4093 * math.sin(math.radians((2 * math.pi / 365) * (day_of_year - 81)))
        
        # Calculate sunrise and sunset hour angles
        cos_hour_angle = -math.tan(lat_rad) * math.tan(declination)
        
        # Handle edge cases near poles
        if cos_hour_angle > 1.0:  # Polar night
            return {"sunrise": None, "sunset": None}
        elif cos_hour_angle < -1.0:  # Midnight sun
            sunrise_time = datetime.combine(today, datetime.min.time())
            sunset_time = datetime.combine(today + timedelta(days=1), datetime.min.time())
            return {
                "sunrise": timezone.localize(sunrise_time),
                "sunset": timezone.localize(sunset_time)
            }
        
        # Calculate hour angle in radians
        hour_angle = math.acos(cos_hour_angle)
        
        # Convert to hours, adjusting for longitude
        hour_angle_deg = math.degrees(hour_angle)
        sunrise_hour = 12 - hour_angle_deg / 15 - longitude / 15
        sunset_hour = 12 + hour_angle_deg / 15 - longitude / 15
        
        # Adjust for time zone and DST (already handled by pytz)
        sunrise_hour_utc = (sunrise_hour + 24) % 24
        sunset_hour_utc = (sunset_hour + 24) % 24
        
        # Convert to datetime objects
        sunrise_hour_int = int(sunrise_hour_utc)
        sunrise_minute = int((sunrise_hour_utc - sunrise_hour_int) * 60)
        
        sunset_hour_int = int(sunset_hour_utc)
        sunset_minute = int((sunset_hour_utc - sunset_hour_int) * 60)
        
        sunrise_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=sunrise_hour_int, minutes=sunrise_minute)
        sunset_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=sunset_hour_int, minutes=sunset_minute)
        
        # Localize times
        sunrise_time = timezone.localize(sunrise_time)
        sunset_time = timezone.localize(sunset_time)
        
        logger.info(f"Calculated sunrise: {sunrise_time.strftime('%H:%M')}, sunset: {sunset_time.strftime('%H:%M')}")
        
        return {
            "sunrise": sunrise_time,
            "sunset": sunset_time
        }
    except Exception as e:
        logger.error(f"Error calculating sunrise/sunset: {e}")
        # Default to sunrise at 6 AM and sunset at 6 PM
        today = datetime.now(pytz.timezone(timezone_str)).date()
        sunrise_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=6)
        sunset_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=18)
        
        sunrise_time = pytz.timezone(timezone_str).localize(sunrise_time)
        sunset_time = pytz.timezone(timezone_str).localize(sunset_time)
        
        logger.info(f"Using default sunrise: {sunrise_time.strftime('%H:%M')}, sunset: {sunset_time.strftime('%H:%M')}")
        
        return {
            "sunrise": sunrise_time,
            "sunset": sunset_time
        }

def is_daytime():
    """
    Check if it's currently daytime based on sunrise and sunset times
    Returns True if it's daytime, False otherwise
    """
    try:
        # Get the current time in the local timezone
        timezone = pytz.timezone(TIMEZONE)
        now = datetime.now(timezone)
        
        # Calculate sunrise and sunset times
        sun_times = calculate_sunrise_sunset(LATITUDE, LONGITUDE, TIMEZONE)
        
        # If sun never rises or sets (polar regions), handle accordingly
        if sun_times["sunrise"] is None:
            logger.info("No sunrise/sunset today (polar night)")
            return False
        
        # Check if current time is between sunrise and sunset
        is_day = sun_times["sunrise"] <= now <= sun_times["sunset"]
        
        if is_day:
            logger.info(f"It's daytime (sunrise: {sun_times['sunrise'].strftime('%H:%M')}, sunset: {sun_times['sunset'].strftime('%H:%M')})")
        else:
            logger.info(f"It's nighttime (sunrise: {sun_times['sunrise'].strftime('%H:%M')}, sunset: {sun_times['sunset'].strftime('%H:%M')})")
        
        return is_day
    except Exception as e:
        logger.error(f"Error checking daytime: {e}")
        # Default to allowing photos if there's an error checking
        logger.info("Defaulting to daytime due to error")
        return True

def capture_image(filepath):
    """Capture an image using libcamera with lower resolution directly"""
    try:
        # Use libcamera-still with reduced resolution and quality
        command = f"libcamera-still --width {MAX_IMAGE_WIDTH} --height {MAX_IMAGE_HEIGHT} --quality {IMAGE_QUALITY} -o {filepath}"
        logger.info(f"Capturing image with command: {command}")
       
        os.system(command)
       
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath) / 1024 # KB
            logger.info(f"Image captured: {filepath} ({file_size:.2f}KB)")
            return True
        else:
            logger.error("Image capture failed: file not created")
            return False
    except Exception as e:
        logger.error(f"Error capturing image: {e}")
        return False

def optimize_image(input_path, output_path=None):
    """
    Optimize image for lower data usage
    Returns the path to the optimized image
    """
    if output_path is None:
        # Create a filename for the optimized image
        filename, ext = os.path.splitext(input_path)
        output_path = f"{filename}_optimized{ext}"
   
    try:
        # Open the image
        with Image.open(input_path) as img:
            # Convert to RGB if it's not already (to ensure JPEG compatibility)
            if img.mode != 'RGB':
                img = img.convert('RGB')
           
            # Calculate new dimensions while maintaining aspect ratio
            width, height = img.size
            if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
                # Calculate ratio to resize
                ratio = min(MAX_IMAGE_WIDTH / width, MAX_IMAGE_HEIGHT / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.LANCZOS)
           
            # Save with compression
            img.save(output_path, 'JPEG', quality=IMAGE_QUALITY, optimize=True)
           
            # Get file size for logging
            original_size = os.path.getsize(input_path) / 1024 # KB
            optimized_size = os.path.getsize(output_path) / 1024 # KB
            logger.info(f"Image optimized: {original_size:.2f}KB → {optimized_size:.2f}KB ({(1 - optimized_size/original_size)*100:.1f}% reduction)")
           
            return output_path
    except Exception as e:
        logger.error(f"Error optimizing image: {e}")
        return input_path # Return original path if optimization fails

def assume_role():
    """
    Assume the AWS IAM role for S3 access
    Returns session credentials dictionary or None if failed
    """
    try:
        logger.info(f"Attempting to assume role: {AWS_ROLE_ARN}")
        
        # Create a boto3 STS client with initial credentials
        sts_client = boto3.client(
            'sts', 
            region_name=AWS_REGION,
            aws_access_key_id=INITIAL_ACCESS_KEY,
            aws_secret_access_key=INITIAL_SECRET_KEY
        )
        
        # Assume the role
        assumed_role = sts_client.assume_role(
    RoleArn=AWS_ROLE_ARN,
    RoleSessionName="rasberrycam-upload",
    DurationSeconds=3600 # 1 hour
        )
        
        credentials = assumed_role['Credentials']
        logger.info("Successfully assumed role")
        
        return {
            'aws_access_key_id': credentials['AccessKeyId'],
            'aws_secret_access_key': credentials['SecretAccessKey'],
            'aws_session_token': credentials['SessionToken']
        }
    except Exception as e:
        logger.error(f"Error assuming role: {e}")
        return None

def check_bucket_exists(s3_client, bucket_name):
    """
    Check if an S3 bucket exists
    """
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info(f"Bucket {bucket_name} exists")
        return True
    except s3_client.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            logger.error(f"Bucket {bucket_name} does not exist")
        else:
            logger.error(f"Error checking bucket {bucket_name}: {e}")
        return False

def create_bucket(s3_client, bucket_name):
    """
    Create an S3 bucket in the specified region
    """
    try:
        location = {'LocationConstraint': AWS_REGION}
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration=location
        )
        logger.info(f"Bucket {bucket_name} created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating bucket {bucket_name}: {e}")
        return False

def upload_to_s3(file_path, bucket_name, object_name=None):
    """
    Upload a file to an S3 bucket with minimal data usage
    """
    # If S3 object_name was not specified, use file_path
    if object_name is None:
        object_name = os.path.basename(file_path)
  
    # Generate a timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    object_name = f"images/{timestamp}_{object_name}"
  
    try:
        # Assume role to get temporary credentials
        role_credentials = assume_role()
        if not role_credentials:
            logger.error("Failed to assume role, cannot upload to S3")
            return False
        
        # Create S3 client with role credentials and reduced part size for multipart uploads
        s3_client = boto3.client(
            's3', 
            region_name=AWS_REGION,
            aws_access_key_id=role_credentials['aws_access_key_id'],
            aws_secret_access_key=role_credentials['aws_secret_access_key'],
            aws_session_token=role_credentials['aws_session_token'],
            config=boto3.session.Config(
                s3={'multipart_threshold': 10 * 1024 * 1024} # Only use multipart for files >10MB
            )
        )
       
        # Check if bucket exists
        if not check_bucket_exists(s3_client, bucket_name):
            logger.info(f"Attempting to create bucket {bucket_name}")
            if not create_bucket(s3_client, bucket_name):
                logger.error(f"Cannot upload to non-existent bucket: {bucket_name}")
                return False
        
        # Upload the file
        file_size = os.path.getsize(file_path) / 1024
        logger.info(f"Uploading file to S3 ({file_size:.2f}KB): {file_path}")
        
        # Create the images/ directory if it doesn't exist
        try:
            s3_client.put_object(Bucket=bucket_name, Key="images/")
            logger.info(f"Created images/ directory in bucket {bucket_name}")
        except Exception as e:
            # It's okay if this fails, might already exist
            pass
            
        s3_client.upload_file(
            file_path,
            bucket_name,
            object_name,
            ExtraArgs={'StorageClass': 'STANDARD'} # Use standard storage class
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

def process_pending_uploads():
    """
    Process any pending uploads in the pending directory
    Returns the number of successfully uploaded files
    """
    if not ensure_internet_connection():
        logger.info("Cannot process pending uploads: internet connection unavailable")
        return 0
   
    # Find all pending images (.jpg files)
    pending_files = glob.glob(os.path.join(PENDING_DIRECTORY, "*.jpg"))
   
    if not pending_files:
        logger.info("No pending uploads found")
        return 0
   
    logger.info(f"Found {len(pending_files)} pending uploads to process")
    successful_uploads = 0
   
    # Sort files by creation time (oldest first)
    pending_files.sort(key=os.path.getctime)
   
    for file_path in pending_files:
        # Upload to S3
        if upload_to_s3(file_path, BUCKET_NAME):
            # Remove file after successful upload
            os.remove(file_path)
            successful_uploads += 1
            logger.info(f"Successfully uploaded and removed: {file_path}")
        else:
            logger.warning(f"Failed to upload: {file_path}")
            # Don't try to upload more files if one fails - might be a connection issue
            break
   
    logger.info(f"Completed processing pending uploads. Success: {successful_uploads}/{len(pending_files)}")
    return successful_uploads

def main():
    # Ensure directories exist
    ensure_directory_exists(SAVE_DIRECTORY)
    ensure_directory_exists(PENDING_DIRECTORY)
   
    logger.info("Starting image capture and upload service")
   
    last_upload_check = 0 # Track when we last checked for uploads
   
    # Continuous loop to capture and queue images for upload
    while True:
        try:
            current_time = time.time()
            
            # Check if it's daytime before capturing an image
            if is_daytime():
                # Capture image
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                raw_image_path = os.path.join(SAVE_DIRECTORY, f"raw_image_{timestamp}.jpg")
               
                if capture_image(raw_image_path):
                    # Optimize the image and move to pending directory
                    optimized_image_path = os.path.join(PENDING_DIRECTORY, f"optimized_{timestamp}.jpg")
                    optimize_image(raw_image_path, optimized_image_path)
                   
                    # Remove the raw image to save space
                    os.remove(raw_image_path)
                    logger.info(f"Raw image removed: {raw_image_path}")
            else:
                logger.info("Skipping image capture: it's nighttime")
           
            # Check if it's time to process pending uploads
            # (we still process uploads at night, just don't capture new images)
            if current_time - last_upload_check >= UPLOAD_CHECK_INTERVAL:
                logger.info("Checking for pending uploads...")
                process_pending_uploads()
                last_upload_check = current_time
           
            # Wait for the specified interval before next capture
            sleep_time = CAPTURE_INTERVAL
            logger.info(f"Waiting {sleep_time} seconds until next capture/check...")
            time.sleep(sleep_time)
       
        except Exception as e:
            logger.error(f"An error occurred in main loop: {e}")
            # Wait for a short time before retrying
            time.sleep(10)

if __name__ == "__main__":
    main()
