import logging

from match.main import get_config


def test_get_config():
    config = get_config()
    assert config.ENV
