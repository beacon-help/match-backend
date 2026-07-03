from http import HTTPStatus

import pytest
from sqlalchemy import text

from match.db import Session
from match.tests.conftest import build_headers


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


def test_get_task(test_client):
    task_id = 100
    expected = build_task_response(task_id=task_id)
    response = test_client.get(f"task/{task_id}", headers=build_headers(100))

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
