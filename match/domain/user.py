from dataclasses import dataclass

from match.domain.exceptions import UserNotPendingVerification, UserVerificationCodeInvalid


@dataclass
class User:
    id: int
    first_name: str
    last_name: str
    email: str

    is_verified: bool
    verification_code: str | None

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
