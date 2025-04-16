import logging
import os
import subprocess
import time

logger = logging.getLogger(__name__)


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
        ping_result = subprocess.run(["ping", "-c", "1", "-W", "3", "8.8.8.8"], capture_output=True, text=True)

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
        result = subprocess.run(["nmcli", "device", "status"], capture_output=True, text=True)
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
