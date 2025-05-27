from copy import deepcopy
from datetime import datetime
from datetime import timezone as tz
from uuid import uuid4

from match.domain import exceptions
from match.domain.interfaces import MatchRepository
from match.domain.task import Task, TaskStatus
from match.domain.user import User


class InMemoryMatchRepository(MatchRepository):
    def __init__(self, test_data: bool = True) -> None:
        self.users: dict[int, User] = {}
        self.tasks: dict[int, Task] = {}
        if test_data:
            self._setup_test_data()

    def _setup_test_data(self) -> None:
        test_users = {
            100: User(
                100,
                "John",
                "Johnson",
                "john@johnson.com",
                is_verified=True,
                verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
            ),
            101: User(
                101,
                "Adam",
                "Adamson",
                "adam@adamson.com",
                is_verified=True,
                verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
            ),
            102: User(
                102,
                "Gary",
                "Moveout",
                "gary@move.out",
                is_verified=False,
                verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
            ),
            103: User(
                101,
                "Garry",
                "Moveout",
                "garry@move.out",
                is_verified=False,
                verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
            ),
        }
        test_tasks = {
            100: Task(
                id=100,
                title="Help",
                description="please help me",
                owner=User(
                    100,
                    "John",
                    "Johnson",
                    "john@johnson.com",
                    is_verified=True,
                    verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                ),
                status=TaskStatus.OPEN,
                updated_at=None,
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            101: Task(
                id=100,
                title="Help",
                description="please help me",
                owner=User(
                    100,
                    "John",
                    "Johnson",
                    "john@johnson.com",
                    is_verified=True,
                    verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                ),
                helper=User(
                    101,
                    "Adam",
                    "Adamson",
                    "adam@adamson.com",
                    is_verified=True,
                    verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                ),
                status=TaskStatus.PENDING,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            102: Task(
                id=100,
                title="Help",
                description="please help me",
                owner=User(
                    100,
                    "John",
                    "Johnson",
                    "john@johnson.com",
                    is_verified=True,
                    verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                ),
                helper=User(
                    101,
                    "Adam",
                    "Adamson",
                    "adam@adamson.com",
                    is_verified=True,
                    verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                ),
                status=TaskStatus.APPROVED,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            103: Task(
                id=100,
                title="Help",
                description="please help me",
                owner=User(
                    100,
                    "John",
                    "Johnson",
                    "john@johnson.com",
                    is_verified=True,
                    verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                ),
                helper=User(
                    101,
                    "Adam",
                    "Adamson",
                    "adam@adamson.com",
                    is_verified=True,
                    verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                ),
                status=TaskStatus.SUCCEEDED,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            104: Task(
                id=100,
                title="Help",
                description="please help me",
                owner=User(
                    100,
                    "John",
                    "Johnson",
                    "john@johnson.com",
                    is_verified=True,
                    verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                ),
                helper=User(
                    101,
                    "Adam",
                    "Adamson",
                    "adam@adamson.com",
                    is_verified=True,
                    verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                ),
                status=TaskStatus.FAILED,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            105: Task(
                id=100,
                title="Help",
                description="please help me",
                owner=User(
                    100,
                    "John",
                    "Johnson",
                    "john@johnson.com",
                    is_verified=True,
                    verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                ),
                helper=User(
                    101,
                    "Adam",
                    "Adamson",
                    "adam@adamson.com",
                    is_verified=True,
                    verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                ),
                status=TaskStatus.CANCELLED,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
        }

        self.users.update(test_users)
        self.tasks.update(test_tasks)

    def create_user(self, user_data: dict) -> User:
        user_id = 1
        while user_id in self.users:
            user_id += 1
        user = User(id=user_id, **user_data)
        self.users[user.id] = user
        return deepcopy(user)

    def user_update(self, user: User) -> User:
        self.users[user.id] = user
        return deepcopy(self.users[user.id])

    def get_user_by_id(self, user_id: int) -> User:
        try:
            return deepcopy(self.users[user_id])
        except KeyError:
            raise exceptions.UserNotFound

    def create_task(self, task: Task) -> Task:
        task_id = 1
        while task_id in self.tasks:
            task_id += 1
        task.id = task_id
        self.tasks[task_id] = deepcopy(task)
        return deepcopy(task)

    def get_task_by_id(self, task_id: int) -> Task:
        try:
            return deepcopy(self.tasks[task_id])
        except KeyError:
            raise exceptions.TaskNotFound

    def get_tasks(self) -> list[Task]:
        return list(deepcopy(t) for t in self.tasks.values())

    def task_update(self, task: Task) -> Task:
        if task.id is None:
            raise Exception("Cannot update task without id.")
        self.get_task_by_id(task.id)
        self.tasks[task.id] = task
        return deepcopy(task)
