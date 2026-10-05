import argparse
from datetime import datetime, timedelta
from datetime import timezone as tz

from match.bootstrap import build_service
from match.db import Session

RETENTION_PERIOD = timedelta(days=30)


def iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=tz.utc)
    return parsed.astimezone(tz.utc)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Permanently remove soft-deleted user accounts.")
    parser.add_argument(
        "--before",
        type=iso_datetime,
        default=datetime.now(tz.utc) - RETENTION_PERIOD,
        help="Purge accounts deleted before this ISO-8601 timestamp (UTC if no offset). "
        "Defaults to 30 days ago.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    deleted_before = parse_args(argv).before
    with Session() as session:
        purged = build_service(session).purge_deleted_users(deleted_before)
    print(f"Purged {purged} account(s) deleted before {deleted_before.isoformat()}.")


if __name__ == "__main__":
    main()
