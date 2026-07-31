import uuid
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import NewType

from match.domain.exceptions import UserNotPendingVerification, UserVerificationCodeInvalid


def generate_uuid_as_str() -> str:
    return str(uuid.uuid4())


UserId = NewType("UserId", int)


class UserType(StrEnum):
    HELP_SEEKER = "help-seeker"
    VOLUNTEER = "volunteer"


@dataclass
class User:
    id: UserId
    user_type: UserType
    first_name: str
    last_name: str
    email: str
    properties: list[str] = field(default_factory=list)

    is_verified: bool = field(default=False)
    verification_code: str = field(default_factory=generate_uuid_as_str)
    password_hash: str | None = field(default=None)

    def __repr__(self) -> str:
        return f"<User {self.id}>"

    @property
    def is_pending_verification(self) -> bool:
        return bool(self.verification_code) and not self.is_verified

    def verify(self, code: str) -> "User":
        if not self.is_pending_verification:
            raise UserNotPendingVerification(f"User {self} is not pending a verification.")
        if not code == self.verification_code:
            raise UserVerificationCodeInvalid(f"User {self} incorrect verification code.")
        self.is_verified = True
        return self


def create_user_verification_message(user: User, verification_url: str) -> str:
    return f"""Hello, {user.first_name}, click: {verification_url} """


class VolunteerProperties(Enum):
    HAS_CAR = "has_car"
    CAN_HOST = "can_host"
    CAN_WORK_PHYSICAL = "can_work_physical"
    HAS_TOOLS = "has_tools"
