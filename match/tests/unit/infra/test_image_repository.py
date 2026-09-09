import tempfile
from pathlib import Path

import pytest

from match.infra.image_repository import LocalImageRepository


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def image_repository(temp_storage):
    return LocalImageRepository(storage_dir=temp_storage)


def test_upload_creates_file(image_repository, temp_storage):
    image_data = b"fake image data"

    file_path = image_repository.upload(image_data)

    assert Path(file_path).exists()
    assert Path(file_path).read_bytes() == image_data


def test_upload_returns_path_string(image_repository):
    image_data = b"test image"

    result = image_repository.upload(image_data)

    assert isinstance(result, str)
    assert result.startswith(image_repository.storage_dir.as_posix())


def test_delete_removes_file(image_repository):
    image_data = b"image to delete"
    file_path = image_repository.upload(image_data)

    image_repository.delete(file_path)

    assert not Path(file_path).exists()


def test_delete_missing_file_does_not_error(image_repository):
    image_repository.delete("/nonexistent/path")
