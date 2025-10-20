import uuid
from dataclasses import dataclass, field

from match.domain.exceptions import UserNotPendingVerification, UserVerificationCodeInvalid


def generate_uuid_as_str() -> str:
    return str(uuid.uuid4())


UserId = int


@dataclass
class User:
    id: UserId
    first_name: str
    last_name: str
    email: str

    is_verified: bool = field(default=False)
    verification_code: str = field(default_factory=generate_uuid_as_str)

    def __repr__(self) -> str:
        return f"User {self.id}"

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
