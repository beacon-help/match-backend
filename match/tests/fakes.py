from datetime import datetime, timedelta
from datetime import timezone as tz

from match.domain.interfaces import UnitOfWork
from match.domain.task import Category, Location, Task, TaskEvent, TaskEventType, TaskStatus
from match.domain.user import User, UserId, UserType
from match.infra.repositories import InMemoryMatchRepository

SEED_TIME = datetime(2024, 11, 14, tzinfo=tz.utc)
OWNER_ID = UserId(100)
HELPER_ID = UserId(101)

_APPROVED = [TaskEventType.CREATED, TaskEventType.OFFERED, TaskEventType.APPROVED]
SEED_TASKS = {
    100: (TaskStatus.OPEN, [TaskEventType.CREATED]),
    101: (TaskStatus.PENDING, [TaskEventType.CREATED, TaskEventType.OFFERED]),
    102: (TaskStatus.APPROVED, _APPROVED),
    103: (TaskStatus.SUCCEEDED, [*_APPROVED, TaskEventType.SUCCEEDED]),
    104: (TaskStatus.FAILED, [*_APPROVED, TaskEventType.FAILED]),
    105: (TaskStatus.CANCELLED, [*_APPROVED, TaskEventType.CLOSED]),
}


def _seed_users() -> list[User]:
    return [
        User(
            id=UserId(user_id),
            user_type=user_type,
            first_name=first_name,
            last_name=last_name,
            email=email,
            is_verified=is_verified,
            verification_code=f"verif-code-{user_id}",
        )
        for user_id, user_type, first_name, last_name, email, is_verified in (
            (100, UserType.VOLUNTEER, "John", "Johnson", "john@johnson.com", True),
            (101, UserType.HELP_SEEKER, "Adam", "Adamson", "adam@adamson.com", True),
            (102, UserType.HELP_SEEKER, "Gary", "Moveout", "gary@move.out", False),
            (103, UserType.VOLUNTEER, "Garry", "Moveout", "garry@move.out", False),
        )
    ]


def _seed_events(event_types: list[TaskEventType]) -> list[TaskEvent]:
    return [
        TaskEvent(
            type=event_type,
            actor_id=HELPER_ID if event_type == TaskEventType.OFFERED else OWNER_ID,
            helper_id=None if event_type == TaskEventType.CREATED else HELPER_ID,
            occurred_at=SEED_TIME + timedelta(hours=hour),
        )
        for hour, event_type in enumerate(event_types)
    ]


def _seed_task(task_id: int, status: TaskStatus, event_types: list[TaskEventType]) -> Task:
    has_helper = status != TaskStatus.OPEN
    return Task(
        id=task_id,
        title="Help",
        description="please help me",
        owner_id=OWNER_ID,
        helper_id=HELPER_ID if has_helper else None,
        status=status,
        category=Category.OTHER,
        location=Location(lat=40.7128, lon=-74.0060, address="New York, NY"),
        events=_seed_events(event_types),
        updated_at=SEED_TIME if has_helper else None,
        created_at=SEED_TIME,
    )


def seeded_in_memory_repository() -> InMemoryMatchRepository:
    repository = InMemoryMatchRepository()
    repository.users.update({user.id: user for user in _seed_users()})
    for task_id, (status, event_types) in SEED_TASKS.items():
        task = _seed_task(task_id, status, event_types)
        repository._persist_new_events(task)
        repository.tasks[task_id] = task
    return repository


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1
