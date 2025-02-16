import pytest

from match.domain.user import User
from match.infra.api.repositories import InMemoryUserRepository


@pytest.fixture(scope="function")
def in_memory_user_repository():
    return InMemoryUserRepository()


def test_create_user(in_memory_user_repository):
    repository = in_memory_user_repository
    user_data = {"first_name": "Adam", "last_name": "Ondra"}

    repository.create_user(user_data)

    user = repository.users[1]
    assert user == User(id=1, first_name="Adam", last_name="Ondra")
    assert len(repository.users) == 1
