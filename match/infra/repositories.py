import json
import math
from copy import deepcopy
from datetime import datetime
from datetime import timezone as tz

import sqlalchemy
from sqlalchemy import orm, select
from sqlalchemy.orm.session import Session as SQLAlchemySession

from match.domain import exceptions
from match.domain.interfaces import MatchRepository, TaskFilter
from match.domain.task import Category, Location, Task, TaskStatus
from match.domain.user import User
from match.infra import db_models

EARTH_RADIUS_KM = 6371.0088


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = lat2_rad - lat1_rad
    delta_lon = math.radians(lon2 - lon1)

    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(haversine))


def _filter_tasks_by_radius(tasks: list[Task], filters: TaskFilter) -> list[Task]:
    location_radius = filters.get("location_radius")
    if location_radius is None:
        return tasks
    return [
        task
        for task in tasks
        if task.location is not None
        and _distance_km(
            location_radius.lat,
            location_radius.lon,
            task.location.lat,
            task.location.lon,
        )
        <= location_radius.radius_km
    ]


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
        test_location = Location(lat=40.7128, lon=-74.0060, address="New York, NY")
        test_tasks = {
            100: Task(
                id=100,
                title="Help",
                description="please help me",
                owner_id=100,
                status=TaskStatus.OPEN,
                category=Category.OTHER,
                location=test_location,
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
                category=Category.OTHER,
                location=test_location,
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
                category=Category.OTHER,
                location=test_location,
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
                category=Category.OTHER,
                location=test_location,
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
                category=Category.OTHER,
                location=test_location,
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
                category=Category.OTHER,
                location=test_location,
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

    def get_users_by_ids(self, user_ids: set[int]) -> dict[int, User]:
        users: dict[int, User] = {}
        for user_id in user_ids:
            try:
                users[user_id] = deepcopy(self.users[user_id])
            except KeyError:
                raise exceptions.UserNotFound
        return users

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

    def get_tasks(self, filters: TaskFilter | None = None) -> list[Task]:
        filters = filters or {}
        tasks = list(deepcopy(t) for t in self.tasks.values())
        if "status" in filters:
            tasks = [task for task in tasks if task.status == filters["status"]]
        if "category" in filters:
            tasks = [task for task in tasks if task.category == filters["category"]]
        if "owner_id" in filters:
            tasks = [task for task in tasks if task.owner_id == filters["owner_id"]]
        if "helper_id" in filters:
            tasks = [task for task in tasks if task.helper_id == filters["helper_id"]]
        return _filter_tasks_by_radius(tasks, filters)

    def task_update(self, task: Task) -> Task:
        if task.id is None:
            raise Exception("Cannot update task without id.")
        self.get_task_by_id(task.id)
        self.tasks[task.id] = task
        return deepcopy(task)


# @dataclass
class SQLiteRepository(MatchRepository):
    def __init__(self, session: SQLAlchemySession) -> None:
        self.session = session
        self._test_data_seeded = False

    def _setup_test_data(self) -> None:
        has_users = self.session.execute(select(db_models.User.id).limit(1)).first() is not None
        has_tasks = self.session.execute(select(db_models.Task.id).limit(1)).first() is not None
        if has_users and has_tasks:
            return

        test_users = [
            db_models.User(
                id=100,
                first_name="John",
                last_name="Johnson",
                email="john@johnson.com",
                properties=json.dumps([]),
                is_verified=True,
                verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            db_models.User(
                id=101,
                first_name="Adam",
                last_name="Adamson",
                email="adam@adamson.com",
                properties=json.dumps([]),
                is_verified=True,
                verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            db_models.User(
                id=102,
                first_name="Gary",
                last_name="Moveout",
                email="gary@move.out",
                properties=json.dumps([]),
                is_verified=False,
                verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            db_models.User(
                id=103,
                first_name="Garry",
                last_name="Moveout",
                email="garry@move.out",
                properties=json.dumps([]),
                is_verified=False,
                verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
        ]

        test_location = (40.7128, -74.0060, "New York, NY")
        test_tasks = [
            db_models.Task(
                id=100,
                title="Help",
                description="please help me",
                owner_id=100,
                helper_id=None,
                status=TaskStatus.OPEN.value,
                category=Category.OTHER.value,
                updated_at=None,
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                location_lat=test_location[0],
                location_lon=test_location[1],
                location_address=test_location[2],
            ),
            db_models.Task(
                id=101,
                title="Help",
                description="please help me",
                owner_id=100,
                helper_id=101,
                status=TaskStatus.PENDING.value,
                category=Category.OTHER.value,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                location_lat=test_location[0],
                location_lon=test_location[1],
                location_address=test_location[2],
            ),
            db_models.Task(
                id=102,
                title="Help",
                description="please help me",
                owner_id=100,
                helper_id=101,
                status=TaskStatus.APPROVED.value,
                category=Category.OTHER.value,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                location_lat=test_location[0],
                location_lon=test_location[1],
                location_address=test_location[2],
            ),
            db_models.Task(
                id=103,
                title="Help",
                description="please help me",
                owner_id=100,
                helper_id=101,
                status=TaskStatus.SUCCEEDED.value,
                category=Category.OTHER.value,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                location_lat=test_location[0],
                location_lon=test_location[1],
                location_address=test_location[2],
            ),
            db_models.Task(
                id=104,
                title="Help",
                description="please help me",
                owner_id=100,
                helper_id=101,
                status=TaskStatus.FAILED.value,
                category=Category.OTHER.value,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                location_lat=test_location[0],
                location_lon=test_location[1],
                location_address=test_location[2],
            ),
            db_models.Task(
                id=105,
                title="Help",
                description="please help me",
                owner_id=100,
                helper_id=101,
                status=TaskStatus.CANCELLED.value,
                category=Category.OTHER.value,
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                location_lat=test_location[0],
                location_lon=test_location[1],
                location_address=test_location[2],
            ),
        ]

        for user in test_users:
            self.session.merge(user)
        for task in test_tasks:
            self.session.merge(task)
        self.session.commit()

    def _ensure_test_data(self) -> None:
        if self._test_data_seeded:
            return
        try:
            self._setup_test_data()
        except sqlalchemy.exc.OperationalError:
            return
        self._test_data_seeded = True

    @staticmethod
    def _user_to_domain(obj: db_models.User) -> User:
        return User(
            id=obj.id,
            first_name=obj.first_name,
            last_name=obj.last_name,
            email=obj.email,
            properties=json.loads(obj.properties),
            is_verified=obj.is_verified,
            verification_code=obj.verification_code,
        )

    def _get_user_by_id(self, user_id: int) -> db_models.User:
        statement = select(db_models.User).filter_by(id=user_id)
        try:
            return self.session.execute(statement).one()[0]
        except sqlalchemy.orm.exc.NoResultFound:
            raise exceptions.UserNotFound

    def create_user(self, user_data: dict) -> User:
        self._ensure_test_data()
        user = User(id=0, **user_data)
        existing_user = self.session.scalars(
            select(db_models.User).filter_by(email=user.email)
        ).first()
        if existing_user is not None:
            return self._user_to_domain(existing_user)
        db_model = db_models.User(
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            properties=json.dumps(user.properties),
            is_verified=user.is_verified,
            verification_code=user.verification_code,
            created_at=datetime.now(tz.utc),
        )
        self.session.add(db_model)
        self.session.commit()
        self.session.refresh(db_model)
        return self._user_to_domain(db_model)

    def user_update(self, user: User) -> User:
        self._ensure_test_data()
        db_obj = self._get_user_by_id(user.id)

        db_obj.first_name = user.first_name
        db_obj.last_name = user.last_name
        db_obj.email = user.email
        db_obj.properties = json.dumps(user.properties)
        db_obj.is_verified = user.is_verified
        db_obj.verification_code = user.verification_code

        self.session.commit()
        self.session.refresh(db_obj)
        return self._user_to_domain(db_obj)

    def get_user_by_id(self, user_id: int) -> User:
        self._ensure_test_data()
        db_obj = self._get_user_by_id(user_id)
        return self._user_to_domain(db_obj)

    def get_users_by_ids(self, user_ids: set[int]) -> dict[int, User]:
        self._ensure_test_data()
        if not user_ids:
            return {}
        statement = select(db_models.User).where(db_models.User.id.in_(user_ids))
        db_objs = self.session.scalars(statement).all()
        return {obj.id: self._user_to_domain(obj) for obj in db_objs}

    @staticmethod
    def _task_to_domain(obj: db_models.Task) -> Task:
        try:
            status = TaskStatus(obj.status)
        except KeyError as e:
            raise e

        if obj.location_lat and obj.location_lon and obj.location_address:
            location = Location(
                lat=obj.location_lat,
                lon=obj.location_lon,
                address=obj.location_address,
            )
        else:
            location = None

        return Task(
            id=obj.id,
            title=obj.title,
            description=obj.description,
            owner_id=obj.owner_id,
            helper_id=obj.helper_id,
            status=status,
            category=Category(obj.category),
            location=location,
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
            category=task.category.value,
            helper_id=task.helper_id,
            updated_at=task.updated_at,
            created_at=task.created_at,
            location_lat=task.location.lat if task.location else None,
            location_lon=task.location.lon if task.location else None,
            location_address=task.location.address if task.location else None,
        )
        self.session.add(db_model)
        self.session.commit()
        self.session.refresh(db_model)
        return self._task_to_domain(db_model)

    def get_task_by_id(self, task_id: int) -> Task:
        db_obj = self._get_task_by_id(task_id)
        return self._task_to_domain(db_obj)

    def get_tasks(self, filters: TaskFilter | None = None) -> list[Task]:
        filters = filters or {}
        statement = select(db_models.Task)
        if "status" in filters:
            statement = statement.filter_by(status=filters["status"].value)
        if "category" in filters:
            statement = statement.filter_by(category=filters["category"].value)
        if "owner_id" in filters:
            statement = statement.filter_by(owner_id=filters["owner_id"])
        if "helper_id" in filters:
            statement = statement.filter_by(helper_id=filters["helper_id"])
        db_objs = self.session.scalars(statement).all()
        tasks = [self._task_to_domain(obj) for obj in db_objs]
        return _filter_tasks_by_radius(tasks, filters)

    def task_update(self, task: Task) -> Task:
        if not task.id:
            raise Exception("Cannot update task without id.")
        db_obj = self._get_task_by_id(task.id)

        db_obj.title = task.title
        db_obj.description = task.description
        db_obj.helper_id = task.helper_id
        db_obj.status = task.status.value
        db_obj.category = task.category.value
        db_obj.updated_at = task.updated_at

        self.session.commit()
        return task
