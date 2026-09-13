import pytest
from fastapi.testclient import TestClient

from match import bootstrap
from match.config import get_config
from match.infra.api.security import create_access_token
from match.infra.image_repository import LocalImageRepository
from match.main import create_app


def build_headers(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


@pytest.fixture(scope="session")
def test_client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def image_storage_dir(tmp_path):
    storage_dir = tmp_path / "imgs"
    original = bootstrap.match_service.image_repository
    bootstrap.match_service.image_repository = LocalImageRepository(storage_dir=str(storage_dir))
    yield storage_dir
    bootstrap.match_service.image_repository = original


@pytest.fixture(scope="session")
def config():
    return get_config()
