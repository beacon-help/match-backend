from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr


class UserCreationRequestSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr


class UserSchema(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr


class TaskStatus(Enum):
    OPEN = "open"
    PENDING_APPROVAL = "pending_approval"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskType(Enum):
    TASK_TYPE_1 = "task_type_1"


class TaskCreationRequestSchema(BaseModel):
    name: str
    type: TaskType
    description: str
    location: str


class TaskSchema(BaseModel):
    id: int
    name: str
    created_at: datetime
    status: TaskStatus
    requester_id: int
    helper_id: int | None = None
    type: TaskType
    description: str
    location: str
