import logging
from dataclasses import dataclass
from typing import Optional

import yaml


@dataclass
class Config:
    site: str
    lon: float
    lat: float
    camera: str
    direction: str


class ConfigurationError(Exception):
    pass


def load_config(config_file: Optional[str] = "config.yaml") -> dict:
    try:
        with open(config_file, "r") as conf_file:
            config = yaml.safe_load(conf_file.read())
    except FileNotFoundError as err:
        logging.error(f"Configuration file not found at {config_file}")
        # TODO decide whether to exit or assume defaults, for now:
        raise ConfigurationError(err)

    except TypeError as err:
        logging.error(f"{config_file} did not contain all the information it needs")
        logging.error(err)
        raise ConfigurationError(err)

    return Config(**config)
