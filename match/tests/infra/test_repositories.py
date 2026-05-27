import pytest

from match.domain.user import User
from match.domain.task import TaskStatus
from match.infra.repositories import InMemoryMatchRepository


@pytest.fixture(scope="function")
def in_memory_user_repository():
    return InMemoryMatchRepository(test_data=False)


def test_create_user(in_memory_user_repository):
    repository = in_memory_user_repository
    user_data = {
        "first_name": "Adam",
        "last_name": "Ondra",
        "email": "adam@example.com",
        "is_verified": False,
        "verification_code": None,
    }

    repository.create_user(user_data)

    user = repository.users[1]
    assert user == User(
        id=1,
        first_name="Adam",
        last_name="Ondra",
        email="adam@example.com",
        is_verified=False,
        verification_code=None,
    )
    assert len(repository.users) == 1


def test_get_tasks_can_filter_by_status():
    repository = InMemoryMatchRepository()

    tasks = repository.get_tasks({"status": TaskStatus.PENDING})

    assert len(tasks) == 1
    assert tasks[0].status == TaskStatus.PENDING


def test_get_tasks_can_filter_by_null_helper_id():
    repository = InMemoryMatchRepository()

    tasks = repository.get_tasks({"helper_id": None})

    assert len(tasks) == 1
    assert tasks[0].helper_id is None
