from http import HTTPStatus

import pytest
from sqlalchemy import text

from match.db import Session
from match.infra.api.schemas import TaskAction
from match.tests.conftest import build_headers

CREATED_EVENT = {
    "id": 1,
    "type": "created",
    "actor": {"id": 100, "first_name": "John"},
    "helper": None,
    "message": None,
    "occurred_at": "2024-11-14T00:00:00",
}


def insert_events(session, *events):
    for hour, (task_id, event_type, actor_id, helper_id) in enumerate(events):
        session.execute(
            text(
                """
                INSERT INTO task_events (task_id,type,actor_id,helper_id,message,occurred_at)
                VALUES (:task_id, :type, :actor_id, :helper_id, null, :occurred_at);
                """
            ),
            {
                "task_id": task_id,
                "type": event_type,
                "actor_id": actor_id,
                "helper_id": helper_id,
                "occurred_at": f"2024-11-14 {hour:02d}:00:00.000000",
            },
        )


def build_task_response(owner_id=100, task_id=1, status="open", helper_id=None, helper_offers=None):
    helper = {"id": helper_id, "first_name": "Adam"} if helper_id is not None else None
    return {
        "id": task_id,
        "title": "Help",
        "created_at": "2024-11-14T00:00:00Z",
        "updated_at": None,
        "status": status,
        "owner": {"id": owner_id, "first_name": "John"},
        "helper": helper,
        "helper_offers": helper_offers if helper_offers is not None else [],
        "description": "please help me",
        "category": "other",
        "location": {
            "lat": 39.4738,
            "lon": 0.3756,
            "address": "My address",
        },
        "images": [],
        "events": [CREATED_EVENT],
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
        INSERT OR REPLACE INTO tasks (id,title,description,category,owner_id,helper_id,updated_at,created_at,location_lat,location_lon,location_address)
        VALUES (101, 'Another task', 'different status', 'food', 101, 101, null, '2024-11-14T00:00:00Z', 39.4738, 0.3756, 'My address');
        """
    session.execute(text(statement))
    insert_events(session, (101, "created", 101, None), (101, "offered", 101, 101))
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
        INSERT OR REPLACE INTO tasks (id,title,description,category,owner_id,helper_id,updated_at,created_at,location_lat,location_lon,location_address)
        VALUES
            (101, 'Nearby task', 'nearby location', 'other', 100, null, null, '2024-11-14T00:00:00Z', 39.4740, 0.3758, 'Nearby address'),
            (102, 'Far task', 'far location', 'other', 100, null, null, '2024-11-14T00:00:00Z', 40.7128, -74.0060, 'NYC'),
            (103, 'No location task', 'no location', 'other', 100, null, null, '2024-11-14T00:00:00Z', null, null, null);
        """
    session.execute(text(statement))
    insert_events(
        session,
        (101, "created", 100, None),
        (102, "created", 100, None),
        (103, "created", 100, None),
    )
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
        INSERT OR REPLACE INTO tasks (id,title,description,category,owner_id,helper_id,updated_at,created_at,location_lat,location_lon,location_address)
        VALUES
            (100, 'Help', 'please help me', 'other', 100, null, null, '2024-11-14T00:00:00Z', 39.4738, 0.3756, 'My address'),
            (101, 'Other task', 'belongs to someone else', 'other', 101, null, null, '2024-11-14T00:00:00Z', 39.4738, 0.3756, 'My address');
        """
    session.execute(text(statement))
    insert_events(session, (101, "created", 101, None), (101, "offered", 100, 100))
    session.commit()

    response = test_client.get("/task/my-tasks", headers=build_headers(100))

    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) > 0
    assert tasks[0] == build_task_response(task_id=100)


def test_list_task_locations(test_client):
    session = Session()
    statement = """
        INSERT OR REPLACE INTO tasks (id,title,description,category,owner_id,helper_id,updated_at,created_at,location_lat,location_lon,location_address)
        VALUES (9999, 'No location task', 'location should be missing', 'other', 100, null, null, '2024-11-14T00:00:00Z', null, null, null);
        """
    session.execute(text(statement))
    insert_events(session, (9999, "created", 100, None))
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
        f"/task/{str(new_task['id'])}/manage",
        params={"action": TaskAction.JOIN, "message": "I can help with this"},
        headers=build_headers(user_id),
    )
    assert response.status_code == expected_status


def test_join_task_requires_message(test_client):
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
        f"/task/{str(new_task['id'])}/manage",
        params={"action": TaskAction.JOIN},
        headers=build_headers(101),
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_manage_task_records_events(test_client):
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
    task_url = f"/task/{new_task['id']}/manage"
    test_client.put(
        task_url,
        params={"action": TaskAction.JOIN, "message": "I can help"},
        headers=build_headers(101),
    )
    test_client.put(
        task_url, params={"action": TaskAction.REJECT, "helper_id": 101}, headers=build_headers(100)
    )

    response = test_client.get(f"/task/{new_task['id']}", headers=build_headers(100))

    assert response.json()["status"] == "open"
    john = {"id": 100, "first_name": "John"}
    adam = {"id": 101, "first_name": "Adam"}
    events = [
        {key: event[key] for key in ("type", "actor", "helper", "message")}
        for event in response.json()["events"]
    ]
    assert events == [
        {"type": "created", "actor": john, "helper": None, "message": None},
        {"type": "offered", "actor": adam, "helper": adam, "message": "I can help"},
        {"type": "rejected", "actor": john, "helper": adam, "message": None},
    ]


UPDATE_PAYLOAD = {
    "title": "new title",
    "description": "new description",
    "category": "food",
    "location": {"lat": 39.4738, "lon": 0.3756, "address": "New address"},
}


def test_edit_task_happy_path(test_client):
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
        f"/task/{new_task['id']}/edit",
        params={"action": "edit"},
        json=UPDATE_PAYLOAD,
        headers=build_headers(100),
    )

    assert response.status_code == HTTPStatus.OK
    task = response.json()
    assert task["title"] == "new title"
    assert task["description"] == "new description"
    assert task["category"] == "food"
    assert task["location"] == {"lat": 39.4738, "lon": 0.3756, "address": "New address"}
    stored = test_client.get(f"/task/{new_task['id']}", headers=build_headers(100)).json()
    assert stored["location"] == {"lat": 39.4738, "lon": 0.3756, "address": "New address"}
    assert stored["title"] == "new title"


def test_edit_task_partial_location_raises(test_client):
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
        f"/task/{new_task['id']}/edit",
        params={"action": "edit"},
        json={"location": {"lat": 40.7128, "lon": -74.0060}},
        headers=build_headers(100),
    )

    assert response.status_code == 422


def test_edit_task_rejects_non_owner(test_client):
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
        f"/task/{new_task['id']}/edit",
        json=UPDATE_PAYLOAD,
        headers=build_headers(101),
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_edit_task_not_found(test_client):
    response = test_client.put(
        "/task/999999/edit",
        json=UPDATE_PAYLOAD,
        headers=build_headers(100),
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_task_images_happy_path(test_client):
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

    response = test_client.post(
        f"/task/{new_task['id']}/images",
        files={"images": ("photo.jpg", b"fake image bytes", "image/jpeg")},
        headers=build_headers(100),
    )

    assert response.status_code == HTTPStatus.CREATED
    task = response.json()
    assert len(task["images"]) == 1
    image_id = task["images"][0]["id"]

    image_response = test_client.get(f"/task/images/{image_id}")

    assert image_response.status_code == HTTPStatus.OK
    assert image_response.content == b"fake image bytes"


def test_add_task_images_rejects_non_owner(test_client, image_storage_dir):
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

    response = test_client.post(
        f"/task/{new_task['id']}/images",
        files={"images": ("photo.jpg", b"fake image bytes", "image/jpeg")},
        headers=build_headers(101),
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert list(image_storage_dir.iterdir()) == []


def test_add_task_images_not_found(test_client):
    response = test_client.post(
        "/task/999999/images",
        files={"images": ("photo.jpg", b"fake image bytes", "image/jpeg")},
        headers=build_headers(100),
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_task_image_not_found(test_client):
    response = test_client.get("/task/images/does-not-exist")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_remove_task_image_happy_path(test_client):
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
    uploaded = test_client.post(
        f"/task/{new_task['id']}/images",
        files={"images": ("photo.jpg", b"fake image bytes", "image/jpeg")},
        headers=build_headers(100),
    ).json()
    image_id = uploaded["images"][0]["id"]

    response = test_client.delete(
        f"/task/{new_task['id']}/images/{image_id}",
        headers=build_headers(100),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["images"] == []
    assert test_client.get(f"/task/images/{image_id}").status_code == HTTPStatus.NOT_FOUND


def test_remove_task_image_rejects_non_owner(test_client):
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
    uploaded = test_client.post(
        f"/task/{new_task['id']}/images",
        files={"images": ("photo.jpg", b"fake image bytes", "image/jpeg")},
        headers=build_headers(100),
    ).json()
    image_id = uploaded["images"][0]["id"]

    response = test_client.delete(
        f"/task/{new_task['id']}/images/{image_id}",
        headers=build_headers(101),
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_remove_task_image_not_found(test_client):
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

    response = test_client.delete(
        f"/task/{new_task['id']}/images/does-not-exist",
        headers=build_headers(100),
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_remove_task_image_task_not_found(test_client):
    response = test_client.delete(
        "/task/999999/images/does-not-exist",
        headers=build_headers(100),
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_deleted_owner_tasks_are_hidden(test_client):
    test_client.delete("/user/me", headers=build_headers(100))
    headers = build_headers(101)

    response = test_client.get("/task/100", headers=headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == test_client.get("/task/999999", headers=headers).json()
    assert test_client.get("/task", headers=headers).json() == []
    assert test_client.get("/task/public").json() == []


def test_get_task_shows_deleted_helper_as_placeholder(test_client):
    session = Session()
    statement = """
        INSERT OR REPLACE INTO tasks (id,title,description,category,owner_id,helper_id,updated_at,created_at,location_lat,location_lon,location_address)
        VALUES (101, 'Help', 'please help me', 'other', 101, 100, null, '2024-11-14T00:00:00Z', 39.4738, 0.3756, 'My address');
        """
    session.execute(text(statement))
    insert_events(session, (101, "created", 101, None), (101, "offered", 100, 100))
    session.commit()
    test_client.delete("/user/me", headers=build_headers(100))

    response = test_client.get("/task/101", headers=build_headers(101))

    assert response.status_code == HTTPStatus.OK
    deleted_user = {"id": 100, "first_name": "Deleted user"}
    task = response.json()
    assert task["status"] == "pending"
    assert task["helper"] == deleted_user
    assert [event["actor"] for event in task["events"]] == [
        {"id": 101, "first_name": "Adam"},
        deleted_user,
    ]


def test_deleted_owner_task_image_answers_like_unknown_image(test_client):
    uploaded = test_client.post(
        "/task/100/images",
        files={"images": ("photo.jpg", b"fake image bytes", "image/jpeg")},
        headers=build_headers(100),
    ).json()
    image_id = uploaded["images"][0]["id"]
    test_client.delete("/user/me", headers=build_headers(100))

    response = test_client.get(f"/task/images/{image_id}")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == test_client.get("/task/images/does-not-exist").json()
