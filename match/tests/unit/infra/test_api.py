import json
from http import HTTPStatus
from uuid import uuid4

import pytest
from sqlalchemy import text

from match.db import Session
from match.infra.api.security import hash_password
from match.tests.conftest import build_headers

VALID_VERIF_CODE = "2f75ccc7-9f7d-45f3-87bf-44345b0f2f06"
SEED_PASSWORD = "s3cr3t-password"


@pytest.fixture(autouse=True)
def populate_db():
    session = Session()
    password_hash = hash_password(SEED_PASSWORD)
    clear_users_statement = "DELETE FROM users;"
    clear_statement = "DELETE FROM tasks;"
    session.execute(text(clear_users_statement))
    session.execute(text(clear_statement))
    users_statement = """
        INSERT OR REPLACE INTO users (
            id, first_name, last_name, email, properties, is_verified, verification_code, password_hash, created_at
        ) VALUES
            (100, 'John', 'Johnson', 'john@johnson.com', '[]', 1, :code_100, :pw, '2024-11-14T00:00:00Z'),
            (101, 'Adam', 'Adamson', 'adam@adamson.com', '[]', 1, :code_101, :pw, '2024-11-14T00:00:00Z'),
            (102, 'Gary', 'Moveout', 'gary@move.out', '[]', 0, :code_102, :pw, '2024-11-14T00:00:00Z'),
            (103, 'Garry', 'Moveout', 'garry@move.out', '[]', 0, :code_103, :pw, '2024-11-14T00:00:00Z');
        """
    statement = """
        INSERT OR REPLACE INTO tasks (id,title,description,status,category,owner_id,helper_id,updated_at,created_at,location_lat,location_lon,location_address)
        VALUES (100, 'Help', 'please help me', 'open', 'other', 100, null, null, '2024-11-14T00:00:00Z', 39.4738, 0.3756, 'My address');
        """
    session.execute(
        text(users_statement),
        {
            "code_100": "verif-code-100",
            "code_101": "verif-code-101",
            "code_102": "verif-code-102",
            "code_103": VALID_VERIF_CODE,
            "pw": password_hash,
        },
    )
    session.execute(text(statement))
    session.commit()


def build_user_response(user_id=100):
    return {
        "id": user_id,
        "first_name": "John",
        "last_name": "Johnson",
        "email": "john@johnson.com",
        "is_verified": True,
    }


def build_task_response(owner_id=100, task_id=1, status="open", helper_id=None):
    helper = {"id": helper_id, "first_name": "Adam"} if helper_id is not None else None
    return {
        "id": task_id,
        "title": "Help",
        "created_at": "2024-11-14T00:00:00Z",
        "updated_at": None,
        "status": status,
        "owner": {"id": owner_id, "first_name": "John"},
        "helper": helper,
        "description": "please help me",
        "category": "other",
        "location": {
            "lat": 39.4738,
            "lon": 0.3756,
            "address": "My address",
        },
    }


def test_health(test_client):
    response = test_client.get("/health")

    assert response.status_code == HTTPStatus.OK


def test_get_user_me(test_client):
    expected = build_user_response()
    response = test_client.get("/user/me", headers=build_headers(100))

    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected


def test_get_user_by_id(test_client):
    expected = build_user_response(100)
    response = test_client.get("/user/100")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected


def test_login_happy_path(test_client):
    response = test_client.post(
        "/user/login",
        data={"username": "john@johnson.com", "password": SEED_PASSWORD},
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]

    token = body["access_token"]
    me_response = test_client.get("/user/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    "username,password",
    (
        pytest.param("john@johnson.com", "wrong-password", id="wrong-password"),
        pytest.param("nobody@nowhere.com", SEED_PASSWORD, id="unknown-user"),
        pytest.param("gary@move.out", SEED_PASSWORD, id="unverified-user"),
    ),
)
def test_login_rejected(test_client, username, password):
    response = test_client.post(
        "/user/login",
        data={"username": username, "password": password},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_refresh_happy_path(test_client):
    login_response = test_client.post(
        "/user/login",
        data={"username": "john@johnson.com", "password": SEED_PASSWORD},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = test_client.post("/user/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == HTTPStatus.OK
    new_access_token = response.json()["access_token"]
    me_response = test_client.get(
        "/user/me", headers={"Authorization": f"Bearer {new_access_token}"}
    )
    assert me_response.status_code == HTTPStatus.OK


def test_access_token_rejected_on_refresh(test_client):
    login_response = test_client.post(
        "/user/login",
        data={"username": "john@johnson.com", "password": SEED_PASSWORD},
    )
    access_token = login_response.json()["access_token"]

    response = test_client.post("/user/refresh", json={"refresh_token": access_token})

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_refresh_token_rejected_on_protected_endpoint(test_client):
    login_response = test_client.post(
        "/user/login",
        data={"username": "john@johnson.com", "password": SEED_PASSWORD},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = test_client.get("/task", headers={"Authorization": f"Bearer {refresh_token}"})

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_create_helpseeker_user_rejects_properties(test_client):
    payload = {
        "first_name": "Arnold",
        "last_name": "Adams",
        "email": "email@example.com",
        "properties": ["HAS_CAR"],
    }

    response = test_client.post("/user/signup/helpseeker", data=json.dumps(payload))

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    "endpoint,payload",
    (
        pytest.param(
            "/user/signup/helpseeker",
            {
                "first_name": "Arnold",
                "last_name": "Adams",
                "email": "email@example.com",
                "password": "s3cr3t-password",
            },
            id="helpseeker",
        ),
        pytest.param(
            "/user/signup/volunteer",
            {
                "first_name": "John",
                "last_name": "Johnson",
                "email": "john@johnson.com",
                "password": "s3cr3t-password",
                "properties": ["HAS_CAR"],
            },
            id="volunteer",
        ),
    ),
)
def test_create_user_happy_path(test_client, endpoint, payload):
    response = test_client.post(endpoint, data=json.dumps(payload))

    assert response.status_code == HTTPStatus.CREATED


def test_verify_user_happy_path(test_client):
    response = test_client.put(f"/user/verify/{VALID_VERIF_CODE}")
    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    "verification_code",
    (
        pytest.param("verif-code-100", id="user already verified"),
        pytest.param(str(uuid4()), id="unknown verification code"),
    ),
)
def test_verify_user_failed(verification_code, test_client):
    response = test_client.put(f"/user/verify/{verification_code}")
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_get_task(test_client):
    task_id = 100
    expected = build_task_response(task_id=task_id)
    response = test_client.get(f"task/{task_id}")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected


@pytest.mark.parametrize(
    "headers,expected_status",
    (
        pytest.param(None, HTTPStatus.UNAUTHORIZED, id="no-header"),
        pytest.param({"x-user": "abc"}, HTTPStatus.UNAUTHORIZED, id="non-integer-header"),
        pytest.param(build_headers(9999), HTTPStatus.UNAUTHORIZED, id="unknown-user"),
        pytest.param(build_headers(102), HTTPStatus.UNAUTHORIZED, id="unverified-user"),
        pytest.param(build_headers(100), HTTPStatus.OK, id="verified-user"),
    ),
)
def test_list_tasks_requires_verified_user(test_client, headers, expected_status):
    response = test_client.get("/task", headers=headers)

    assert response.status_code == expected_status


def test_list_tasks(test_client):
    response = test_client.get("/task", headers=build_headers(100))

    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) > 0
    assert "owner_id" not in tasks[0]
    assert "helper_id" not in tasks[0]
    assert tasks[0]["owner"] == {"id": 100, "first_name": "John"}


def test_list_tasks_filtered_by_status(test_client):
    session = Session()
    statement = """
        INSERT OR REPLACE INTO tasks (id,title,description,status,category,owner_id,helper_id,updated_at,created_at,location_lat,location_lon,location_address)
        VALUES (101, 'Another task', 'different status', 'pending', 'food', 101, 101, null, '2024-11-14T00:00:00Z', 39.4738, 0.3756, 'My address');
        """
    session.execute(text(statement))
    session.commit()

    response = test_client.get("/task", params={"status": "pending"}, headers=build_headers(100))

    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["status"] == "pending"
    assert tasks[0]["id"] == 101


def test_list_tasks_filtered_by_null_helper_id(test_client):
    response = test_client.get("/task", params={"helper_id": "null"}, headers=build_headers(100))

    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) > 0
    assert all(task["helper"] is None for task in tasks)


def test_list_tasks_filtered_by_radius(test_client):
    session = Session()
    statement = """
        INSERT OR REPLACE INTO tasks (id,title,description,status,category,owner_id,helper_id,updated_at,created_at,location_lat,location_lon,location_address)
        VALUES
            (101, 'Nearby task', 'nearby location', 'open', 'other', 100, null, null, '2024-11-14T00:00:00Z', 39.4740, 0.3758, 'Nearby address'),
            (102, 'Far task', 'far location', 'open', 'other', 100, null, null, '2024-11-14T00:00:00Z', 40.7128, -74.0060, 'NYC'),
            (103, 'No location task', 'no location', 'open', 'other', 100, null, null, '2024-11-14T00:00:00Z', null, null, null);
        """
    session.execute(text(statement))
    session.commit()

    response = test_client.get(
        "/task",
        params={"lat": 39.4738, "lon": 0.3756, "radius_km": 1},
        headers=build_headers(100),
    )

    assert response.status_code == HTTPStatus.OK
    assert {task["id"] for task in response.json()} == {100, 101}


@pytest.mark.parametrize(
    "params", ({"lat": 39.4738, "radius_km": 1}, {"lat": 39.4738, "lot": 39.4738})
)
def test_list_tasks_rejects_partial_radius_filter(test_client, params):
    response = test_client.get("/task", params=params, headers=build_headers(100))

    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_get_my_tasks(test_client):
    session = Session()
    statement = """
        INSERT OR REPLACE INTO tasks (id,title,description,status,category,owner_id,helper_id,updated_at,created_at,location_lat,location_lon,location_address)
        VALUES
            (100, 'Help', 'please help me', 'open', 'other', 100, null, null, '2024-11-14T00:00:00Z', 39.4738, 0.3756, 'My address'),
            (101, 'Other task', 'belongs to someone else', 'pending', 'other', 101, null, null, '2024-11-14T00:00:00Z', 39.4738, 0.3756, 'My address');
        """
    session.execute(text(statement))
    session.commit()

    response = test_client.get("/task/my-tasks", headers=build_headers(100))

    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) > 0
    assert tasks[0] == build_task_response(task_id=100)


def test_list_task_locations(test_client):
    session = Session()
    statement = """
        INSERT OR REPLACE INTO tasks (id,title,description,status,category,owner_id,helper_id,updated_at,created_at,location_lat,location_lon,location_address)
        VALUES (9999, 'No location task', 'location should be missing', 'open', 'other', 100, null, null, '2024-11-14T00:00:00Z', null, null, null);
        """
    session.execute(text(statement))
    session.commit()

    response = test_client.get("/task/locations")

    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) > 0
    assert 9999 not in {task["id"] for task in tasks}
    assert set(tasks[0].keys()) == {"id", "location"}
    assert set(tasks[0]["location"].keys()) == {"lat", "lon", "address"}


@pytest.mark.parametrize(
    "user_id,expected_status",
    (
        pytest.param(100, HTTPStatus.CREATED, id="happy-path"),
        pytest.param(102, HTTPStatus.FORBIDDEN, id="user-not-verified", marks=pytest.mark.xfail),
    ),
)
def test_create_task(test_client, user_id, expected_status):
    response = test_client.post(
        "/task",
        json={
            "title": "title",
            "description": "description",
            "category": "other",
            "location": {"lat": 40.7128, "lon": -74.0060, "address": "NYC"},
        },
        headers=build_headers(user_id),
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "user_id,expected_status",
    (
        pytest.param(101, HTTPStatus.OK, id="happy-path"),
        pytest.param(102, HTTPStatus.FORBIDDEN, id="user-not-verified", marks=pytest.mark.xfail),
    ),
)
def test_join_task(test_client, user_id, expected_status):
    new_task = test_client.post(
        "/task",
        json={
            "title": "title",
            "description": "description",
            "category": "other",
            "location": {"lat": 40.7128, "lon": -74.0060, "address": "NYC"},
        },
        headers=build_headers(100),
    ).json()
    response = test_client.put(
        f"/task/{str(new_task['id'])}", params={"action": "join"}, headers=build_headers(user_id)
    )
    assert response.status_code == expected_status
