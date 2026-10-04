from datetime import datetime
from datetime import timezone as tz
from uuid import uuid4

import pytest

from match.domain import exceptions as domain_exceptions
from match.domain.user import User, UserType


def build_user(
    id,
    user_type=UserType.HELP_SEEKER,
    first_name="John",
    last_name="Test",
    email="test@me.com",
    is_verified=True,
    verification_code=uuid4(),
):
    return User(
        id=id,
        user_type=user_type,
        first_name=first_name,
        last_name=last_name,
        email=email,
        is_verified=is_verified,
        verification_code=verification_code,
    )


VALID_UUID = uuid4()


@pytest.mark.parametrize(
    "user,verification_code,expected_error",
    (
        pytest.param(
            build_user(1, is_verified=True),
            uuid4(),
            domain_exceptions.UserNotPendingVerification,
            id="user already verified",
        ),
        pytest.param(
            build_user(id=1, is_verified=True, verification_code=VALID_UUID),
            VALID_UUID,
            domain_exceptions.UserNotPendingVerification,
            id="user already verified, valid code",
        ),
        pytest.param(
            build_user(1, is_verified=False),
            uuid4(),
            domain_exceptions.UserVerificationCodeInvalid,
            id="user pending verification, invalid code",
        ),
    ),
)
def test_fail_user_verification(user, verification_code, expected_error):
    with pytest.raises(expected_error) as e:
        user.verify(verification_code)
        assert issubclass(e, domain_exceptions.UserVerificationError)


def test_user_verification_happy_path():
    uuid = uuid4()
    user = build_user(1, is_verified=False, verification_code=uuid)
    user.verify(uuid)
    assert user.is_verified


def test_delete_marks_user_as_deleted():
    user = build_user(1)
    before = datetime.now(tz.utc)

    user.delete()

    assert before <= user.deleted_at <= datetime.now(tz.utc)


def test_delete_already_deleted_user_raises():
    user = build_user(1)
    user.delete()

    with pytest.raises(domain_exceptions.UserAlreadyDeleted):
        user.delete()
