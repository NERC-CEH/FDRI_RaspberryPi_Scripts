from pathlib import Path

import pytest

from raspberrycam.config import Config, ConfigurationError, load_config


def test_config(config_file: str) -> None:
    config = load_config(config_file)
    assert isinstance(config, Config)
    assert config.site

    with pytest.raises(ConfigurationError):
        load_config("definitely_not_a_file.md")


def test_config_invalid(tmp_path: Path) -> None:
    with open(tmp_path / "bad_config.yml", "w") as out:
        out.write("site: 2323\nlon: 0")

    # Config dataclass will throw errors without all its fields set
    with pytest.raises(ConfigurationError):
        load_config(tmp_path / "bad_config.yml")
