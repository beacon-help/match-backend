import enum
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr
from pydantic_extra_types.coordinate import Latitude, Longitude

from match.domain.task import Category
from match.domain.user import UserType, VolunteerProperties


class UserCreationBaseSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str


class HelpseekerCreationRequestSchema(UserCreationBaseSchema):
    model_config = ConfigDict(extra="forbid")


class VolunteerCreationRequestSchema(UserCreationBaseSchema):
    model_config = ConfigDict(extra="forbid")

    properties: list[VolunteerProperties]


class UserSchema(BaseModel):
    id: int
    user_type: UserType
    first_name: str
    last_name: str
    email: EmailStr
    is_verified: bool


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequestSchema(BaseModel):
    refresh_token: str


class TaskStatus(Enum):
    OPEN = "open"
    PENDING = "pending"
    APPROVED = "approved"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    TASK_TYPE_1 = "task_type_1"


class Location(BaseModel):
    lat: Latitude
    lon: Longitude
    address: str


class TaskCreationRequestSchema(BaseModel):
    title: str
    description: str
    category: Category
    location: Location


class TaskEditRequestSchema(BaseModel):
    title: str
    description: str
    category: Category
    location: Location | None


class PublicTaskSchema(BaseModel):
    id: int
    title: str
    status: TaskStatus
    location: Location
    category: Category


class TaskUserSchema(BaseModel):
    id: int
    first_name: str


class TaskSchema(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime | None
    status: TaskStatus
    owner: TaskUserSchema
    helper: TaskUserSchema | None
    description: str
    location: Location
    category: Category


class TaskLocationSchema(BaseModel):
    id: int
    location: Location


class TaskAction(enum.StrEnum):
    JOIN = "join"
    APPROVE = "approve"
    REJECT = "reject"
    CLOSE = "close"
    REPORT_SUCCESS = "report_success"
    REPORT_FAILURE = "report_failure"
