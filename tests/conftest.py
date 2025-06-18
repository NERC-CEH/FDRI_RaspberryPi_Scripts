from pathlib import Path

import pytest


@pytest.fixture
def config_file() -> Path:
    return Path(__file__).parent.resolve() / "../config/config.yaml"
