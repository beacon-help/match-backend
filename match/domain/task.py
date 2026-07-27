from dataclasses import dataclass, field
from datetime import datetime
from datetime import timezone as tz
from enum import StrEnum

from match.domain.exceptions import InvalidTaskAction, NotAnOwner
from match.domain.user import User, UserId


class TaskStatus(StrEnum):
    OPEN = "open"
    PENDING = "pending"
    APPROVED = "approved"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Category(StrEnum):
    TRANSPORT = "transport people"
    FOOD = "food"
    ACCOMMODATION = "accommodation"
    CLOTHES = "clothes"
    MEDICAL_HELP = "medical help"
    CLEAN = "clean"
    REPAIR = "repair"
    OTHER = "other"


@dataclass
class Location:
    lat: float
    lon: float
    address: str


@dataclass(frozen=True)
class LocationRadius:
    lat: float
    lon: float
    radius_km: float


@dataclass
class Task:
    id: int | None
    title: str
    description: str
    owner_id: UserId
    status: TaskStatus
    category: Category
    location: Location | None
    helper_id: UserId | None = None
    updated_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz.utc))

    @classmethod
    def create_task(
        cls,
        owner: User,
        title: str,
        description: str,
        category: Category,
        location: Location | None,
    ) -> "Task":
        return cls(
            id=None,
            status=TaskStatus.OPEN,
            owner_id=owner.id,
            helper_id=None,
            title=title,
            description=description,
            category=category,
            location=location,
        )

    def _post_task_update(self) -> None:
        self.updated_at = datetime.now(tz.utc)

    def _validate_owner(self, user: User) -> None:
        if self.owner_id != user.id:
            raise NotAnOwner("User is not an owner.")

    def join(self, helper_id: int) -> None:
        if self.status != TaskStatus.OPEN:
            raise InvalidTaskAction(f"Cannot join this Task with status {self.status}")
        if self.owner_id == helper_id:
            raise InvalidTaskAction("Owner cannot join its own Task.")
        self.helper_id = helper_id
        self.status = TaskStatus.PENDING
        self._post_task_update()

    def approve_helper(self, user: User, helper_id: UserId) -> None:
        try:
            self._validate_owner(user)
        except NotAnOwner as e:
            raise InvalidTaskAction from e

        if self.status != TaskStatus.PENDING or not self.helper_id:
            raise InvalidTaskAction("Cannot approve helper.")
        if self.helper_id != helper_id:
            raise InvalidTaskAction(f"Incorrect helper_id {helper_id}.")
        self.status = TaskStatus.APPROVED
        self._post_task_update()

    def reject_helper(self, user: User, helper_id: UserId) -> None:
        try:
            self._validate_owner(user)
        except NotAnOwner as e:
            raise InvalidTaskAction from e

        if self.status not in (TaskStatus.PENDING, TaskStatus.APPROVED):
            raise InvalidTaskAction("Cannot reject helper.")
        if self.helper_id is None:
            raise InvalidTaskAction("No helper to reject.")
        if self.helper_id != helper_id:
            raise InvalidTaskAction(f"Incorrect helper_id {helper_id}")
        self.status = TaskStatus.OPEN
        self.helper_id = None
        self._post_task_update()

    def report_succeeded(self, user: User) -> None:
        try:
            self._validate_owner(user)
        except NotAnOwner as e:
            raise InvalidTaskAction from e

        if self.status != TaskStatus.APPROVED:
            raise InvalidTaskAction("Cannot report this task.")
        self.status = TaskStatus.SUCCEEDED
        self._post_task_update()

    def report_failed(self, user: User) -> None:
        try:
            self._validate_owner(user)
        except NotAnOwner as e:
            raise InvalidTaskAction from e

        if self.status != TaskStatus.APPROVED:
            raise InvalidTaskAction("Cannot report this task.")
        self.status = TaskStatus.FAILED
        self._post_task_update()

    def edit(
        self,
        user: User,
        title: str | None = None,
        description: str | None = None,
        category: Category | None = None,
        location: Location | None = None,
    ) -> None:
        try:
            self._validate_owner(user)
        except NotAnOwner as e:
            raise InvalidTaskAction from e

        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if category is not None:
            self.category = category
        if location is not None:
            self.location = location
        self._post_task_update()

    def close(self, user: User) -> None:
        try:
            self._validate_owner(user)
        except NotAnOwner as e:
            raise InvalidTaskAction from e

        if self.status == TaskStatus.CANCELLED:
            raise Exception("Task already closed.")
        if self.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED):
            raise Exception("Task is already finished.")
        self.status = TaskStatus.CANCELLED
        self._post_task_update()
