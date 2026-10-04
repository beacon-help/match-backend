from datetime import datetime, timedelta
from datetime import timezone as tz
from http import HTTPStatus

import pytest
from sqlalchemy import text

from match.db import Session
from match.infra.cli.purge_deleted_users import main as purge_deleted_users
from match.tests.conftest import build_headers

SQLITE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
SEED_TIME = "2024-11-14 00:00:00.000000"
TABLES = ("images", "task_events", "tasks", "users")


def _clear_tables(session):
    for table in TABLES:
        session.execute(text(f"DELETE FROM {table};"))
    session.commit()


@pytest.fixture()
def session():
    session = Session()
    _clear_tables(session)
    for user_id in (1, 2, 3):
        session.execute(
            text(
                """
                INSERT INTO users (
                    id, user_type, first_name, last_name, email, properties, is_verified,
                    verification_code, created_at
                ) VALUES (:id, 'VOLUNTEER', 'User', 'Test', :email, '[]', 1, :code, :created_at);
                """
            ),
            {
                "id": user_id,
                "email": f"user{user_id}@example.com",
                "code": f"verif-code-{user_id}",
                "created_at": SEED_TIME,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO tasks (id, title, description, category, owner_id, created_at)
                VALUES (:id, 'Help', 'please help me', 'other', :id, :created_at);
                """
            ),
            {"id": user_id, "created_at": SEED_TIME},
        )
        session.execute(
            text(
                """
                INSERT INTO task_events (task_id, type, actor_id, occurred_at)
                VALUES (:id, 'created', :id, :occurred_at);
                """
            ),
            {"id": user_id, "occurred_at": SEED_TIME},
        )
        session.execute(
            text("INSERT INTO images (id, task_id) VALUES (:image_id, :id);"),
            {"id": user_id, "image_id": f"image-{user_id}"},
        )
    session.execute(text("UPDATE tasks SET helper_id = 1 WHERE id = 3;"))
    session.execute(
        text(
            """
            INSERT INTO task_events (task_id, type, actor_id, helper_id, occurred_at)
            VALUES (3, 'offered', 1, 1, '2024-11-14 01:00:00.000000');
            """
        )
    )
    session.commit()
    yield session
    _clear_tables(session)
    session.close()


def _ids(session, table):
    return session.scalars(text(f"SELECT id FROM {table} ORDER BY id")).all()


def _purge_all_deleted_users():
    purge_deleted_users(["--before", (datetime.now(tz.utc) + timedelta(minutes=1)).isoformat()])


def test_delete_user_keeps_rows_and_marks_them_deleted(test_client, session):
    response = test_client.delete("/user/me", headers=build_headers(1))

    assert response.status_code == HTTPStatus.NO_CONTENT
    users = dict(session.execute(text("SELECT id, deleted_at FROM users")).tuples().all())
    tasks = dict(session.execute(text("SELECT id, deleted_at FROM tasks")).tuples().all())
    assert users[1] is not None
    assert users == {1: users[1], 2: None, 3: None}
    assert tasks == {1: users[1], 2: None, 3: None}
    assert session.scalar(text("SELECT COUNT(*) FROM task_events")) == 4
    assert _ids(session, "images") == ["image-1", "image-2", "image-3"]


def test_purge_removes_only_accounts_deleted_before_default_cutoff(
    test_client, session, image_storage_dir
):
    for user_id in (1, 2):
        test_client.delete("/user/me", headers=build_headers(user_id))
    deleted_long_ago = datetime.now(tz.utc) - timedelta(days=31)
    session.execute(
        text("UPDATE users SET deleted_at = :deleted_at WHERE id = 1;"),
        {"deleted_at": deleted_long_ago.strftime(SQLITE_DATETIME_FORMAT)},
    )
    session.commit()
    for image_id in ("image-1", "image-2"):
        (image_storage_dir / image_id).write_bytes(b"image")

    purge_deleted_users([])

    assert _ids(session, "users") == [2, 3]
    assert _ids(session, "tasks") == [2, 3]
    assert session.execute(
        text("SELECT task_id, type FROM task_events ORDER BY task_id, id")
    ).tuples().all() == [(2, "created"), (3, "created"), (3, "offered")]
    assert _ids(session, "images") == ["image-2", "image-3"]
    assert not (image_storage_dir / "image-1").exists()
    assert (image_storage_dir / "image-2").exists()


def test_purge_with_explicit_cutoff_includes_recent_deletions(test_client, session):
    test_client.delete("/user/me", headers=build_headers(2))

    _purge_all_deleted_users()

    assert _ids(session, "users") == [1, 3]
    assert _ids(session, "tasks") == [1, 3]


def test_signup_with_deleted_account_email_creates_new_account(test_client, session):
    test_client.delete("/user/me", headers=build_headers(1))

    response = test_client.post(
        "/user/signup/helpseeker",
        json={
            "first_name": "New",
            "last_name": "User",
            "email": "user1@example.com",
            "password": "s3cr3t-password",
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    new_id = response.json()["id"]
    accounts = text(
        "SELECT id, deleted_at IS NOT NULL FROM users WHERE email = 'user1@example.com' ORDER BY id"
    )
    assert session.execute(accounts).tuples().all() == [(1, 1), (new_id, 0)]

    _purge_all_deleted_users()

    assert session.execute(accounts).tuples().all() == [(new_id, 0)]


def test_purged_user_id_is_not_reused(test_client, session):
    test_client.delete("/user/me", headers=build_headers(3))
    _purge_all_deleted_users()

    response = test_client.post(
        "/user/signup/helpseeker",
        json={
            "first_name": "New",
            "last_name": "User",
            "email": "new.user@example.com",
            "password": "s3cr3t-password",
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["id"] > 3
