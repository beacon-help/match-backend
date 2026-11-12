import json

from pydantic import BaseModel
from sentry_sdk.scrubber import EventScrubber
from sentry_sdk.serializer import serialize

from match.config import SENTRY_DENYLIST
from match.infra.api.schemas import HelpseekerCreationRequestSchema, PasswordChangeRequestSchema


def test_sentry_scrubs_password_change_fields() -> None:
    event = {"request": {"data": {"current_password": "old-secret", "new_password": "new-secret"}}}

    EventScrubber(denylist=SENTRY_DENYLIST, send_default_pii=True).scrub_event(event)

    data = event["request"]["data"]
    assert data["current_password"] != "old-secret"
    assert data["new_password"] != "new-secret"


def _serialized_frame_with_params(params: BaseModel) -> str:
    event = {
        "exception": {
            "values": [
                {"stacktrace": {"frames": [{"function": "handler", "vars": {"params": params}}]}}
            ]
        }
    }
    EventScrubber(denylist=SENTRY_DENYLIST, send_default_pii=True).scrub_event(event)
    return json.dumps(serialize(event))


def test_sentry_frame_locals_do_not_expose_password_change_fields() -> None:
    params = PasswordChangeRequestSchema(current_password="old-secret", new_password="new-secret")

    serialized = _serialized_frame_with_params(params)

    assert "old-secret" not in serialized
    assert "new-secret" not in serialized


def test_sentry_frame_locals_do_not_expose_signup_password() -> None:
    params = HelpseekerCreationRequestSchema(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        password="signup-secret",
    )

    serialized = _serialized_frame_with_params(params)

    assert "Ada" in serialized
    assert "signup-secret" not in serialized
