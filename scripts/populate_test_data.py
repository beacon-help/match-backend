from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta
from datetime import timezone as tz
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.orm.session import Session as SQLAlchemySession

from match.config import Environment, get_config
from match.db import Session
from match.domain.task import Category, TaskEventType
from match.domain.user import UserType, VolunteerProperties
from match.infra import db_models
from match.infra.api.security import hash_password

ALLOWED_ENVS = (Environment.TEST, Environment.DEV)

_APPROVED = [TaskEventType.CREATED, TaskEventType.OFFERED, TaskEventType.APPROVED]
TASK_EVENT_SEQUENCES: list[list[TaskEventType]] = [
    [TaskEventType.CREATED],
    [TaskEventType.CREATED, TaskEventType.OFFERED],
    _APPROVED,
    [*_APPROVED, TaskEventType.SUCCEEDED],
    [*_APPROVED, TaskEventType.FAILED],
    [*_APPROVED, TaskEventType.CLOSED],
]


def _build_users() -> list[db_models.User]:
    now = datetime.now(tz.utc)
    return [
        db_models.User(
            user_type=UserType.VOLUNTEER,
            first_name="Verified",
            last_name="WithPassword",
            email="verified.password@example.com",
            properties=json.dumps([VolunteerProperties.HAS_CAR.value]),
            is_verified=True,
            verification_code="verified-with-password",
            password_hash=hash_password("password123"),
            created_at=now,
        ),
        db_models.User(
            user_type=UserType.VOLUNTEER,
            first_name="Verified",
            last_name="NoPassword",
            email="verified.nopassword@example.com",
            properties=json.dumps([VolunteerProperties.CAN_HOST.value]),
            is_verified=True,
            verification_code="verified-no-password",
            password_hash=None,
            created_at=now,
        ),
        db_models.User(
            user_type=UserType.HELP_SEEKER,
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
            user_type=UserType.VOLUNTEER,
            first_name="Volunteer",
            last_name="AllProperties",
            email="volunteer.all@example.com",
            properties=json.dumps([p.value for p in VolunteerProperties]),
            is_verified=True,
            verification_code="volunteer-all-properties",
            password_hash=hash_password("password123"),
            created_at=now,
        ),
        db_models.User(
            user_type=UserType.VOLUNTEER,
            first_name="Volunteer",
            last_name="User",
            email="volunteer@verified.com",
            properties=json.dumps([VolunteerProperties.HAS_CAR.value]),
            is_verified=True,
            verification_code="volunteer-verified",
            password_hash=hash_password("Password"),
            created_at=now,
        ),
        db_models.User(
            user_type=UserType.HELP_SEEKER,
            first_name="Help",
            last_name="Seeker",
            email="help-seeker@verified.com",
            properties=json.dumps([]),
            is_verified=True,
            verification_code="help-seeker-verified",
            password_hash=hash_password("Password"),
            created_at=now,
        ),
        db_models.User(
            user_type=UserType.HELP_SEEKER,
            first_name="Help",
            last_name="Seeker Plus",
            email="help-seeker+t@verified.com",
            properties=json.dumps([]),
            is_verified=True,
            verification_code="help-seeker-plus-verified",
            password_hash=hash_password("Password"),
            created_at=now,
        ),
    ]


def _add_tasks(session: SQLAlchemySession, owner_id: int, helper_id: int) -> None:
    now = datetime.now(tz.utc)
    categories: list[Category] = list(Category)
    task_data = [
        {
            "title": "Help with grocery shopping",
            "lat": 39.4699,
            "lon": -0.3763,
            "address": "Valencia City Center, Spain",
        },
        {
            "title": "Garden maintenance needed",
            "lat": 39.4550,
            "lon": -0.3840,
            "address": "Ruzafa, Valencia, Spain",
        },
        {
            "title": "Moving assistance required",
            "lat": 39.3700,
            "lon": -0.3200,
            "address": "El Cabanyal, Valencia, Spain",
        },
        {
            "title": "House cleaning service",
            "lat": 39.5500,
            "lon": -0.7500,
            "address": "Bétera, Valencia, Spain",
        },
        {
            "title": "Furniture assembly help",
            "lat": 39.5200,
            "lon": -0.4200,
            "address": "Almàssera, Valencia, Spain",
        },
        {
            "title": "Yard work and landscaping",
            "lat": 39.4100,
            "lon": -0.3800,
            "address": "Sedaví, Valencia, Spain",
        },
        {
            "title": "Home repair assistance",
            "lat": 39.3900,
            "lon": -0.4100,
            "address": "Picanya, Valencia, Spain",
        },
        {
            "title": "Elderly care support",
            "lat": 39.4900,
            "lon": -0.4100,
            "address": "La Torre, Valencia, Spain",
        },
    ]
    for i, event_types in enumerate(TASK_EVENT_SEQUENCES):
        gaps = [timedelta(minutes=random.randint(10, 48 * 60)) for _ in event_types[1:]]
        created_at = now - sum(gaps, timedelta())
        occurred_ats = [created_at]
        for gap in gaps:
            occurred_ats.append(occurred_ats[-1] + gap)
        category = categories[i % len(categories)]
        has_helper = len(event_types) > 1
        data = task_data[i % len(task_data)]
        task = db_models.Task(
            title=data["title"],
            description=f"A task ending with {event_types[-1].value}",
            owner_id=owner_id,
            helper_id=helper_id if has_helper else None,
            category=category.value,
            updated_at=now if has_helper else None,
            created_at=created_at,
            location_lat=data["lat"],
            location_lon=data["lon"],
            location_address=data["address"],
        )
        session.add(task)
        session.flush()
        session.add_all(
            db_models.TaskEvent(
                task_id=task.id,
                type=event_type.value,
                actor_id=helper_id if event_type == TaskEventType.OFFERED else owner_id,
                helper_id=None if event_type == TaskEventType.CREATED else helper_id,
                occurred_at=occurred_at,
            )
            for event_type, occurred_at in zip(event_types, occurred_ats)
        )


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

        _add_tasks(session, owner_id=users[0].id, helper_id=users[1].id)
        _add_tasks(session, owner_id=users[6].id, helper_id=users[1].id)

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    main()
