from copy import deepcopy
from datetime import datetime
from datetime import timezone as tz

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
        test_users = {100: User(100, "John", "Johnson", "john@johnson.com"), 101: User(101, "Adam", "Adamson", "adam@adamson.com")}
        test_tasks = {100: Task(id=100, title="Help", description="please help me", owner=User(100, "John", "Johnson", "john@johnson.com"), status=TaskStatus.OPEN, updated_at=None, created_at=datetime(2024, 11, 14, tzinfo=tz.utc))}

        self.users.update(test_users)
        self.tasks.update(test_tasks)

    def create_user(self, user_data: dict) -> User:
        user_id = 1
        while user_id in self.users:
            user_id += 1
        user = User(id=user_id, **user_data)
        self.users[user.id] = user
        print(self.users)
        return deepcopy(user)

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
