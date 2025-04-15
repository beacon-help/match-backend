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
    PENDING = "pending"
    APPROVED = "approved"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    TASK_TYPE_1 = "task_type_1"


class TaskCreationRequestSchema(BaseModel):
    title: str
    description: str


class TaskSchema(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime | None
    status: TaskStatus
    owner_id: int
    helper_id: int | None
    description: str
