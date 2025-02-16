import json
from http import HTTPStatus


def build_user_response(user_id=1):
    return {
        "id": user_id,
        "first_name": "Arnold",
        "last_name": "Adams",
        "email": "email@example.com",
    }


def build_task_response(task_id=1, requester_id=3, status="open", helper_id=None):
    return {
        "id": task_id,
        "name": "Task 1",
        "created_at": "2024-11-14T00:00:00Z",
        "status": status,
        "requester_id": requester_id,
        "helper_id": helper_id,
        "type": "task_type_1",
        "description": "This is a description.",
        "location": "This will be a location",
    }


def test_health(test_client):
    response = test_client.get("/health")

    assert response.status_code == HTTPStatus.OK


def test_get_user_me(test_client):
    expected = build_user_response()
    response = test_client.get("/user/me")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected


def test_get_user_by_id(test_client):
    expected = build_user_response(123)
    response = test_client.get("/user/123")

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


def test_get_task(test_client):
    task_id = 2
    expected = build_task_response(task_id=task_id)
    response = test_client.get(f"task/{task_id}")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected
