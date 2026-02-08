import json
from http import HTTPStatus
from uuid import uuid4

import pytest
from sqlalchemy import text

from match.db import Session

VALID_VERIF_CODE = "2f75ccc7-9f7d-45f3-87bf-44345b0f2f06"


def build_headers(user_id):
    return {"x-user": str(user_id)}


def build_user_response(user_id=100):
    return {
        "id": user_id,
        "first_name": "John",
        "last_name": "Johnson",
        "email": "john@johnson.com",
        "is_verified": True,
    }


def build_task_response(owner_id=100, task_id=1, status="open", helper_id=None):
    return {
        "id": task_id,
        "title": "Help",
        "created_at": "2024-11-14T00:00:00Z",
        "updated_at": None,
        "status": status,
        "owner_id": owner_id,
        "helper_id": helper_id,
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


def test_create_user_happy_path(test_client):
    payload = {
        "first_name": "Arnold",
        "last_name": "Adams",
        "email": "email@example.com",
    }
    response = test_client.post("/user/signup", data=json.dumps(payload))

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
