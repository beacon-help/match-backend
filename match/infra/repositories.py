import json
import math
from collections import defaultdict
from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime
from datetime import timezone as tz

import sqlalchemy
from sqlalchemy import Select, orm, select
from sqlalchemy.orm.session import Session as SQLAlchemySession

from match.domain import exceptions
from match.domain.interfaces import MatchRepository, TaskFilter
from match.domain.task import (
    Category,
    HelperOffer,
    ImageId,
    Location,
    Task,
    TaskEvent,
    TaskEventType,
    TaskStatus,
)
from match.domain.user import User, UserId, UserType
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


_SEED_TIME = datetime(2024, 11, 14, tzinfo=tz.utc)
_APPROVED_EVENTS = [TaskEventType.CREATED, TaskEventType.OFFERED, TaskEventType.APPROVED]
_SEED_EVENT_TYPES = {
    100: [TaskEventType.CREATED],
    101: [TaskEventType.CREATED, TaskEventType.OFFERED],
    102: _APPROVED_EVENTS,
    103: [*_APPROVED_EVENTS, TaskEventType.SUCCEEDED],
    104: [*_APPROVED_EVENTS, TaskEventType.FAILED],
    105: [*_APPROVED_EVENTS, TaskEventType.CLOSED],
}


def _seed_events(task_id: int, owner_id: int, helper_id: int) -> list[TaskEvent]:
    return [
        TaskEvent(
            type=event_type,
            actor_id=UserId(helper_id if event_type == TaskEventType.OFFERED else owner_id),
            helper_id=None if event_type == TaskEventType.CREATED else UserId(helper_id),
            occurred_at=_SEED_TIME,
        )
        for event_type in _SEED_EVENT_TYPES[task_id]
    ]


class InMemoryMatchRepository(MatchRepository):
    def __init__(self, test_data: bool = True) -> None:
        self.users: dict[int, User] = {}
        self.tasks: dict[int, Task] = {}
        self.images: dict[str, int] = {}
        self._last_event_id = 0
        if test_data:
            self._setup_test_data()

    def _persist_new_images(self, task_id: int, task: Task) -> None:
        for image_id in task.images:
            if image_id not in self.images:
                self.images[image_id] = task_id

    def _persist_new_events(self, task: Task) -> None:
        for event in task.events:
            if event.id is None:
                self._last_event_id += 1
                event.id = self._last_event_id

    def _setup_test_data(self) -> None:
        test_users = {
            100: User(
                id=UserId(100),
                user_type=UserType.VOLUNTEER,
                first_name="John",
                last_name="Johnson",
                email="john@johnson.com",
                is_verified=True,
                verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
            ),
            101: User(
                id=UserId(101),
                user_type=UserType.HELP_SEEKER,
                first_name="Adam",
                last_name="Adamson",
                email="adam@adamson.com",
                is_verified=True,
                verification_code="3a86ddd8-a08e-56g4-98cg-55456c1g3g17",
            ),
            102: User(
                id=UserId(102),
                user_type=UserType.HELP_SEEKER,
                first_name="Gary",
                last_name="Moveout",
                email="gary@move.out",
                is_verified=False,
                verification_code="4b97eee9-b19f-67h5-09dh-66567d2h4h28",
            ),
            103: User(
                id=UserId(101),
                user_type=UserType.VOLUNTEER,
                first_name="Garry",
                last_name="Moveout",
                email="garry@move.out",
                is_verified=False,
                verification_code="5ca8fffa-c2ag-78i6-1aei-77678e3i5i39",
            ),
        }
        test_location = Location(lat=40.7128, lon=-74.0060, address="New York, NY")
        test_tasks = {
            100: Task(
                id=100,
                title="Help",
                description="please help me",
                owner_id=UserId(100),
                status=TaskStatus.OPEN,
                category=Category.OTHER,
                location=test_location,
                events=_seed_events(100, owner_id=100, helper_id=101),
                updated_at=None,
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            101: Task(
                id=101,
                title="Help",
                description="please help me",
                owner_id=UserId(100),
                helper_id=UserId(101),
                status=TaskStatus.PENDING,
                category=Category.OTHER,
                location=test_location,
                events=_seed_events(101, owner_id=100, helper_id=101),
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            102: Task(
                id=102,
                title="Help",
                description="please help me",
                owner_id=UserId(100),
                helper_id=UserId(101),
                status=TaskStatus.APPROVED,
                category=Category.OTHER,
                location=test_location,
                events=_seed_events(102, owner_id=100, helper_id=101),
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            103: Task(
                id=103,
                title="Help",
                description="please help me",
                owner_id=UserId(100),
                helper_id=UserId(101),
                status=TaskStatus.SUCCEEDED,
                category=Category.OTHER,
                location=test_location,
                events=_seed_events(103, owner_id=100, helper_id=101),
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            104: Task(
                id=104,
                title="Help",
                description="please help me",
                owner_id=UserId(100),
                helper_id=UserId(101),
                status=TaskStatus.FAILED,
                category=Category.OTHER,
                location=test_location,
                events=_seed_events(104, owner_id=100, helper_id=101),
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            105: Task(
                id=105,
                title="Help",
                description="please help me",
                owner_id=UserId(100),
                helper_id=UserId(101),
                status=TaskStatus.CANCELLED,
                category=Category.OTHER,
                location=test_location,
                events=_seed_events(105, owner_id=100, helper_id=101),
                updated_at=datetime(2024, 11, 14, tzinfo=tz.utc),
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
        }

        for task in test_tasks.values():
            self._persist_new_events(task)
        self.users.update(test_users)
        self.tasks.update(test_tasks)

    def create_user(self, user_data: dict) -> User:
        user_id = 1
        while user_id in self.users:
            user_id += 1
        user = User(id=UserId(user_id), **user_data)
        self.users[user_id] = user
        return deepcopy(user)

    def user_update(self, user: User) -> User:
        self.users[user.id] = user
        return deepcopy(self.users[user.id])

    def get_user_by_id(self, user_id: int) -> User:
        try:
            return deepcopy(self.users[user_id])
        except KeyError:
            raise exceptions.UserNotFound

    def get_user_by_email(self, email: str) -> User:
        for user in self.users.values():
            if user.email == email:
                return deepcopy(user)
        raise exceptions.UserNotFound

    def get_user_by_verification_code(self, verification_code: str) -> User:
        for user in self.users.values():
            if user.verification_code == verification_code:
                return deepcopy(user)
        raise exceptions.UserNotFound

    def get_users_by_ids(self, user_ids: set[UserId]) -> dict[UserId, User]:
        users: dict[UserId, User] = {}
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
        self._persist_new_images(task_id, task)
        self._persist_new_events(task)
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
            raise exceptions.RepositoryException("Cannot update task without id.")
        self.get_task_by_id(task.id)
        self._persist_new_images(task.id, task)
        self._persist_new_events(task)
        self.tasks[task.id] = task
        return deepcopy(task)

    def images_delete(self, image_ids: list[ImageId]) -> None:
        for image_id in image_ids:
            self.images.pop(image_id, None)


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
                user_type=UserType.VOLUNTEER,
                first_name="John",
                last_name="Johnson",
                email="john@johnson.com",
                properties=json.dumps([]),
                is_verified=True,
                verification_code="2f75ccc7-9f7d-45f3-87bf-44345b0f2f06",
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            db_models.User(
                user_type=UserType.HELP_SEEKER,
                id=101,
                first_name="Adam",
                last_name="Adamson",
                email="adam@adamson.com",
                properties=json.dumps([]),
                is_verified=True,
                verification_code="3a86ddd8-a08e-56g4-98cg-55456c1g3g17",
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            db_models.User(
                id=102,
                user_type=UserType.HELP_SEEKER,
                first_name="Gary",
                last_name="Moveout",
                email="gary@move.out",
                properties=json.dumps([]),
                is_verified=False,
                verification_code="4b97eee9-b19f-67h5-09dh-66567d2h4h28",
                created_at=datetime(2024, 11, 14, tzinfo=tz.utc),
            ),
            db_models.User(
                id=103,
                user_type=UserType.VOLUNTEER,
                first_name="Garry",
                last_name="Moveout",
                email="garry@move.out",
                properties=json.dumps([]),
                is_verified=False,
                verification_code="5ca8fffa-c2ag-78i6-1aei-77678e3i5i39",
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
        if not has_tasks:
            for task_id in _SEED_EVENT_TYPES:
                self.session.add_all(
                    db_models.TaskEvent(
                        task_id=task_id,
                        type=event.type.value,
                        actor_id=event.actor_id,
                        helper_id=event.helper_id,
                        occurred_at=event.occurred_at,
                    )
                    for event in _seed_events(task_id, owner_id=100, helper_id=101)
                )
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
            id=UserId(obj.id),
            user_type=obj.user_type,
            first_name=obj.first_name,
            last_name=obj.last_name,
            email=obj.email,
            properties=json.loads(obj.properties),
            is_verified=obj.is_verified,
            verification_code=obj.verification_code,
            password_hash=obj.password_hash,
        )

    def _get_user_by_id(self, user_id: int) -> db_models.User:
        statement = select(db_models.User).filter_by(id=user_id)
        try:
            return self.session.execute(statement).one()[0]
        except sqlalchemy.orm.exc.NoResultFound:
            raise exceptions.UserNotFound

    def create_user(self, user_data: dict) -> User:
        self._ensure_test_data()
        user = User(id=UserId(0), **user_data)
        existing_user = self.session.scalars(
            select(db_models.User).filter_by(email=user.email)
        ).first()
        if existing_user is not None:
            return self._user_to_domain(existing_user)
        db_model = db_models.User(
            user_type=user.user_type,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            properties=json.dumps(user.properties),
            is_verified=user.is_verified,
            verification_code=user.verification_code,
            password_hash=user.password_hash,
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
        db_obj.password_hash = user.password_hash

        self.session.commit()
        self.session.refresh(db_obj)
        return self._user_to_domain(db_obj)

    def get_user_by_id(self, user_id: int) -> User:
        self._ensure_test_data()
        db_obj = self._get_user_by_id(user_id)
        return self._user_to_domain(db_obj)

    def get_user_by_email(self, email: str) -> User:
        self._ensure_test_data()
        statement = select(db_models.User).filter_by(email=email)
        try:
            db_obj = self.session.execute(statement).one()[0]
        except sqlalchemy.orm.exc.NoResultFound:
            raise exceptions.UserNotFound
        return self._user_to_domain(db_obj)

    def get_user_by_verification_code(self, verification_code: str) -> User:
        self._ensure_test_data()
        statement = select(db_models.User).filter_by(verification_code=verification_code)
        try:
            db_obj = self.session.execute(statement).one()[0]
        except sqlalchemy.orm.exc.NoResultFound:
            raise exceptions.UserNotFound
        return self._user_to_domain(db_obj)

    def get_users_by_ids(self, user_ids: set[UserId]) -> dict[UserId, User]:
        self._ensure_test_data()
        if not user_ids:
            return {}
        statement = select(db_models.User).where(db_models.User.id.in_(user_ids))
        db_objs = self.session.scalars(statement).all()
        return {UserId(obj.id): self._user_to_domain(obj) for obj in db_objs}

    def _get_images_for_tasks(self, task_ids: list[int]) -> dict[int, list[ImageId]]:
        statement = select(db_models.Image).where(db_models.Image.task_id.in_(task_ids))
        images_by_task_id: dict[int, list[ImageId]] = defaultdict(list)
        for obj in self.session.scalars(statement):
            images_by_task_id[obj.task_id].append(ImageId(obj.id))
        return images_by_task_id

    def _persist_new_images(self, task_id: int, task: Task) -> None:
        existing_ids = set(
            self.session.scalars(select(db_models.Image.id).filter_by(task_id=task_id))
        )
        new_ids = [image_id for image_id in task.images if image_id not in existing_ids]
        if not new_ids:
            return
        db_images = [db_models.Image(id=image_id, task_id=task_id) for image_id in new_ids]
        self.session.add_all(db_images)
        self.session.flush()

    def _get_events_for_tasks(self, task_ids: list[int]) -> dict[int, list[TaskEvent]]:
        statement = (
            select(db_models.TaskEvent)
            .where(db_models.TaskEvent.task_id.in_(task_ids))
            .order_by(db_models.TaskEvent.occurred_at, db_models.TaskEvent.id)
        )
        events_by_task_id: dict[int, list[TaskEvent]] = defaultdict(list)
        for obj in self.session.scalars(statement):
            events_by_task_id[obj.task_id].append(
                TaskEvent(
                    id=obj.id,
                    type=TaskEventType(obj.type),
                    actor_id=UserId(obj.actor_id),
                    helper_id=UserId(obj.helper_id) if obj.helper_id is not None else None,
                    message=obj.message,
                    occurred_at=obj.occurred_at,
                )
            )
        return events_by_task_id

    def _persist_new_events(self, task_id: int, task: Task) -> None:
        new_events = [event for event in task.events if event.id is None]
        if not new_events:
            return
        db_events = [
            db_models.TaskEvent(
                task_id=task_id,
                type=event.type.value,
                actor_id=event.actor_id,
                helper_id=event.helper_id,
                message=event.message,
                occurred_at=event.occurred_at,
            )
            for event in new_events
        ]
        self.session.add_all(db_events)
        self.session.flush()
        for event, db_event in zip(new_events, db_events):
            event.id = db_event.id

    def _tasks_to_domain(self, rows: Sequence[tuple[db_models.Task, str]]) -> list[Task]:
        task_ids = [obj.id for obj, _ in rows]
        images_by_task_id = self._get_images_for_tasks(task_ids)
        events_by_task_id = self._get_events_for_tasks(task_ids)
        return [
            self._task_to_domain(obj, status, images_by_task_id[obj.id], events_by_task_id[obj.id])
            for obj, status in rows
        ]

    @staticmethod
    def _task_to_domain(
        obj: db_models.Task, status: str, images: list[ImageId], events: list[TaskEvent]
    ) -> Task:
        if obj.location_lat and obj.location_lon and obj.location_address:
            location = Location(
                lat=obj.location_lat,
                lon=obj.location_lon,
                address=obj.location_address,
            )
        else:
            location = None

        helper_offers_list = []
        if obj.helper_offers:
            try:
                offers_data = json.loads(obj.helper_offers)
                helper_offers_list = [HelperOffer.from_dict(offer) for offer in offers_data]
            except (json.JSONDecodeError, ValueError):
                helper_offers_list = []

        return Task(
            id=obj.id,
            title=obj.title,
            description=obj.description,
            owner_id=UserId(obj.owner_id),
            helper_id=UserId(obj.helper_id) if obj.helper_id is not None else None,
            helper_offers=helper_offers_list,
            images=images,
            events=events,
            status=TaskStatus(status),
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
        helper_offers_json = (
            json.dumps([offer.to_dict() for offer in task.helper_offers])
            if task.helper_offers
            else None
        )
        db_model = db_models.Task(
            title=task.title,
            description=task.description,
            owner_id=task.owner_id,
            category=task.category.value,
            helper_id=task.helper_id,
            helper_offers=helper_offers_json,
            updated_at=task.updated_at,
            created_at=task.created_at,
            location_lat=task.location.lat if task.location else None,
            location_lon=task.location.lon if task.location else None,
            location_address=task.location.address if task.location else None,
        )
        self.session.add(db_model)
        self.session.flush()
        self._persist_new_images(db_model.id, task)
        self._persist_new_events(db_model.id, task)
        self.session.commit()
        return self.get_task_by_id(db_model.id)

    @staticmethod
    def _select_tasks_with_status() -> Select[tuple[db_models.Task, str]]:
        view = db_models.tasks_with_status
        return select(db_models.Task, view.c.status).join(view, view.c.id == db_models.Task.id)

    def get_task_by_id(self, task_id: int) -> Task:
        statement = self._select_tasks_with_status().where(db_models.Task.id == task_id)
        try:
            row = self.session.execute(statement).tuples().one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise exceptions.TaskNotFound
        return self._tasks_to_domain([row])[0]

    def get_tasks(self, filters: TaskFilter | None = None) -> list[Task]:
        filters = filters or {}
        statement = self._select_tasks_with_status()
        if "status" in filters:
            statement = statement.where(
                db_models.tasks_with_status.c.status == filters["status"].value
            )
        if "category" in filters:
            statement = statement.where(db_models.Task.category == filters["category"].value)
        if "owner_id" in filters:
            statement = statement.where(db_models.Task.owner_id == filters["owner_id"])
        if "helper_id" in filters:
            statement = statement.where(db_models.Task.helper_id == filters["helper_id"])
        tasks = self._tasks_to_domain(self.session.execute(statement).tuples().all())
        return _filter_tasks_by_radius(tasks, filters)

    def task_update(self, task: Task) -> Task:
        if not task.id:
            raise exceptions.RepositoryException("Cannot update task without id.")
        db_obj = self._get_task_by_id(task.id)

        db_obj.title = task.title
        db_obj.description = task.description
        db_obj.helper_id = task.helper_id
        db_obj.helper_offers = (
            json.dumps([offer.to_dict() for offer in task.helper_offers])
            if task.helper_offers
            else None
        )
        db_obj.category = task.category.value
        db_obj.updated_at = task.updated_at

        self._persist_new_images(task.id, task)
        self._persist_new_events(task.id, task)
        self.session.commit()
        return task

    def images_delete(self, image_ids: list[ImageId]) -> None:
        if not image_ids:
            return
        statement = select(db_models.Image).where(db_models.Image.id.in_(image_ids))
        db_images = self.session.scalars(statement).all()
        for db_image in db_images:
            self.session.delete(db_image)
        self.session.commit()
