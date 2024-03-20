"""
Plugin testing fixtures
"""

from pathlib import Path
import logging
import os
import sys

import pytest


logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def plugin_directory(request) -> Path:
    """
    pending.api plugin directory path object
    """
    repository_root_directory = Path(request.config.rootdir)
    plugin_directory_path = repository_root_directory.joinpath("plugins")
    assert plugin_directory_path.exists()
    return plugin_directory_path


@pytest.fixture(scope="session")
def configuration():
    test_plugin_directory = Path(__file__).parent
    plugin_file = test_plugin_directory.joinpath("test_config.py")
    sys.path.insert(0, str(plugin_file))
    os.environ["HUB_CONFIG"] = "test_config"
    yield
    sys.path.remove(str(plugin_file))
