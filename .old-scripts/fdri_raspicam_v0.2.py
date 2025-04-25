import time
import os
import subprocess
import boto3
from botocore.exceptions import NoCredentialsError
from datetime import datetime, timedelta
import pytz
from PIL import Image
import glob
import logging
import signal

# Import astral for sunrise/sunset calculations
from astral import LocationInfo
from astral.sun import sun

# Configuration
BASE_DIRECTORY = "/home"
SAVE_DIRECTORY = f"{BASE_DIRECTORY}/fdri/test_photos"
PENDING_DIRECTORY = f"{BASE_DIRECTORY}/fdri/pending_uploads"
BUCKET_NAME = "ukceh-fdri-staging-rasberrycam"
CAPTURE_INTERVAL_DAY = 300  # Capture interval in seconds during day (5 min)
CAPTURE_INTERVAL_NIGHT = 1800  # Longer interval at nightf (30 min)
AWS_REGION = os.environ["AWS_REGION"]  # Set your AWS region here
AWS_ROLE_ARN = os.environ["AWS_ROLE_ARN"]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"{BASE_DIRECTORY}/photo_uploader.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger()

# Initial AWS Credentials (only used to assume role)
# IMPORTANT: Replace these with your actual credentials
# NOTE: You should use more secure methods in production

AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]

# Image optimization settings
IMAGE_QUALITY = 85  # JPEG quality (1-100, lower means more compression)
MAX_IMAGE_WIDTH = 1024  # Maximum width of image in pixels
MAX_IMAGE_HEIGHT = 768  # Maximum height of image in pixels

# Location settings for sunrise/sunset calculation
# Replace with your actual location coordinates
LATITUDE = 51.6023  # Wallingford, England
LONGITUDE = -1.1125
TIMEZONE = "Europe/London"
CITY_NAME = "Wallingford"  # Location name for Astral

# Power management
ENABLE_LOW_POWER_MODE = True
ENABLE_AUTO_SHUTDOWN = True
SHUTDOWN_NIGHT_MODE = True
SHUTDOWN_COMMAND = "sudo shutdown -h now"  # Command to shutdown the Pi
CPU_GOV_COMMAND = (
    "echo {0} | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
)
PRE_SUNRISE_WAKEUP = 15  # Minutes to wake up before sunrise
POST_SUNSET_SLEEP = 15  # Minutes to keep running after sunset

# Upload settings
IMMEDIATE_UPLOAD = True  # Attempt to upload immediately after capture
USE_PENDING_DIRECTORY = True  # Store in pending directory if upload fails

# Global state
running = True
next_wakeup_time = None


def signal_handler(sig, frame):
    """Handle Ctrl+C and other termination signals"""
    global running
    logger.info("Shutdown signal received. Exiting gracefully...")
    running = False


# Register signal handlers for graceful termination
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


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
        # Verify internet access with fewer pings (1 instead of 2)
        ping_result = subprocess.run(
            ["ping", "-c", "1", "-W", "3", "8.8.8.8"], capture_output=True, text=True
        )

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
        logger.info(
            "No internet connection available. Gathering network information..."
        )

        # Log active connections
        result = subprocess.run(
            ["nmcli", "device", "status"], capture_output=True, text=True
        )
        logger.info(f"Network devices:\n{result.stdout}")

        # Shorter wait time for connections to establish
        logger.info("Waiting 15 seconds for connection to establish...")
        time.sleep(15)

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
    Calculate sunrise and sunset times using the astral library
    Returns a dictionary with sunrise and sunset datetime objects
    """
    try:
        # Create a location object
        location = LocationInfo(
            name=CITY_NAME,
            region="England",
            timezone=timezone_str,
            latitude=latitude,
            longitude=longitude,
        )

        # Get the timezone
        tz = pytz.timezone(timezone_str)

        # Get today's date
        today = datetime.now(tz).date()

        # Calculate sun information for today
        s = sun(location.observer, date=today, tzinfo=tz)

        # Extract sunrise and sunset times
        sunrise_time = s["sunrise"]
        sunset_time = s["sunset"]

        # Calculate tomorrow's sunrise for overnight scheduling
        tomorrow = today + timedelta(days=1)
        tomorrow_s = sun(location.observer, date=tomorrow, tzinfo=tz)
        tomorrow_sunrise = tomorrow_s["sunrise"]

        logger.info(
            f"Calculated sunrise: {sunrise_time.strftime('%H:%M')}, sunset: {sunset_time.strftime('%H:%M')}"
        )
        logger.info(f"Tomorrow's sunrise: {tomorrow_sunrise.strftime('%H:%M')}")

        return {
            "sunrise": sunrise_time,
            "sunset": sunset_time,
            "tomorrow_sunrise": tomorrow_sunrise,
        }
    except Exception as e:
        logger.error(f"Error calculating sunrise/sunset with astral: {e}")
        # Default to sunrise at 6 AM and sunset at 6 PM if there's an error
        today = datetime.now(pytz.timezone(timezone_str)).date()
        tomorrow = today + timedelta(days=1)

        sunrise_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=6)
        sunset_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=18)
        tomorrow_sunrise = datetime.combine(tomorrow, datetime.min.time()) + timedelta(
            hours=6
        )

        sunrise_time = pytz.timezone(timezone_str).localize(sunrise_time)
        sunset_time = pytz.timezone(timezone_str).localize(sunset_time)
        tomorrow_sunrise = pytz.timezone(timezone_str).localize(tomorrow_sunrise)

        logger.info(
            f"Using default sunrise: {sunrise_time.strftime('%H:%M')}, sunset: {sunset_time.strftime('%H:%M')}"
        )

        return {
            "sunrise": sunrise_time,
            "sunset": sunset_time,
            "tomorrow_sunrise": tomorrow_sunrise,
        }


def is_daytime(sun_times=None):
    """
    Check if it's currently daytime based on sunrise and sunset times
    Returns True if it's daytime, False otherwise
    """
    try:
        # Get the current time in the local timezone
        timezone = pytz.timezone(TIMEZONE)
        now = datetime.now(timezone)

        # Calculate sunrise and sunset times if not provided
        if sun_times is None:
            sun_times = calculate_sunrise_sunset(LATITUDE, LONGITUDE, TIMEZONE)

        # Adjust for early wakeup and late sleep
        adjusted_sunrise = sun_times["sunrise"] - timedelta(minutes=PRE_SUNRISE_WAKEUP)
        adjusted_sunset = sun_times["sunset"] + timedelta(minutes=POST_SUNSET_SLEEP)

        # Check if current time is between sunrise and sunset
        is_day = adjusted_sunrise <= now <= adjusted_sunset

        if is_day:
            logger.info(
                f"It's operating time (adjusted sunrise: {adjusted_sunrise.strftime('%H:%M')}, "
                f"adjusted sunset: {adjusted_sunset.strftime('%H:%M')})"
            )
        else:
            logger.info(
                f"It's outside operating hours (adjusted sunrise: {adjusted_sunrise.strftime('%H:%M')}, "
                f"adjusted sunset: {adjusted_sunset.strftime('%H:%M')})"
            )

        return is_day
    except Exception as e:
        logger.error(f"Error checking daytime: {e}")
        # Default to allowing photos if there's an error checking
        logger.info("Defaulting to daytime due to error")
        return True


def time_until_sunrise(sun_times=None):
    """Calculate seconds until next sunrise (including tomorrow)"""
    try:
        # Get the current time in the local timezone
        timezone = pytz.timezone(TIMEZONE)
        now = datetime.now(timezone)

        # Calculate sunrise and sunset times if not provided
        if sun_times is None:
            sun_times = calculate_sunrise_sunset(LATITUDE, LONGITUDE, TIMEZONE)

        # Adjust for early wakeup
        adjusted_sunrise = sun_times["sunrise"] - timedelta(minutes=PRE_SUNRISE_WAKEUP)
        adjusted_tomorrow_sunrise = sun_times["tomorrow_sunrise"] - timedelta(
            minutes=PRE_SUNRISE_WAKEUP
        )

        # If it's after today's sunrise, use tomorrow's sunrise
        if now > adjusted_sunrise:
            next_sunrise = adjusted_tomorrow_sunrise
        else:
            next_sunrise = adjusted_sunrise

        # Calculate seconds until sunrise
        seconds_until = (next_sunrise - now).total_seconds()

        # Ensure it's at least 60 seconds to avoid immediate wakeup
        seconds_until = max(seconds_until, 60)

        logger.info(
            f"Next sunrise at {next_sunrise.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"{seconds_until/60:.1f} minutes from now"
        )

        return seconds_until
    except Exception as e:
        logger.error(f"Error calculating time until sunrise: {e}")
        # Default to 6 hours if there's an error
        return 6 * 3600


def set_cpu_governor(mode="ondemand"):
    """Set CPU governor to save power"""
    if not ENABLE_LOW_POWER_MODE:
        return

    try:
        # Valid modes: performance, powersave, userspace, ondemand, conservative
        # - powersave: Minimum frequency, save power
        # - ondemand: Scale frequency based on CPU load
        # - performance: Maximum frequency, best performance

        command = CPU_GOV_COMMAND.format(mode)
        logger.info(f"Setting CPU governor to {mode}")
        subprocess.run(command, shell=True)
    except Exception as e:
        logger.error(f"Failed to set CPU governor: {e}")


def turn_off_camera():
    """Disable the camera module to save power"""
    try:
        if os.path.exists("/sys/modules/bcm2835_v4l2"):
            logger.info("Turning off camera module")
            subprocess.run("sudo rmmod bcm2835-v4l2", shell=True)
            subprocess.run("sudo rmmod bcm2835-isp", shell=True)
    except Exception as e:
        logger.error(f"Failed to turn off camera: {e}")


def turn_on_camera():
    """Enable the camera module"""
    try:
        logger.info("Ensuring camera module is on")
        subprocess.run("sudo modprobe bcm2835-v4l2", shell=True)
    except Exception as e:
        logger.error(f"Failed to turn on camera: {e}")


def schedule_wakeup(seconds_until_wakeup):
    """Schedule system to wake up after shutdown"""
    global next_wakeup_time

    try:
        # Calculate wake time
        wake_time = datetime.now() + timedelta(seconds=seconds_until_wakeup)
        next_wakeup_time = wake_time

        # Format for rtcwake (seconds since epoch)
        epoch_time = int(wake_time.timestamp())

        # Schedule wake using rtcwake
        logger.info(f"Scheduling wakeup at {wake_time.strftime('%Y-%m-%d %H:%M:%S')}")
        subprocess.run(f"sudo rtcwake -m no -t {epoch_time}", shell=True)

        return True
    except Exception as e:
        logger.error(f"Failed to schedule wakeup: {e}")
        return False


def shutdown_system():
    """Shutdown the Raspberry Pi to save power"""
    if not ENABLE_AUTO_SHUTDOWN:
        logger.info("Auto shutdown disabled, not shutting down")
        return

    try:
        logger.info("Initiating system shutdown")
        # Final sync to make sure all data is written
        subprocess.run("sync", shell=True)

        # Execute shutdown command
        subprocess.run(SHUTDOWN_COMMAND, shell=True)
    except Exception as e:
        logger.error(f"Failed to shutdown: {e}")


def capture_image(filepath):
    """Capture an image using libcamera with lower resolution directly"""
    try:
        # Turn on camera if needed
        turn_on_camera()

        # Use libcamera-still with reduced resolution and quality
        command = f"libcamera-still --width {MAX_IMAGE_WIDTH} --height {MAX_IMAGE_HEIGHT} --quality {IMAGE_QUALITY} -o {filepath}"
        logger.info(f"Capturing image with command: {command}")

        os.system(command)

        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath) / 1024  # KB
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
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Calculate new dimensions while maintaining aspect ratio
            width, height = img.size
            if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
                # Calculate ratio to resize
                ratio = min(MAX_IMAGE_WIDTH / width, MAX_IMAGE_HEIGHT / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.LANCZOS)

            # Save with compression
            img.save(output_path, "JPEG", quality=IMAGE_QUALITY, optimize=True)

            # Get file size for logging
            original_size = os.path.getsize(input_path) / 1024  # KB
            optimized_size = os.path.getsize(output_path) / 1024  # KB
            logger.info(
                f"Image optimized: {original_size:.2f}KB → {optimized_size:.2f}KB ({(1 - optimized_size/original_size)*100:.1f}% reduction)"
            )

            return output_path
    except Exception as e:
        logger.error(f"Error optimizing image: {e}")
        return input_path  # Return original path if optimization fails


def assume_role():
    """
    Assume the AWS IAM role for S3 access
    Returns session credentials dictionary or None if failed
    """
    try:
        logger.info(f"Attempting to assume role: {AWS_ROLE_ARN}")

        # Create a boto3 STS client with initial credentials
        sts_client = boto3.client(
            "sts",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )

        # Assume the role
        assumed_role = sts_client.assume_role(
            RoleArn=AWS_ROLE_ARN,
            RoleSessionName="rasberrycam-upload",
            DurationSeconds=3600,  # 1 hour
        )

        credentials = assumed_role["Credentials"]
        logger.info("Successfully assumed role")

        return {
            "aws_access_key_id": credentials["AccessKeyId"],
            "aws_secret_access_key": credentials["SecretAccessKey"],
            "aws_session_token": credentials["SessionToken"],
        }
    except Exception as e:
        logger.error(f"Error assuming role: {e}")
        return None


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
            "s3",
            region_name=AWS_REGION,
            aws_access_key_id=role_credentials["aws_access_key_id"],
            aws_secret_access_key=role_credentials["aws_secret_access_key"],
            aws_session_token=role_credentials["aws_session_token"],
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

    # Set to performance mode for faster uploads
    set_cpu_governor("performance")

    # Only process a maximum of 10 files at a time to avoid high power usage
    batch_size = min(10, len(pending_files))
    files_to_process = pending_files[:batch_size]
    logger.info(f"Processing batch of {len(files_to_process)} files")

    for file_path in files_to_process:
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

    # Set back to power-saving mode
    set_cpu_governor("ondemand")

    logger.info(
        f"Completed processing pending uploads. Success: {successful_uploads}/{len(files_to_process)}"
    )
    return successful_uploads


def capture_and_upload():
    """
    Capture, optimize, and handle the image (upload immediately or save to pending)
    Returns True if full process was successful, False otherwise
    """
    # Temporarily set to performance mode for faster image processing
    set_cpu_governor("performance")

    # Capture image
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    raw_image_path = os.path.join(SAVE_DIRECTORY, f"raw_image_{timestamp}.jpg")

    capture_success = capture_image(raw_image_path)
    if not capture_success:
        logger.error("Failed to capture image")
        set_cpu_governor("ondemand")  # Return to power saving mode
        return False

    # Optimize the image
    optimized_image_path = os.path.join(SAVE_DIRECTORY, f"optimized_{timestamp}.jpg")
    optimized_path = optimize_image(raw_image_path, optimized_image_path)

    # Try to upload immediately if configured
    upload_success = False
    if IMMEDIATE_UPLOAD and ensure_internet_connection():
        upload_success = upload_to_s3(optimized_path, BUCKET_NAME)

        if upload_success:
            logger.info("Image uploaded immediately to S3")

            # Clean up files after successful upload
            try:
                os.remove(raw_image_path)
                os.remove(optimized_path)
                logger.info(f"Temporary files removed after successful upload")
            except Exception as e:
                logger.error(f"Error removing temporary files: {e}")

    # If immediate upload failed or is not configured, save to pending directory
    if not upload_success and USE_PENDING_DIRECTORY:
        pending_path = os.path.join(PENDING_DIRECTORY, f"pending_{timestamp}.jpg")
        try:
            # Move the optimized image to pending directory
            os.rename(optimized_path, pending_path)
            logger.info(f"Image saved to pending directory: {pending_path}")

            # Remove raw image to save space
            os.remove(raw_image_path)
            logger.info(f"Raw image removed: {raw_image_path}")
        except Exception as e:
            logger.error(f"Error saving to pending directory: {e}")
            set_cpu_governor("ondemand")  # Return to power saving mode
            return False

    # Turn off camera to save power
    turn_off_camera()

    # Return to power saving mode
    set_cpu_governor("ondemand")

    return True


def main():
    global running

    # Ensure directories exist
    ensure_directory_exists(SAVE_DIRECTORY)
    ensure_directory_exists(PENDING_DIRECTORY)

    logger.info("Starting power-optimized camera service with immediate upload")

    # Set initial power saving mode
    set_cpu_governor("ondemand")

    last_upload_check = 0  # Track when we last checked for pending uploads
    sun_times = calculate_sunrise_sunset(
        LATITUDE, LONGITUDE, TIMEZONE
    )  # Get sunrise/sunset times once

    # Main loop
    while running:
        try:
            current_time = time.time()

            # Re-calculate sun times at midnight or when they're not available
            current_hour = datetime.now().hour
            if current_hour == 0 or not sun_times:
                sun_times = calculate_sunrise_sunset(LATITUDE, LONGITUDE, TIMEZONE)

            # Set the appropriate mode based on time of day
            day_mode = is_daytime(sun_times)

            if day_mode:
                # Day mode operation
                capture_interval = CAPTURE_INTERVAL_DAY

                # Capture and upload image
                logger.info("Starting capture and upload process...")
                if capture_and_upload():
                    logger.info("Image successfully processed")
                else:
                    logger.warning("Failed to process image")
            else:
                # Night mode operation
                capture_interval = CAPTURE_INTERVAL_NIGHT
                logger.info("Skipping image capture: it's nighttime")

                # If auto shutdown is enabled for night, schedule wakeup and shut down
                if SHUTDOWN_NIGHT_MODE:
                    seconds_to_sunrise = time_until_sunrise(sun_times)

                    # Only shutdown if we have more than 30 minutes until sunrise
                    if seconds_to_sunrise > 1800:
                        # Schedule wakeup
                        if schedule_wakeup(seconds_to_sunrise):
                            # Upload any pending files before shutdown
                            process_pending_uploads()
                            # Shutdown
                            shutdown_system()
                            # Exit loop - system should be shutting down
                            break

            # Check if it's time to process any pending uploads
            if current_time - last_upload_check >= capture_interval * 3:
                logger.info("Checking for pending uploads...")
                process_pending_uploads()
                last_upload_check = current_time

            # Wait for the specified interval before next capture
            logger.info(f"Waiting {capture_interval} seconds until next check...")

            # Instead of a single sleep, do multiple short sleeps to check for termination
            for _ in range(capture_interval // 5):
                if not running:
                    break
                time.sleep(5)

            # For any remainder time
            if running and capture_interval % 5 > 0:
                time.sleep(capture_interval % 5)

        except Exception as e:
            logger.error(f"An error occurred in main loop: {e}")
            # Wait for a short time before retrying
            time.sleep(10)

    logger.info("Program terminating cleanly")


if __name__ == "__main__":
    main()
