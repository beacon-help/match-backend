import json
import math
from collections import Counter, defaultdict
from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime
from datetime import timezone as tz

import sqlalchemy
from sqlalchemy import Select, delete, orm, select, update
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


class InMemoryMatchRepository(MatchRepository):
    def __init__(self) -> None:
        self.users: dict[int, User] = {}
        self.tasks: dict[int, Task] = {}
        self.images: dict[str, int] = {}
        self.deleted_task_ids: set[int] = set()
        self._last_event_id = 0

    def _active_users(self) -> dict[int, User]:
        return {user_id: user for user_id, user in self.users.items() if user.deleted_at is None}

    def _active_tasks(self) -> dict[int, Task]:
        return {
            task_id: task
            for task_id, task in self.tasks.items()
            if task_id not in self.deleted_task_ids
        }

    def _persist_new_images(self, task_id: int, task: Task) -> None:
        for image_id in task.images:
            if image_id not in self.images:
                self.images[image_id] = task_id

    def _persist_new_events(self, task: Task) -> None:
        for event in task.events:
            if event.id is None:
                self._last_event_id += 1
                event.id = self._last_event_id

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
        self.users[user.id] = user
        return deepcopy(self.users[user.id])

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

    def user_delete(self, user: User) -> None:
        self.get_user_by_id(user.id)
        self.users[user.id] = deepcopy(user)
        self.deleted_task_ids.update(
            task_id for task_id, task in self.tasks.items() if task.owner_id == user.id
        )

    def get_user_ids_deleted_before(self, deleted_before: datetime) -> set[UserId]:
        return {
            UserId(user_id)
            for user_id, user in self.users.items()
            if user.deleted_at is not None and user.deleted_at < deleted_before
        }

    def users_purge(self, user_ids: set[UserId]) -> list[ImageId]:
        task_ids = {task_id for task_id, task in self.tasks.items() if task.owner_id in user_ids}
        image_ids = [
            ImageId(image_id) for image_id, task_id in self.images.items() if task_id in task_ids
        ]
        for image_id in image_ids:
            del self.images[image_id]
        for task_id in task_ids:
            del self.tasks[task_id]
        self.deleted_task_ids -= task_ids
        for user_id in user_ids:
            del self.users[user_id]
        return image_ids

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
        return _filter_tasks_by_radius(tasks, filters)

    def task_update(self, task: Task) -> Task:
        if task.id is None:
            raise exceptions.RepositoryException("Cannot update task without id.")
        self.get_task_by_id(task.id)
        self._persist_new_images(task.id, task)
        self._persist_new_events(task)
        self.tasks[task.id] = task
        return deepcopy(task)

    def count_tasks_by_status(self) -> dict[TaskStatus, int]:
        return dict(Counter(task.status for task in self._active_tasks().values()))

    def image_exists(self, image_id: ImageId) -> bool:
        return self.images.get(image_id) in self._active_tasks()

    def images_delete(self, image_ids: list[ImageId]) -> None:
        for image_id in image_ids:
            self.images.pop(image_id, None)


class SQLiteRepository(MatchRepository):
    def __init__(self, session: SQLAlchemySession) -> None:
        self.session = session

    @staticmethod
    def _select_users() -> Select[tuple[db_models.User]]:
        return select(db_models.User).where(db_models.User.deleted_at.is_(None))

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
            deleted_at=obj.deleted_at,
        )

    def _get_user_by_id(self, user_id: int) -> db_models.User:
        statement = self._select_users().filter_by(id=user_id)
        try:
            return self.session.execute(statement).one()[0]
        except sqlalchemy.orm.exc.NoResultFound:
            raise exceptions.UserNotFound

    def create_user(self, user_data: dict) -> User:
        user = User(id=UserId(0), **user_data)
        existing_user = self.session.scalars(
            self._select_users().filter_by(email=user.email)
        ).first()
        if existing_user is not None:
            raise exceptions.EmailAlreadyRegistered
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
        db_obj = self._get_user_by_id(user_id)
        return self._user_to_domain(db_obj)

    def get_user_by_email(self, email: str) -> User:
        statement = self._select_users().filter_by(email=email)
        try:
            db_obj = self.session.execute(statement).one()[0]
        except sqlalchemy.orm.exc.NoResultFound:
            raise exceptions.UserNotFound
        return self._user_to_domain(db_obj)

    def get_user_by_verification_code(self, verification_code: str) -> User:
        statement = self._select_users().filter_by(verification_code=verification_code)
        try:
            db_obj = self.session.execute(statement).one()[0]
        except sqlalchemy.orm.exc.NoResultFound:
            raise exceptions.UserNotFound
        return self._user_to_domain(db_obj)

    def get_users_by_ids(self, user_ids: set[UserId]) -> dict[UserId, User]:
        if not user_ids:
            return {}
        statement = self._select_users().where(db_models.User.id.in_(user_ids))
        db_objs = self.session.scalars(statement).all()
        return {UserId(obj.id): self._user_to_domain(obj) for obj in db_objs}

    def count_users_by_type(self) -> dict[UserType, int]:
        statement = (
            select(db_models.User.user_type, sqlalchemy.func.count())
            .where(db_models.User.deleted_at.is_(None))
            .group_by(db_models.User.user_type)
        )
        return dict(self.session.execute(statement).tuples().all())

    def user_delete(self, user: User) -> None:
        self._get_user_by_id(user.id).deleted_at = user.deleted_at
        self.session.execute(
            update(db_models.Task)
            .where(db_models.Task.owner_id == user.id, db_models.Task.deleted_at.is_(None))
            .values(deleted_at=user.deleted_at)
        )
        self.session.commit()

    def get_user_ids_deleted_before(self, deleted_before: datetime) -> set[UserId]:
        statement = select(db_models.User.id).where(db_models.User.deleted_at < deleted_before)
        return {UserId(user_id) for user_id in self.session.scalars(statement)}

    def users_purge(self, user_ids: set[UserId]) -> list[ImageId]:
        task_ids = select(db_models.Task.id).where(db_models.Task.owner_id.in_(user_ids))
        image_ids = list(
            self.session.scalars(
                select(db_models.Image.id).where(db_models.Image.task_id.in_(task_ids))
            )
        )
        self.session.execute(delete(db_models.Image).where(db_models.Image.task_id.in_(task_ids)))
        self.session.execute(
            delete(db_models.TaskEvent).where(db_models.TaskEvent.task_id.in_(task_ids))
        )
        self.session.execute(delete(db_models.Task).where(db_models.Task.owner_id.in_(user_ids)))
        self.session.execute(delete(db_models.User).where(db_models.User.id.in_(user_ids)))
        self.session.commit()
        return [ImageId(image_id) for image_id in image_ids]

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
        if obj.location_lat is not None and obj.location_lon is not None and obj.location_address:
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
        statement = select(db_models.Task).where(
            db_models.Task.id == task_id, db_models.Task.deleted_at.is_(None)
        )
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
        return (
            select(db_models.Task, view.c.status)
            .join(view, view.c.id == db_models.Task.id)
            .where(db_models.Task.deleted_at.is_(None))
        )

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
        db_obj.location_lat = task.location.lat if task.location else None
        db_obj.location_lon = task.location.lon if task.location else None
        db_obj.location_address = task.location.address if task.location else None
        db_obj.updated_at = task.updated_at

        self._persist_new_images(task.id, task)
        self._persist_new_events(task.id, task)
        self.session.commit()
        return task

    def count_tasks_by_status(self) -> dict[TaskStatus, int]:
        view = db_models.tasks_with_status
        statement = (
            select(view.c.status, sqlalchemy.func.count())
            .join(db_models.Task, db_models.Task.id == view.c.id)
            .where(db_models.Task.deleted_at.is_(None))
            .group_by(view.c.status)
        )
        return {
            TaskStatus(status): count
            for status, count in self.session.execute(statement).tuples().all()
        }

    def image_exists(self, image_id: ImageId) -> bool:
        statement = (
            select(db_models.Image.id)
            .join(db_models.Task, db_models.Task.id == db_models.Image.task_id)
            .where(db_models.Image.id == image_id, db_models.Task.deleted_at.is_(None))
        )
        return self.session.scalar(statement) is not None

    def images_delete(self, image_ids: list[ImageId]) -> None:
        if not image_ids:
            return
        statement = select(db_models.Image).where(db_models.Image.id.in_(image_ids))
        db_images = self.session.scalars(statement).all()
        for db_image in db_images:
            self.session.delete(db_image)
        self.session.commit()
