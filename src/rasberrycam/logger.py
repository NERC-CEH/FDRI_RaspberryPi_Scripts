import logging
import logging.handlers
from pathlib import Path

from driutils.logger import LogFormatter


def setup_logging(filename: Path, level: int = logging.INFO) -> None:
    """
    Set up basic logging configuration with a custom formatter.

    This function configures the root logger with a StreamHandler and
    the custom LogFormatter. It removes any existing handlers before
    adding the new one.

    Args:
        filename: Path to the current log file
        level: The logging level to set for the root logger. Defaults to logging.INFO.

    Returns:
        None
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    formatter = LogFormatter()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = logging.handlers.TimedRotatingFileHandler(filename, when="W0", backupCount=4)
    file_handler.setFormatter(formatter)

    root_logger.handlers = [stream_handler, file_handler]
