import pytest
from fastapi.testclient import TestClient

from match.config import get_config
from match.infra.api.security import create_access_token
from match.main import create_app


def build_headers(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


@pytest.fixture(scope="session")
def test_client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(scope="session")
def config():
    return get_config()
