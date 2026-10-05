from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta
from datetime import timezone as tz

from match.domain import exceptions
from match.domain.interfaces import TaskFilter, TaskRepository, UnitOfWork, UserRepository
from match.domain.task import (
    Category,
    ImageId,
    Location,
    Task,
    TaskEvent,
    TaskEventType,
    TaskStatus,
)
from match.domain.user import User, UserId, UserType

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


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self.users: dict[int, User] = {}

    def _active_users(self) -> dict[int, User]:
        return {user_id: user for user_id, user in self.users.items() if user.deleted_at is None}

    def create_user(self, user_data: dict) -> User:
        if any(user.email == user_data["email"] for user in self._active_users().values()):
            raise exceptions.EmailAlreadyRegistered
        user_id = 1
        while user_id in self.users:
            user_id += 1
        user = User(id=UserId(user_id), **user_data)
        self.users[user_id] = user
        return deepcopy(user)

    def user_update(self, user: User) -> User:
        self.get_user_by_id(user.id)
        self.users[user.id] = deepcopy(user)
        return deepcopy(user)

    def get_user_by_id(self, user_id: int) -> User:
        try:
            return deepcopy(self._active_users()[user_id])
        except KeyError:
            raise exceptions.UserNotFound

    def get_user_by_email(self, email: str) -> User:
        for user in self._active_users().values():
            if user.email == email:
                return deepcopy(user)
        raise exceptions.UserNotFound

    def get_user_by_verification_code(self, verification_code: str) -> User:
        for user in self._active_users().values():
            if user.verification_code == verification_code:
                return deepcopy(user)
        raise exceptions.UserNotFound

    def count_users_by_type(self) -> dict[UserType, int]:
        return dict(Counter(user.user_type for user in self._active_users().values()))

    def get_users_by_ids(self, user_ids: set[UserId]) -> dict[UserId, User]:
        users = self._active_users()
        return {user_id: deepcopy(users[user_id]) for user_id in user_ids if user_id in users}

    def get_user_ids_deleted_before(self, deleted_before: datetime) -> set[UserId]:
        return {
            UserId(user_id)
            for user_id, user in self.users.items()
            if user.deleted_at is not None and user.deleted_at < deleted_before
        }

    def users_purge(self, user_ids: set[UserId]) -> None:
        for user_id in user_ids:
            del self.users[user_id]


class InMemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self.tasks: dict[int, Task] = {}
        self.images: dict[str, int] = {}
        self.deleted_task_ids: set[int] = set()
        self._last_event_id = 0

    def _active_tasks(self) -> dict[int, Task]:
        return {
            task_id: task
            for task_id, task in self.tasks.items()
            if task_id not in self.deleted_task_ids
        }

    def _sync_images(self, task_id: int, task: Task) -> None:
        for image_id in [i for i, owner in self.images.items() if owner == task_id]:
            if image_id not in task.images:
                del self.images[image_id]
        for image_id in task.images:
            self.images.setdefault(image_id, task_id)

    def _persist_new_events(self, task: Task) -> None:
        for event in task.events:
            if event.id is None:
                self._last_event_id += 1
                event.id = self._last_event_id

    def save_task(self, task: Task) -> Task:
        if task.id is None:
            task.id = max(self.tasks, default=0) + 1
        else:
            self.get_task_by_id(task.id)
        self._sync_images(task.id, task)
        self._persist_new_events(task)
        self.tasks[task.id] = deepcopy(task)
        return deepcopy(task)

    def get_task_by_id(self, task_id: int) -> Task:
        try:
            return deepcopy(self._active_tasks()[task_id])
        except KeyError:
            raise exceptions.TaskNotFound

    def get_tasks(self, filters: TaskFilter | None = None) -> list[Task]:
        filters = filters or {}
        tasks = list(deepcopy(t) for t in self._active_tasks().values())
        if "status" in filters:
            tasks = [task for task in tasks if task.status == filters["status"]]
        if "category" in filters:
            tasks = [task for task in tasks if task.category == filters["category"]]
        if "owner_id" in filters:
            tasks = [task for task in tasks if task.owner_id == filters["owner_id"]]
        if "helper_id" in filters:
            tasks = [task for task in tasks if task.helper_id == filters["helper_id"]]
        if "location_radius" in filters:
            tasks = [
                task
                for task in tasks
                if task.location is not None and filters["location_radius"].contains(task.location)
            ]
        return tasks

    def count_tasks_by_status(self) -> dict[TaskStatus, int]:
        return dict(Counter(task.status for task in self._active_tasks().values()))

    def image_exists(self, image_id: ImageId) -> bool:
        return self.images.get(image_id) in self._active_tasks()

    def tasks_delete_owned_by(self, owner_id: UserId, deleted_at: datetime) -> None:
        self.deleted_task_ids.update(
            task_id for task_id, task in self.tasks.items() if task.owner_id == owner_id
        )

    def tasks_purge_owned_by(self, owner_ids: set[UserId]) -> list[ImageId]:
        task_ids = {task_id for task_id, task in self.tasks.items() if task.owner_id in owner_ids}
        image_ids = [
            ImageId(image_id) for image_id, task_id in self.images.items() if task_id in task_ids
        ]
        for image_id in image_ids:
            del self.images[image_id]
        for task_id in task_ids:
            del self.tasks[task_id]
        self.deleted_task_ids -= task_ids
        return image_ids


def seeded_user_repository() -> InMemoryUserRepository:
    repository = InMemoryUserRepository()
    repository.users.update({user.id: user for user in _seed_users()})
    return repository


def seeded_task_repository() -> InMemoryTaskRepository:
    repository = InMemoryTaskRepository()
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
