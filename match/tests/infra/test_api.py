import json
from http import HTTPStatus


def build_headers(user_id):
    return {"x-user": str(user_id)}


def build_user_response(user_id=100):
    return {
        "id": user_id,
        "first_name": "John",
        "last_name": "Johnson",
        "email": "john@johnson.com",
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


def test_get_task(test_client):
    task_id = 100
    expected = build_task_response(task_id=task_id)
    response = test_client.get(f"task/{task_id}")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == expected


def test_create_task(test_client):
    response = test_client.post(
        "/task", json={"title": "title", "description": "description"}, headers=build_headers(100)
    )

    assert response.status_code == HTTPStatus.CREATED


def test_join_task(test_client):
    new_task = test_client.post(
        "/task", json={"title": "title", "description": "description"}, headers=build_headers(100)
    ).json()
    response = test_client.put(
        f"/task/{str(new_task['id'])}", params={"action": "join"}, headers=build_headers(101)
    )
    assert response.status_code == HTTPStatus.OK
