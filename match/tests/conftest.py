import os
import tempfile
from pathlib import Path

# The engine is created when match.db is imported, so the test database must be configured first.
_test_dir = Path(tempfile.mkdtemp(prefix="match-tests-"))
_local_config = _test_dir / "config.local.yaml"
_local_config.write_text(f"backend:\n  db_path: {_test_dir / 'test.db'}\n")
os.environ["MATCH_CONFIG_LOCAL"] = str(_local_config)

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient

from match import bootstrap
from match.config import get_config
from match.infra.api.security import create_access_token
from match.infra.image_repository import LocalImageRepository
from match.main import create_app


def build_headers(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    alembic_config = AlembicConfig()
    alembic_config.set_main_option("script_location", "match/alembic")
    command.upgrade(alembic_config, "head")


@pytest.fixture(scope="session")
def test_client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def image_storage_dir(tmp_path, monkeypatch):
    storage_dir = tmp_path / "imgs"
    monkeypatch.setattr(
        bootstrap, "image_repository", LocalImageRepository(storage_dir=str(storage_dir))
    )
    return storage_dir


@pytest.fixture(scope="session")
def config():
    return get_config()
