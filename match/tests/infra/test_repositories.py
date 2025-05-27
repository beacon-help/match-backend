import pytest

from match.domain.user import User
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
