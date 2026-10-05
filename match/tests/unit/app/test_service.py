from datetime import datetime, timedelta
from datetime import timezone as tz

import pytest

from match.app.exceptions import ImageNotFound
from match.app.service import MatchService
from match.domain.exceptions import RepositoryException, TaskNotFound, UserNotFound
from match.infra.image_repository import LocalImageRepository
from match.infra.message_client import FakeMessageClient
from match.infra.password_hasher import PwdlibPasswordHasher
from match.tests.fakes import (
    FakeUnitOfWork,
    InMemoryTaskRepository,
    InMemoryUserRepository,
    seeded_task_repository,
    seeded_user_repository,
)


@pytest.fixture
def service(tmp_path, config):
    return MatchService(
        user_messaging_client=FakeMessageClient(config=config),
        user_repository=seeded_user_repository(),
        task_repository=seeded_task_repository(),
        image_repository=LocalImageRepository(storage_dir=str(tmp_path / "imgs")),
        password_hasher=PwdlibPasswordHasher(),
        unit_of_work=FakeUnitOfWork(),
        _fe_host=config.FE_HOST,
    )


def test_task_remove_image_keeps_file_when_persisting_fails(service, monkeypatch):
    task = service.task_add_images(task_id=100, owner_id=100, images=[b"fake image bytes"])
    image_id = task.images[0]

    def failing_task_update(task):
        raise RepositoryException("boom")

    monkeypatch.setattr(service.task_repository, "task_update", failing_task_update)

    with pytest.raises(RepositoryException):
        service.task_remove_image(task_id=100, owner_id=100, image_id=image_id)

    assert (service.image_repository.storage_dir / image_id).exists()


def test_get_stats(service):
    task_stats, user_stats = service.get_stats()

    assert task_stats == {"total": 6, "successful": 1, "in_progress": 2}
    assert user_stats == {"total_helpers": 2, "total_help_seekers": 2}


def test_get_stats_empty(service):
    service.user_repository = InMemoryUserRepository()
    service.task_repository = InMemoryTaskRepository()

    task_stats, user_stats = service.get_stats()

    assert task_stats == {"total": 0, "successful": 0, "in_progress": 0}
    assert user_stats == {"total_helpers": 0, "total_help_seekers": 0}


def test_delete_user_hides_user_and_owned_tasks(service):
    service.delete_user(100)

    with pytest.raises(UserNotFound):
        service.get_user_by_id(100)
    with pytest.raises(TaskNotFound):
        service.get_task_by_id(100)
    assert service.get_tasks() == []
    assert service.get_stats() == (
        {"total": 0, "successful": 0, "in_progress": 0},
        {"total_helpers": 1, "total_help_seekers": 2},
    )


def test_users_referenced_by_task_skip_deleted_users(service):
    service.delete_user(101)

    users = service.get_users_referenced_by([service.get_task_by_id(102)])

    assert set(users) == {100}


def test_purge_deleted_users_respects_cutoff(service):
    task = service.task_add_images(task_id=100, owner_id=100, images=[b"fake image bytes"])
    image_path = service.image_repository.storage_dir / task.images[0]
    service.delete_user(100)
    service.delete_user(101)
    service.user_repository.users[100].deleted_at = datetime.now(tz.utc) - timedelta(days=31)

    purged = service.purge_deleted_users(datetime.now(tz.utc) - timedelta(days=30))

    assert purged == 1
    assert 100 not in service.user_repository.users
    assert service.user_repository.users[101].deleted_at is not None
    assert all(task.owner_id != 100 for task in service.task_repository.tasks.values())
    assert not image_path.exists()


def test_get_task_image_of_deleted_owner_raises_not_found(service):
    task = service.task_add_images(task_id=100, owner_id=100, images=[b"fake image bytes"])
    assert service.get_task_image(task.images[0]) == b"fake image bytes"

    service.delete_user(100)

    with pytest.raises(ImageNotFound):
        service.get_task_image(task.images[0])


def test_delete_user_commits_once(service):
    service.delete_user(100)

    assert service.unit_of_work.commits == 1
