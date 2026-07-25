from __future__ import annotations

import json
import sys
from datetime import datetime
from datetime import timezone as tz
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from match.config import Environment, get_config  # noqa: E402
from match.db import Session  # noqa: E402
from match.domain.task import Category, TaskStatus  # noqa: E402
from match.domain.user import VolunteerProperties  # noqa: E402
from match.infra import db_models  # noqa: E402
from match.infra.api.security import hash_password  # noqa: E402

ALLOWED_ENVS = (Environment.TEST, Environment.DEV)


def _build_users() -> list[db_models.User]:
    now = datetime.now(tz.utc)
    return [
        db_models.User(
            first_name="Verified",
            last_name="WithPassword",
            email="verified.password@example.com",
            properties=json.dumps([VolunteerProperties.has_car.value]),
            is_verified=True,
            verification_code="verified-with-password",
            password_hash=hash_password("password123"),
            created_at=now,
        ),
        db_models.User(
            first_name="Verified",
            last_name="NoPassword",
            email="verified.nopassword@example.com",
            properties=json.dumps([VolunteerProperties.can_host.value]),
            is_verified=True,
            verification_code="verified-no-password",
            password_hash=None,
            created_at=now,
        ),
        db_models.User(
            first_name="Unverified",
            last_name="Pending",
            email="unverified.pending@example.com",
            properties=json.dumps([]),
            is_verified=False,
            verification_code="unverified-pending",
            password_hash=None,
            created_at=now,
        ),
        db_models.User(
            first_name="Volunteer",
            last_name="AllProperties",
            email="volunteer.all@example.com",
            properties=json.dumps([p.value for p in VolunteerProperties]),
            is_verified=True,
            verification_code="volunteer-all-properties",
            password_hash=hash_password("password123"),
            created_at=now,
        ),
    ]


def _build_tasks(owner_id: int, helper_id: int) -> list[db_models.Task]:
    now = datetime.now(tz.utc)
    statuses: list[TaskStatus] = list(TaskStatus)
    categories: list[Category] = list(Category)
    tasks = []
    for i, status in enumerate(statuses):
        category = categories[i % len(categories)]
        has_helper = status != TaskStatus.OPEN
        tasks.append(
            db_models.Task(
                title=f"Task {status.value}",
                description=f"A task with status {status.value}",
                owner_id=owner_id,
                helper_id=helper_id if has_helper else None,
                status=status.value,
                category=category.value,
                updated_at=now if has_helper else None,
                created_at=now,
                location_lat=40.7128,
                location_lon=-74.0060,
                location_address="New York, NY",
            )
        )
    return tasks


def main() -> None:
    config = get_config()
    if config.ENV not in ALLOWED_ENVS:
        raise RuntimeError(
            f"Refusing to populate test data: ENV={config.ENV.value!r}, "
            f"expected one of {[env.value for env in ALLOWED_ENVS]}."
        )

    session = Session()
    try:
        users = _build_users()
        for user in users:
            session.add(user)
        session.flush()

        tasks = _build_tasks(owner_id=users[0].id, helper_id=users[1].id)
        for task in tasks:
            session.add(task)

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    main()
