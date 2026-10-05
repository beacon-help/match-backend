from datetime import datetime
from datetime import timezone as tz

from match.domain.task import Category, Location, Task, TaskEvent, TaskEventType, TaskStatus
from match.domain.user import User, UserId, UserType
from match.infra.api.presenters import TaskPresenter

OWNER = User(
    id=UserId(1), user_type=UserType.HELP_SEEKER, first_name="Olga", last_name="O", email="o@x.com"
)
NOW = datetime(2024, 11, 14, tzinfo=tz.utc)


def build_task():
    return Task(
        id=7,
        title="t",
        description="d",
        owner_id=OWNER.id,
        helper_id=UserId(2),
        status=TaskStatus.PENDING,
        category=Category.OTHER,
        location=Location(lat=0.0, lon=0.0, address="a"),
        images=["img-1"],
        events=[
            TaskEvent(type=TaskEventType.CREATED, actor_id=OWNER.id, occurred_at=NOW, id=1),
            TaskEvent(
                type=TaskEventType.OFFERED,
                actor_id=UserId(2),
                helper_id=UserId(2),
                occurred_at=NOW,
                id=2,
            ),
        ],
    )


def test_missing_users_are_shown_as_deleted():
    response = TaskPresenter("http://host").task(build_task(), {OWNER.id: OWNER})

    deleted_user = {"id": 2, "first_name": "Deleted user"}
    assert response["owner"] == {"id": 1, "first_name": "Olga"}
    assert response["helper"] == deleted_user
    assert [event["actor"] for event in response["events"]] == [response["owner"], deleted_user]


def test_images_link_to_the_image_endpoint():
    response = TaskPresenter("http://host").task(build_task(), {OWNER.id: OWNER})

    assert response["images"] == [{"id": "img-1", "path": "http://host/task/images/img-1"}]


def test_locations_skip_tasks_without_location():
    task_without_location = build_task()
    task_without_location.location = None

    assert TaskPresenter.locations([build_task(), task_without_location]) == [
        {"id": 7, "location": Location(lat=0.0, lon=0.0, address="a")}
    ]
