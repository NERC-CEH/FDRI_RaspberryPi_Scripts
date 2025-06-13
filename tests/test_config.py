import pytest

from raspberrycam.config import load_config


def test_config(config_file: str) -> None:
    conf_data = load_config(config_file)
    assert "site" in conf_data

    with pytest.raises(FileNotFoundError):
        conf_null = load_config("definitely_not_a_file.md")
        assert "site" in conf_null
