from dataclasses import dataclass, field
from datetime import datetime
from datetime import timezone as tz
from enum import StrEnum
from typing import NewType

from match.domain.exceptions import DomainException, InvalidLocation, InvalidTaskAction, NotAnOwner
from match.domain.user import User, UserId

ImageId = NewType("ImageId", str)


class TaskStatus(StrEnum):
    OPEN = "open"
    PENDING = "pending"
    APPROVED = "approved"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


FINISHED_STATUSES = (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED)


class Category(StrEnum):
    TRANSPORT = "transport people"
    FOOD = "food"
    ACCOMMODATION = "accommodation"
    CLOTHES = "clothes"
    MEDICAL_HELP = "medical help"
    CLEAN = "clean"
    REPAIR = "repair"
    OTHER = "other"


@dataclass(frozen=True)
class HelperOffer:
    user_id: UserId
    offered_at: datetime
    message: str


class TaskEventType(StrEnum):
    CREATED = "created"
    OFFERED = "offered"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CLOSED = "closed"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class TaskEvent:
    type: TaskEventType
    actor_id: UserId
    occurred_at: datetime
    helper_id: UserId | None = None
    message: str | None = None
    id: int | None = None


def _validate_coordinates(lat: float, lon: float, radius_km: float | None = None) -> None:
    if not -90 <= lat <= 90:
        raise InvalidLocation("Invalid latitude.")
    if not -180 <= lon <= 180:
        raise InvalidLocation("Invalid longitude.")
    if radius_km is not None and radius_km <= 0:
        raise InvalidLocation("Invalid radius.")


@dataclass(frozen=True)
class Location:
    lat: float
    lon: float
    address: str

    def __post_init__(self) -> None:
        _validate_coordinates(self.lat, self.lon)
        if not self.address.strip():
            raise InvalidLocation("Address is required.")


@dataclass(frozen=True)
class LocationRadius:
    lat: float
    lon: float
    radius_km: float

    def __post_init__(self) -> None:
        _validate_coordinates(self.lat, self.lon, self.radius_km)


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
    images: list[ImageId] = field(default_factory=list)
    events: list[TaskEvent] = field(default_factory=list)
    updated_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz.utc))

    def __repr__(self) -> str:
        return f"<Task {self.id}>"

    @property
    def helper_offers(self) -> list[HelperOffer]:
        return [
            HelperOffer(
                user_id=event.actor_id, offered_at=event.occurred_at, message=event.message or ""
            )
            for event in self.events
            if event.type == TaskEventType.OFFERED
        ]

    @property
    def participant_ids(self) -> set[UserId]:
        user_ids = {self.owner_id}
        if self.helper_id is not None:
            user_ids.add(self.helper_id)
        for event in self.events:
            user_ids.add(event.actor_id)
            if event.helper_id is not None:
                user_ids.add(event.helper_id)
        return user_ids

    @classmethod
    def create_task(
        cls,
        owner: User,
        title: str,
        description: str,
        category: Category,
        location: Location | None,
    ) -> "Task":
        created_at = datetime.now(tz.utc)
        return cls(
            id=None,
            status=TaskStatus.OPEN,
            owner_id=owner.id,
            helper_id=None,
            title=title,
            description=description,
            category=category,
            location=location,
            events=[
                TaskEvent(type=TaskEventType.CREATED, actor_id=owner.id, occurred_at=created_at)
            ],
            created_at=created_at,
        )

    def _record_event(
        self,
        type: TaskEventType,
        actor_id: UserId,
        helper_id: UserId | None = None,
        message: str | None = None,
    ) -> None:
        self.events.append(
            TaskEvent(
                type=type,
                actor_id=actor_id,
                occurred_at=datetime.now(tz.utc),
                helper_id=helper_id,
                message=message,
            )
        )

    def _post_task_update(self) -> None:
        self.updated_at = datetime.now(tz.utc)

    def _validate_owner(self, user: User) -> None:
        if self.owner_id != user.id:
            raise NotAnOwner("User is not an owner.")

    def validate_editable_by(self, user: User) -> None:
        self._validate_owner(user)
        if self.status in FINISHED_STATUSES:
            raise InvalidTaskAction("Finished tasks cannot be changed.")

    def join(self, helper: User, message: str) -> None:
        if self.status != TaskStatus.OPEN:
            raise InvalidTaskAction(f"Cannot join this Task with status {self.status}")
        if self.owner_id == helper.id:
            raise InvalidTaskAction("Owner cannot join its own Task.")
        self.helper_id = helper.id
        self.status = TaskStatus.PENDING
        self._record_event(
            TaskEventType.OFFERED, actor_id=helper.id, helper_id=helper.id, message=message
        )
        self._post_task_update()

    def approve_helper(self, user: User, helper_id: UserId) -> None:
        self._validate_owner(user)
        if self.status != TaskStatus.PENDING or not self.helper_id:
            raise InvalidTaskAction("Cannot approve helper.")
        if self.helper_id != helper_id:
            raise InvalidTaskAction(f"Incorrect helper_id {helper_id}.")
        self.status = TaskStatus.APPROVED
        self._record_event(TaskEventType.APPROVED, actor_id=user.id, helper_id=helper_id)
        self._post_task_update()

    def reject_helper(self, user: User, helper_id: UserId) -> None:
        self._validate_owner(user)
        if self.status != TaskStatus.PENDING:
            raise InvalidTaskAction("Cannot reject helper.")
        if self.helper_id != helper_id:
            raise InvalidTaskAction(f"Incorrect helper_id {helper_id}")
        self.status = TaskStatus.OPEN
        self.helper_id = None
        self._record_event(TaskEventType.REJECTED, actor_id=user.id, helper_id=helper_id)
        self._post_task_update()

    def withdraw(self, helper: User) -> None:
        if self.status not in (TaskStatus.PENDING, TaskStatus.APPROVED):
            raise InvalidTaskAction("Cannot withdraw from this task.")
        if self.helper_id != helper.id:
            raise InvalidTaskAction("User is not the helper of this task.")
        self.status = TaskStatus.OPEN
        self.helper_id = None
        self._record_event(TaskEventType.WITHDRAWN, actor_id=helper.id, helper_id=helper.id)
        self._post_task_update()

    def report_succeeded(self, user: User) -> None:
        self._validate_owner(user)
        if self.status != TaskStatus.APPROVED:
            raise InvalidTaskAction("Cannot report this task.")
        self.status = TaskStatus.SUCCEEDED
        self._record_event(TaskEventType.SUCCEEDED, actor_id=user.id, helper_id=self.helper_id)
        self._post_task_update()

    def report_failed(self, user: User) -> None:
        self._validate_owner(user)
        if self.status != TaskStatus.APPROVED:
            raise InvalidTaskAction("Cannot report this task.")
        self.status = TaskStatus.FAILED
        self._record_event(TaskEventType.FAILED, actor_id=user.id, helper_id=self.helper_id)
        self._post_task_update()

    def edit(
        self,
        user: User,
        title: str | None = None,
        description: str | None = None,
        category: Category | None = None,
        location: Location | None = None,
    ) -> None:
        self.validate_editable_by(user)
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if category is not None:
            self.category = category
        if location is not None:
            self.location = location
        self._post_task_update()

    def add_images(self, user: User, image_ids: list[ImageId]) -> None:
        self.validate_editable_by(user)
        self.images.extend(image_ids)
        self._post_task_update()

    def remove_image(self, user: User, image_id: ImageId) -> None:
        self.validate_editable_by(user)
        if image_id not in self.images:
            raise DomainException(f"Image {image_id} not found on task.")

        self.images.remove(image_id)
        self._post_task_update()

    def close(self, user: User) -> None:
        self._validate_owner(user)
        if self.status == TaskStatus.CANCELLED:
            raise InvalidTaskAction("Task already closed.")
        if self.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED):
            raise InvalidTaskAction("Task is already finished.")
        self.status = TaskStatus.CANCELLED
        self._record_event(TaskEventType.CLOSED, actor_id=user.id)
        self._post_task_update()
