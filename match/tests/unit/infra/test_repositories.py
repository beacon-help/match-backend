import pytest

from match.domain.exceptions import EmailAlreadyRegistered
from match.domain.task import TaskStatus
from match.domain.user import User, UserType
from match.infra.repositories import InMemoryMatchRepository
from match.tests.fakes import seeded_in_memory_repository


@pytest.fixture(scope="function")
def in_memory_user_repository():
    return InMemoryMatchRepository()


def test_create_user(in_memory_user_repository):
    repository = in_memory_user_repository
    user_data = {
        "user_type": UserType.HELP_SEEKER,
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
        user_type=UserType.HELP_SEEKER,
        first_name="Adam",
        last_name="Ondra",
        email="adam@example.com",
        is_verified=False,
        verification_code=None,
    )
    assert len(repository.users) == 1


def test_get_tasks_can_filter_by_status():
    repository = seeded_in_memory_repository()

    tasks = repository.get_tasks({"status": TaskStatus.PENDING})

    assert len(tasks) == 1
    assert tasks[0].status == TaskStatus.PENDING


def test_get_tasks_can_filter_by_null_helper_id():
    repository = seeded_in_memory_repository()

    tasks = repository.get_tasks({"helper_id": None})

    assert len(tasks) == 1
    assert tasks[0].helper_id is None


def test_count_tasks_by_status():
    repository = seeded_in_memory_repository()

    assert repository.count_tasks_by_status() == {status: 1 for status in TaskStatus}


def test_count_users_by_type():
    repository = seeded_in_memory_repository()

    assert repository.count_users_by_type() == {UserType.VOLUNTEER: 2, UserType.HELP_SEEKER: 2}


def test_create_user_rejects_registered_email(in_memory_user_repository):
    user_data = {
        "user_type": UserType.HELP_SEEKER,
        "first_name": "Adam",
        "last_name": "Ondra",
        "email": "adam@example.com",
    }
    in_memory_user_repository.create_user(user_data)

    with pytest.raises(EmailAlreadyRegistered):
        in_memory_user_repository.create_user(user_data)
