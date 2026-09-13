import tempfile

import pytest

from match.infra.image_repository import LocalImageRepository


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def image_repository(temp_storage):
    return LocalImageRepository(storage_dir=temp_storage)


def test_upload_creates_file(image_repository):
    image_data = b"fake image data"

    image_id = image_repository.upload(image_data)

    assert (image_repository.storage_dir / image_id).read_bytes() == image_data


def test_upload_same_content_gets_distinct_ids(image_repository):
    first_id = image_repository.upload(b"same bytes")
    second_id = image_repository.upload(b"same bytes")

    assert first_id != second_id


def test_read_returns_bytes_by_id(image_repository):
    first_id = image_repository.upload(b"image one")
    second_id = image_repository.upload(b"image two")

    result = image_repository.read([first_id, second_id])

    assert result == {first_id: b"image one", second_id: b"image two"}


def test_delete_removes_file(image_repository):
    image_id = image_repository.upload(b"image to delete")

    image_repository.delete(image_id)

    assert not (image_repository.storage_dir / image_id).exists()


def test_delete_missing_file_does_not_error(image_repository):
    image_repository.delete("does-not-exist")
