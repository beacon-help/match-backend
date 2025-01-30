import pytest
from fastapi.testclient import TestClient

from match.main import create_app


@pytest.fixture(scope="session")
def test_client():
    app = create_app()
    return TestClient(app)
