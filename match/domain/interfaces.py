import abc
from datetime import datetime
from typing import TypedDict

from match.domain.task import Category, ImageId, LocationRadius, Task, TaskStatus
from match.domain.user import User, UserId, UserType


class TaskFilter(TypedDict, total=False):
    status: TaskStatus
    category: Category
    owner_id: int
    helper_id: int | None
    location_radius: LocationRadius


class MatchRepository(abc.ABC):
    @abc.abstractmethod
    def create_user(self, user_data: dict) -> User: ...

    @abc.abstractmethod
    def get_user_by_id(self, user_id: int) -> User: ...

    @abc.abstractmethod
    def get_user_by_email(self, email: str) -> User: ...

    @abc.abstractmethod
    def get_user_by_verification_code(self, verification_code: str) -> User: ...

    @abc.abstractmethod
    def get_users_by_ids(self, user_ids: set[UserId]) -> dict[UserId, User]: ...

    @abc.abstractmethod
    def user_update(self, user: User) -> User: ...

    @abc.abstractmethod
    def count_users_by_type(self) -> dict[UserType, int]: ...

    @abc.abstractmethod
    def user_delete(self, user: User) -> None: ...

    @abc.abstractmethod
    def get_user_ids_deleted_before(self, deleted_before: datetime) -> set[UserId]: ...

    @abc.abstractmethod
    def users_purge(self, user_ids: set[UserId]) -> list[ImageId]: ...

    @abc.abstractmethod
    def create_task(self, task: Task) -> Task: ...

    @abc.abstractmethod
    def get_task_by_id(self, task_id: int) -> Task: ...

    @abc.abstractmethod
    def get_tasks(self, filters: TaskFilter | None = None) -> list[Task]: ...

    @abc.abstractmethod
    def task_update(self, task: Task) -> Task: ...

    @abc.abstractmethod
    def count_tasks_by_status(self) -> dict[TaskStatus, int]: ...

    @abc.abstractmethod
    def image_exists(self, image_id: ImageId) -> bool: ...

    @abc.abstractmethod
    def images_delete(self, image_ids: list[ImageId]) -> None: ...


class PasswordHasher(abc.ABC):
    @abc.abstractmethod
    def hash(self, password: str) -> str: ...

    @abc.abstractmethod
    def verify(self, password: str, password_hash: str) -> bool: ...


class MessageClient(abc.ABC):
    @abc.abstractmethod
    def send_message(self, message: str, user: User) -> None: ...


class ImageRepository(abc.ABC):
    @abc.abstractmethod
    def upload(self, image: bytes) -> str: ...

    @abc.abstractmethod
    def read(self, image_ids: list[str]) -> dict[str, bytes]: ...

    @abc.abstractmethod
    def delete(self, image_id: str) -> None: ...
