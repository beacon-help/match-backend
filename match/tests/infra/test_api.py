import json
from http import HTTPStatus
from uuid import uuid4

import pytest
from sqlalchemy import text

from match.db import Session
from match.tests.conftest import build_headers

VALID_VERIF_CODE = "2f75ccc7-9f7d-45f3-87bf-44345b0f2f06"


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
            },
            id="helpseeker",
        ),
        pytest.param(
            "/user/signup/volunteer",
            {
                "first_name": "John",
                "last_name": "Johnson",
                "email": "john@johnson.com",
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
    verification_code = "2f75ccc7-9f7d-45f3-87bf-44345b0f2f06"
    response = test_client.put(f"/user/verify/{verification_code}", headers=build_headers(103))
    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    "user_id,verification_code",
    (
        pytest.param(100, uuid4(), id="user already verified"),
        pytest.param(100, VALID_VERIF_CODE, id="user already verified, valid code"),
        pytest.param(103, uuid4(), id="user pending verification, invalid code"),
    ),
)
def test_verify_user_failed(user_id, verification_code, test_client):
    response = test_client.put(f"/user/verify/{verification_code}", headers=build_headers(user_id))
    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.fixture(autouse=True)
def populate_db():
    session = Session()
    clear_statement = "DELETE FROM tasks;"
    session.execute(text(clear_statement))
    statement = """
        INSERT OR REPLACE INTO tasks (id,title,description,status,category,owner_id,helper_id,updated_at,created_at,location_lat,location_lon,location_address)
        VALUES (100, 'Help', 'please help me', 'open', 'other', 100, null, null, '2024-11-14T00:00:00Z', 39.4738, 0.3756, 'My address');
        """
    session.execute(text(statement))
    session.commit()


def test_get_task(test_client):
    task_id = 100
    expected = build_task_response(task_id=task_id)
    response = test_client.get(f"task/{task_id}")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected


def test_list_tasks(test_client):
    response = test_client.get("/task")

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

    response = test_client.get("/task", params={"status": "pending"})

    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["status"] == "pending"
    assert tasks[0]["id"] == 101


def test_list_tasks_filtered_by_null_helper_id(test_client):
    response = test_client.get("/task", params={"helper_id": "null"})

    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) > 0
    assert all(task["helper"] is None for task in tasks)


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
