import pytest
from fastapi.testclient import TestClient

from match.config import get_config
from match.main import create_app


@pytest.fixture(scope="session")
def test_client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(scope="session")
def config():
    return get_config()
