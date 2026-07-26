from __future__ import annotations

import json
import sys
from datetime import datetime
from datetime import timezone as tz
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from match.config import Environment, get_config
from match.db import Session
from match.domain.task import Category, TaskStatus
from match.domain.user import VolunteerProperties
from match.infra import db_models
from match.infra.api.security import hash_password

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
        db_models.User(
            first_name="Volunteer",
            last_name="User",
            email="volunteer@verified.com",
            properties=json.dumps([VolunteerProperties.has_car.value]),
            is_verified=True,
            verification_code="volunteer-verified",
            password_hash=hash_password("Password"),
            created_at=now,
        ),
        db_models.User(
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


def _build_tasks(owner_id: int, helper_id: int) -> list[db_models.Task]:
    now = datetime.now(tz.utc)
    statuses: list[TaskStatus] = list(TaskStatus)
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
    tasks = []
    for i, status in enumerate(statuses):
        category = categories[i % len(categories)]
        has_helper = status != TaskStatus.OPEN
        data = task_data[i % len(task_data)]
        tasks.append(
            db_models.Task(
                title=data["title"],
                description=f"A task with status {status.value}",
                owner_id=owner_id,
                helper_id=helper_id if has_helper else None,
                status=status.value,
                category=category.value,
                updated_at=now if has_helper else None,
                created_at=now,
                location_lat=data["lat"],
                location_lon=data["lon"],
                location_address=data["address"],
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

        new_user_tasks = _build_tasks(owner_id=users[6].id, helper_id=users[1].id)
        for task in new_user_tasks:
            session.add(task)

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    main()
