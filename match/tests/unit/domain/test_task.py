import pytest

from match.domain.exceptions import DomainException, InvalidTaskAction
from match.domain.task import Category, Task, TaskEventType
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


def test_add_images_appends_images():
    owner = build_user(1)
    task = build_task(owner)

    task.add_images(owner, ["hash1", "hash2"])

    assert task.images == ["hash1", "hash2"]
    assert task.updated_at is not None


def test_add_images_rejects_non_owner():
    owner = build_user(1)
    other_user = build_user(2)
    task = build_task(owner)

    with pytest.raises(InvalidTaskAction):
        task.add_images(other_user, ["hash1"])

    assert task.images == []


def test_remove_image_removes_by_id():
    owner = build_user(1)
    task = build_task(owner)
    task.add_images(owner, ["hash1", "hash2"])

    task.remove_image(owner, "hash1")

    assert task.images == ["hash2"]


def test_remove_image_rejects_non_owner():
    owner = build_user(1)
    other_user = build_user(2)
    task = build_task(owner)
    task.add_images(owner, ["hash1"])

    with pytest.raises(InvalidTaskAction):
        task.remove_image(other_user, "hash1")

    assert task.images == ["hash1"]


def test_remove_image_not_found():
    owner = build_user(1)
    task = build_task(owner)

    with pytest.raises(DomainException):
        task.remove_image(owner, "does-not-exist")


def event_summary(task):
    return [(event.type, event.actor_id, event.helper_id) for event in task.events]


def test_create_task_records_created_event():
    owner = build_user(1)

    task = build_task(owner)

    assert event_summary(task) == [(TaskEventType.CREATED, 1, None)]
    assert task.events[0].occurred_at == task.created_at


def test_task_lifecycle_records_events():
    owner = build_user(1)
    task = build_task(owner)

    task.join(2, "I can help")
    task.approve_helper(owner, 2)
    task.report_succeeded(owner)

    assert event_summary(task) == [
        (TaskEventType.CREATED, 1, None),
        (TaskEventType.OFFERED, 2, 2),
        (TaskEventType.APPROVED, 1, 2),
        (TaskEventType.SUCCEEDED, 1, 2),
    ]
    assert task.events[1].message == "I can help"


def test_reject_records_rejected_helper():
    owner = build_user(1)
    task = build_task(owner)
    task.join(2, "I can help")

    task.reject_helper(owner, 2)

    assert task.helper_id is None
    assert event_summary(task)[-1] == (TaskEventType.REJECTED, 1, 2)


def test_report_failed_records_event():
    owner = build_user(1)
    task = build_task(owner)
    task.join(2, "I can help")
    task.approve_helper(owner, 2)

    task.report_failed(owner)

    assert event_summary(task)[-1] == (TaskEventType.FAILED, 1, 2)


def test_close_records_event():
    owner = build_user(1)
    task = build_task(owner)

    task.close(owner)

    assert event_summary(task)[-1] == (TaskEventType.CLOSED, 1, None)


def test_failed_action_records_no_event():
    owner = build_user(1)
    task = build_task(owner)

    with pytest.raises(InvalidTaskAction):
        task.approve_helper(owner, 2)

    assert event_summary(task) == [(TaskEventType.CREATED, 1, None)]
