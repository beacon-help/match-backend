import pytest

from match.app.service import MatchService
from match.domain.exceptions import RepositoryException
from match.infra.image_repository import LocalImageRepository
from match.infra.message_client import FakeMessageClient
from match.infra.repositories import InMemoryMatchRepository


@pytest.fixture
def service(tmp_path, config):
    return MatchService(
        user_messaging_client=FakeMessageClient(config=config),
        repository=InMemoryMatchRepository(),
        image_repository=LocalImageRepository(
            storage_dir=str(tmp_path / "imgs"), backend_host=config.BACKEND_HOST
        ),
        _fe_host=config.FE_HOST,
    )


def test_task_remove_image_keeps_file_when_persisting_fails(service, monkeypatch):
    task = service.task_add_images(task_id=100, owner_id=100, images=[b"fake image bytes"])
    image_id = task.images[0]

    def failing_task_update(task):
        raise RepositoryException("boom")

    monkeypatch.setattr(service.repository, "task_update", failing_task_update)

    with pytest.raises(RepositoryException):
        service.task_remove_image(task_id=100, owner_id=100, image_id=image_id)

    assert (service.image_repository.storage_dir / image_id).exists()
