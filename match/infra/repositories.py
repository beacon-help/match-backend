from copy import deepcopy
from datetime import datetime
from datetime import timezone as tz

import sqlalchemy
from sqlalchemy import orm, select
from sqlalchemy.orm.session import Session as SQLAlchemySession

from match.domain import exceptions
from match.domain.interfaces import MatchRepository
from match.domain.task import Task, TaskStatus
from match.domain.user import User
from match.infra import db_models


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
                owner_id=100,
                status=TaskStatus.OPEN,
                updated_at=None,
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            101: Task(
                id=100,
                title="Help",
                description="please help me",
                owner_id=100,
                helper_id=101,
                status=TaskStatus.PENDING,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            102: Task(
                id=100,
                title="Help",
                description="please help me",
                owner_id=100,
                helper_id=101,
                status=TaskStatus.APPROVED,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            103: Task(
                id=100,
                title="Help",
                description="please help me",
                owner_id=100,
                helper_id=101,
                status=TaskStatus.SUCCEEDED,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            104: Task(
                id=100,
                title="Help",
                description="please help me",
                owner_id=100,
                helper_id=101,
                status=TaskStatus.FAILED,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            105: Task(
                id=100,
                title="Help",
                description="please help me",
                owner_id=100,
                helper_id=101,
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


# @dataclass
class SQLiteRepository(InMemoryMatchRepository):
    def __init__(self, session: SQLAlchemySession) -> None:
        self.users: dict[int, User] = {}
        self.tasks: dict[int, Task] = {}
        self._setup_test_data()
        self.session = session

    @staticmethod
    def _task_to_domain(obj: db_models.Task) -> Task:
        try:
            status = TaskStatus(obj.status)
        except KeyError as e:
            raise e

        return Task(
            id=obj.id,
            title=obj.title,
            description=obj.description,
            owner_id=obj.owner_id,
            helper_id=obj.helper_id,
            status=status,
            updated_at=obj.updated_at,
            created_at=obj.created_at,
        )

    def _get_task_by_id(self, task_id: int) -> db_models.Task:
        statement = select(db_models.Task).filter_by(id=task_id)
        try:
            return self.session.execute(statement).one()[0]
        except sqlalchemy.orm.exc.NoResultFound:
            raise exceptions.TaskNotFound

    def create_task(self, task: Task) -> Task:
        db_model = db_models.Task(
            title=task.title,
            description=task.description,
            owner_id=task.owner_id,
            status=task.status.value,
            helper_id=task.helper_id,
            updated_at=task.updated_at,
            created_at=task.created_at,
        )
        self.session.add(db_model)
        self.session.commit()
        self.session.refresh(db_model)
        return self._task_to_domain(db_model)

    def get_task_by_id(self, task_id: int) -> Task:
        db_obj = self._get_task_by_id(task_id)
        return self._task_to_domain(db_obj)

    def get_tasks(self) -> list[Task]:
        statement = select(db_models.Task)
        db_objs = self.session.scalars(statement).all()
        return [self._task_to_domain(obj) for obj in db_objs]

    def task_update(self, task: Task) -> Task:
        if not task.id:
            raise Exception("Cannot update task without id.")
        db_obj = self._get_task_by_id(task.id)

        db_obj.title = task.title
        db_obj.description = task.description
        db_obj.helper_id = task.helper_id
        db_obj.status = task.status
        db_obj.updated_at = task.updated_at

        self.session.commit()
        return task
