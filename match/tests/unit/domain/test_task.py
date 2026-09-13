import pytest

from match.domain.exceptions import DomainException, InvalidTaskAction
from match.domain.task import Category, Task
from match.domain.user import User, UserType


def build_user(id, first_name="John"):
    return User(
        id=id,
        user_type=UserType.HELP_SEEKER,
        first_name=first_name,
        last_name="Test",
        email=f"user{id}@example.com",
        is_verified=True,
        verification_code=None,
    )


def build_task(owner):
    return Task.create_task(
        owner=owner,
        title="title",
        description="description",
        category=Category.OTHER,
        location=None,
    )


def test_add_images_appends_paths():
    owner = build_user(1)
    task = build_task(owner)

    task.add_images(owner, ["data/imgs/hash1", "data/imgs/hash2"])

    assert task.image_paths == ["data/imgs/hash1", "data/imgs/hash2"]
    assert task.updated_at is not None


def test_add_images_rejects_non_owner():
    owner = build_user(1)
    other_user = build_user(2)
    task = build_task(owner)

    with pytest.raises(InvalidTaskAction):
        task.add_images(other_user, ["data/imgs/hash1"])

    assert task.image_paths == []


def test_remove_image_removes_path():
    owner = build_user(1)
    task = build_task(owner)
    task.add_images(owner, ["data/imgs/hash1", "data/imgs/hash2"])

    task.remove_image(owner, "data/imgs/hash1")

    assert task.image_paths == ["data/imgs/hash2"]


def test_remove_image_rejects_non_owner():
    owner = build_user(1)
    other_user = build_user(2)
    task = build_task(owner)
    task.add_images(owner, ["data/imgs/hash1"])

    with pytest.raises(InvalidTaskAction):
        task.remove_image(other_user, "data/imgs/hash1")

    assert task.image_paths == ["data/imgs/hash1"]


def test_remove_image_not_found():
    owner = build_user(1)
    task = build_task(owner)

    with pytest.raises(DomainException):
        task.remove_image(owner, "data/imgs/does-not-exist")
