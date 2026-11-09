import enum
from datetime import datetime
from typing import Annotated, Any, Self

from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    EmailStr,
    PlainValidator,
    StringConstraints,
    model_validator,
)
from pydantic_extra_types.coordinate import Latitude, Longitude

from match.domain.task import Category, TaskEventType, TaskStatus
from match.domain.user import UserType, VolunteerProperties

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Password = Annotated[str, StringConstraints(min_length=8)]


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


class HelpseekerUpdateRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: Name
    last_name: Name


class VolunteerUpdateRequestSchema(HelpseekerUpdateRequestSchema):
    properties: list[VolunteerProperties]


# Documents both body shapes but passes the body through unvalidated; the API validates it
# with the schema matching the signed-in user's type.
ProfileUpdateBody = Annotated[
    Any,
    PlainValidator(
        lambda body: body,
        json_schema_input_type=HelpseekerUpdateRequestSchema | VolunteerUpdateRequestSchema,
    ),
]


class PasswordChangeRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password: Password

    @model_validator(mode="after")
    def check_new_password_differs(self) -> Self:
        if self.new_password == self.current_password:
            raise ValueError("New password must differ from the current password.")
        return self


class UserSchema(BaseModel):
    id: int
    user_type: UserType
    first_name: str
    last_name: str
    email: EmailStr
    is_verified: bool
    properties: list[VolunteerProperties]


class PublicUserSchema(BaseModel):
    id: int
    user_type: UserType
    first_name: str


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequestSchema(BaseModel):
    refresh_token: str


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


class ImageSchema(BaseModel):
    id: str
    path: AnyUrl


class TaskEventSchema(BaseModel):
    id: int
    type: TaskEventType
    actor: TaskUserSchema
    helper: TaskUserSchema | None
    message: str | None
    occurred_at: datetime


class TaskSchema(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime | None
    status: TaskStatus
    owner: TaskUserSchema
    helper: TaskUserSchema | None
    helper_offers: list
    description: str
    location: Location
    category: Category
    images: list[ImageSchema]
    events: list[TaskEventSchema]


class TaskLocationSchema(BaseModel):
    id: int
    location: Location


class TaskAction(enum.StrEnum):
    JOIN = "join"
    APPROVE = "approve"
    REJECT = "reject"
    WITHDRAW = "withdraw"
    CLOSE = "close"
    REPORT_SUCCESS = "report_success"
    REPORT_FAILURE = "report_failure"


class TaskStats(BaseModel):
    total: int
    successful: int
    in_progress: int


class UserStats(BaseModel):
    total_helpers: int
    total_help_seekers: int


class Stats(BaseModel):
    tasks: TaskStats
    users: UserStats
