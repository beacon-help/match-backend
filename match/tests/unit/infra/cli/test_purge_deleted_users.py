from datetime import datetime, timedelta
from datetime import timezone as tz

import pytest

from match.infra.cli.purge_deleted_users import parse_args


def test_before_defaults_to_30_days_ago():
    before = parse_args([]).before

    assert abs(before - (datetime.now(tz.utc) - timedelta(days=30))) < timedelta(minutes=1)


@pytest.mark.parametrize(
    "value",
    (
        pytest.param("2026-09-04T10:00:00", id="naive-is-utc"),
        pytest.param("2026-09-04T12:00:00+02:00", id="offset-converted-to-utc"),
    ),
)
def test_before_is_parsed_as_utc(value):
    before = parse_args(["--before", value]).before

    assert before == datetime(2026, 9, 4, 10, tzinfo=tz.utc)
    assert before.tzinfo == tz.utc
