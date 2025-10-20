from dataclasses import dataclass, field
from datetime import datetime
from datetime import timezone as tz
from enum import StrEnum

from match.domain.user import User, UserId


class TaskStatus(StrEnum):
    OPEN = "open"
    PENDING = "pending"
    APPROVED = "approved"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    id: int | None
    title: str
    description: str
    owner_id: UserId
    status: TaskStatus
    helper_id: UserId | None = None
    updated_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz.utc))

    @classmethod
    def create_task(cls, owner: User, title: str, description: str) -> "Task":
        return cls(
            id=None,
            status=TaskStatus.OPEN,
            owner_id=owner.id,
            helper_id=None,
            title=title,
            description=description,
        )

    def _post_task_update(self) -> None:
        self.updated_at = datetime.now(tz.utc)

    def _validate_owner(self, user: User) -> None:
        if self.owner_id != user.id:
            raise Exception("User is not an owner.")

    def join(self, helper_id: int) -> None:
        if self.status != TaskStatus.OPEN:
            raise Exception(f"Cannot join this Task with status {self.status}")
        if self.owner_id == helper_id:
            raise Exception("Owner cannot join its own Task.")
        self.helper_id = helper_id
        self.status = TaskStatus.PENDING
        self._post_task_update()

    def approve_helper(self, owner: User, helper_id: UserId) -> None:
        self._validate_owner(owner)
        if self.status != TaskStatus.PENDING or not self.helper_id:
            raise Exception("Cannot approve helper.")
        if self.helper_id != helper_id:
            raise Exception(f"Incorrect helper_id {helper_id}.")
        self.status = TaskStatus.APPROVED
        self._post_task_update()

    def reject_helper(self, owner: User, helper_id: UserId) -> None:
        self._validate_owner(owner)
        if self.status not in (TaskStatus.PENDING, TaskStatus.APPROVED):
            raise Exception("Cannot reject helper.")
        if self.helper_id is None:
            raise Exception("No helper to reject.")
        if self.helper_id != helper_id:
            raise Exception(f"Incorrect helper_id {helper_id}")
        self.status = TaskStatus.OPEN
        self.helper_id = None
        self._post_task_update()

    def report_succeeded(self, user: User) -> None:
        self._validate_owner(user)
        if self.status != TaskStatus.APPROVED:
            raise Exception("Cannot report this task.")
        self.status = TaskStatus.SUCCEEDED
        self._post_task_update()

    def report_failed(self, user: User) -> None:
        self._validate_owner(user)
        if self.status != TaskStatus.APPROVED:
            raise Exception("Cannot report this task.")
        self.status = TaskStatus.FAILED
        self._post_task_update()

    def close(self, user: User) -> None:
        self._validate_owner(user)
        if self.status == TaskStatus.CANCELLED:
            raise Exception("Task already closed.")
        if self.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED):
            raise Exception("Task is already finished.")
        self.status = TaskStatus.CANCELLED
        self._post_task_update()
