from sentry_sdk.scrubber import EventScrubber

from match.config import SENTRY_DENYLIST


def test_sentry_scrubs_password_change_fields() -> None:
    event = {"request": {"data": {"current_password": "old-secret", "new_password": "new-secret"}}}

    EventScrubber(denylist=SENTRY_DENYLIST, send_default_pii=True).scrub_event(event)

    data = event["request"]["data"]
    assert data["current_password"] != "old-secret"
    assert data["new_password"] != "new-secret"
